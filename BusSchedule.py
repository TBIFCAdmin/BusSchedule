import os
import tempfile
import gc  # Added for manual memory reclamation
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from tabulate import tabulate

# 1. Page Config
st.set_page_config(layout="wide")

# Read URLs from urls.txt safely
URLS_FILE = "urls.txt"
if not os.path.exists(URLS_FILE):
    with open(URLS_FILE, "w") as f:
        f.write("https://nextlift.ca\n")
        f.write("https://nextlift.ca\n")

with open(URLS_FILE, "r") as f:
    urls = [line.strip() for line in f if line.strip()]

num_urls = len(urls)

if "has_warnings" not in st.session_state:
    st.session_state.has_warnings = False

# Global Terminal CSS Injection (High-Visibility Transit Theme)
st.write(
    '<style>'
    'header, footer, [data-testid="stToolbar"] {display: none !important;}'
    'html, body, [data-testid="stAppViewContainer"] {height: 100vh; overflow: hidden !important; background-color: #0A0F1D !important;}'

    '.block-container {padding-top: 2rem !important; padding-bottom: 1.5rem !important; '
    'padding-left: 3rem !important; padding-right: 3rem !important; '
    'height: 100vh; display: flex; flex-direction: column; justify-content: space-between; background-color: #0A0F1D;}'

    # Public Display Board Typography
    '.display-title {color: #FFFFFF; font-weight: 900; letter-spacing: -1px; text-transform: uppercase; margin: 0; padding: 0;}'
    '.display-subtitle {color: #8E9AA8; font-weight: 500; margin-top: -0.5vh; margin-bottom: 2vh; text-transform: uppercase; letter-spacing: 1px;}'
    '.schedule-header {font-weight: 800; color: #00FFCC; text-transform: uppercase; border-left: 6px solid #00FFCC; padding-left: 12px; margin-top: 1vh; margin-bottom: 1.5vh;}'

    # Terminal Flight Board Styling (Dark background, Amber/Teal text grid)
    'table {width: 100%; border: none; background-color: #111625; margin-bottom: 1.5vh; border-collapse: collapse; box-shadow: 0px 4px 15px rgba(0,0,0,0.5);}'
    'th {padding: 12px 16px; border: none; color: #8E9AA8 !important; text-align: left; background-color: #171E31; text-transform: uppercase; font-weight: 700; letter-spacing: 1px;}'
    'table td {border: none; padding: 14px 16px; color: #FFFFFF !important; border-bottom: 2px solid #1C243B; font-variant-numeric: tabular-nums;}'

    # High visibility column mappings
    'td:first-child {background-color: #FFB800 !important; color: #000000 !important; font-weight: 900; text-align: center; width: 12%; font-size: 110%;}'
    'td:nth-child(2) {font-weight: 600; color: #FFFFFF;}'
    'td:last-child {font-weight: 800; color: #00FFCC !important; text-align: right;}'
    'th:last-child {text-align: right;}'

    # Critical Alert Ribbon at bottom
    '.warning-banner {background-color: #FF3B30; color: #FFFFFF; padding: 2vh; '
    'border-radius: 6px; font-weight: 900; text-transform: uppercase; animation: pulse 2s infinite; margin-top: 1.5vh; text-align: center; width: 100%; letter-spacing: 1px;}'

    '@keyframes pulse {0% {opacity: 1;} 50% {opacity: 0.85;} 100% {opacity: 1;}}'
    '</style>',
    unsafe_allow_html=True
)

# 2. Public Display Font Scaling Architecture
if st.session_state.has_warnings or num_urls > 2:
    st.write(
        '<style>'
        '.display-title {font-size: 4.5vh !important;}'
        '.display-subtitle {font-size: 2.2vh !important;}'
        '.schedule-header {font-size: 2.6vh !important;}'
        'th {font-size: 2.4vh !important; padding: 10px 14px;}'
        'table td {font-size: 2.6vh !important; padding: 10px 14px !important;}'
        '.warning-banner {font-size: 2.6vh;}'
        '</style>',
        unsafe_allow_html=True
    )
else:
    st.write(
        '<style>'
        '.display-title {font-size: 5.5vh !important;}'
        '.display-subtitle {font-size: 2.6vh !important;}'
        '.schedule-header {font-size: 3.4vh !important;}'
        'th {font-size: 3.0vh !important; padding: 16px 20px;}'
        'table td {font-size: 3.6vh !important; padding: 16px 20px !important;}'
        '</style>',
        unsafe_allow_html=True
    )


# 3. Dynamic Driver Caching
@st.cache_resource
def get_cached_drivers_dynamic(count):
    drivers = []
    waits = []

    system_temp_folder = tempfile.gettempdir()

    for i in range(count):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        # --- ADD THESE LINUX SPECIFIC FIXES ---
        options.add_argument("--disable-gpu")  # Disables hardware acceleration
        options.add_argument("--disable-software-rasterizer")  # Prevents falling back to slow raster rendering
        options.add_argument("--disable-extensions")  # Speeds up containerized/headless execution
        options.add_argument("--blink-settings=imagesEnabled=false")  # Stops loading images to save memory/speed up
        # --------------------------------------

        options.add_argument(f"--remote-debugging-port={9222 + i}")

        worker_data_path = os.path.join(system_temp_folder, f"chrome_bus_schedule_{i}")
        options.add_argument(f"--user-data-dir={worker_data_path}")

        d = webdriver.Chrome(options=options)

        # Lower this value slightly if testing; 20 seconds is high
        # and will stall your layout engine completely if one URL fails
        w = WebDriverWait(d, 20)
        drivers.append(d)
        waits.append(w)
    return drivers, waits


drivers, waits = get_cached_drivers_dynamic(num_urls)


# 4. Schedule Fragment Function
@st.fragment(run_every="20s")
def render_bus_schedule(driver_instance, wait_instance, url, container):
    try:
        driver_instance.get(url)
    except Exception as e:
        container.error(f"Failed to access URL layout: {e}")
        return

    if f"Header-{url}" not in st.session_state:
        st.session_state[f"Header-{url}"] = ""

    if st.session_state[f"Header-{url}"] in ["", "Please define your search..."]:
        try:
            wait_instance.until(lambda d: d.find_element(By.CLASS_NAME, "header-result").text.strip() != "")
            st.session_state[f"Header-{url}"] = driver_instance.find_element(By.CLASS_NAME, "header-result").text
        except TimeoutException:
            st.session_state[f"Header-{url}"] = "SYSTEM TIMEOUT - REFRESHING DATA"

    list_of_lists = []

    try:
        # Core parent wait: Ensures transit entry items are fully built
        wait_instance.until(
            lambda d: len([el for el in d.find_elements(By.CLASS_NAME, "header-main") if el.text.strip()]) > 0
        )

        # Pull elements safely
        destinations = [el.text.strip() for el in driver_instance.find_elements(By.CLASS_NAME, "header-main") if
                        el.text.strip()]

        # --- FIXED FOR LINUX HEADLESS: RAW ATTRIBUTE SCRAPER ---
        # NextLift embeds route information in raw html properties.
        # Using get_attribute("textContent") bypasses headless frame occlusion entirely.
        routes = []
        route_elements = driver_instance.find_elements(By.CLASS_NAME, "line-prop-addon-image-container-route")

        for el in route_elements:
            # Force pull from raw text layer, skipping Selenium's visibility engine rules
            route_num = el.get_attribute("textContent")
            if route_num:
                route_num = route_num.strip()

            if not route_num:
                # Secondary fallback: Extract numeric values straight from raw outer HTML tags
                try:
                    outer = el.get_attribute("outerHTML")
                    # Quick split to catch values wrapped in inner structures
                    route_num = outer.split(">")[1].split("<")[0].strip()
                except Exception:
                    route_num = "?"

            # DIRECT HTML ATTRIBUTE EXTRACTION FOR COLOR MATCHING
            # Since value_of_css_property returns blank in headless boxes,
            # we read the style property directly if configured by NextLift
            try:
                style_attr = el.get_attribute("style") or ""
                bg_color = "#FFB800"  # default brand amber
                text_color = "#000000"  # default dark text

                if "background-color" in style_attr:
                    bg_color = style_attr.split("background-color:")[1].split(";")[0].strip()
                if "color" in style_attr and "background-color" not in style_attr.split("color")[0]:
                    text_color = style_attr.split("color:")[1].split(";")[0].strip()
            except Exception:
                bg_color = "#FFB800"
                text_color = "#000000"

            routes.append({
                "number": route_num if route_num else "?",
                "bg": bg_color,
                "fg": text_color
            })

        # Process arrival times via raw layers
        times = []
        time_elements = driver_instance.find_elements(By.CLASS_NAME, "line-prop-addon-image-container-time")
        for el in time_elements:
            text = el.get_attribute("textContent")
            times.append(text.strip() if text else "N/A")

        # Zip elements together into customized layout structures
        for idx, dest in enumerate(destinations):
            arrival_time = times[idx] if idx < len(times) else "N/A"
            route_data = routes[idx] if idx < len(routes) else {"number": "?", "bg": "#FFB800", "fg": "#000000"}

            # Format row data using customized styling matching individual route configurations
            styled_route = (
                f'<span style="background-color: {route_data["bg"]}; '
                f'color: {route_data["fg"]}; '
                f'padding: 6px 12px; '
                f'border-radius: 4px; '
                f'display: inline-block; '
                f'min-width: 50px; '
                f'text-align: center; '
                f'font-weight: 900;'
                f'box-shadow: 0px 2px 4px rgba(0,0,0,0.3);">'
                f'{route_data["number"]}</span>'
            )
            list_of_lists.append([styled_route, dest, arrival_time])

    except (TimeoutException, StaleElementReferenceException):
        pass

    txtHeader = st.session_state[f"Header-{url}"]
    output_html = f'<p class="schedule-header">{txtHeader}</p>'

    if list_of_lists:
        table = tabulate(
            list_of_lists,
            headers=["Route", "Destination", "Scheduled Arrival"],
            tablefmt="html"
        )
        # Clear out default table formatting constraints to support nested markup cells
        output_html += table.replace("&lt;", "<").replace("&gt;", ">")
    else:
        output_html += "<p style='color: #8E9AA8; font-size: 2.6vh; font-style: italic; padding: 20px;'>No upcoming departures scheduled for this terminal block.</p>"

    container.markdown(output_html, unsafe_allow_html=True)

    try:
        driver_instance.delete_all_cookies()
        driver_instance.execute_cdp_cmd("Network.clearBrowserCache", {})
        driver_instance.execute_cdp_cmd("Network.clearBrowserCookies", {})
    except Exception:
        pass


# --- STANDALONE BOTTOM WARNING FRAGMENT ---
@st.fragment(run_every="20s")
def render_global_warnings(drivers_list, container):
    unique_warnings = set()

    for d_instance in drivers_list:
        try:
            w_wait = WebDriverWait(d_instance, 2)
            w_wait.until(EC.presence_of_element_located((By.ID, "noResults")))

            elements = d_instance.find_elements(By.ID, "noResults")
            for x in elements:
                text = x.text.strip()
                if text:
                    unique_warnings.add(text)
        except TimeoutException:
            pass

    found_warnings = len(unique_warnings) > 0

    if found_warnings != st.session_state.has_warnings:
        st.session_state.has_warnings = found_warnings
        #st.rerun()

    if unique_warnings:
        combined_text = "  ⚠️  ".join(unique_warnings)
        html_banner = f'<div class="warning-banner">SYSTEM NOTICE: {combined_text}</div>'
        container.markdown(html_banner, unsafe_allow_html=True)
    else:
        container.empty()


# 5. Core View Layout Engine (Stacked Vertical Viewport Setup)
st.markdown('<p class="display-title">Live Transit Arrival Times</p>', unsafe_allow_html=True)

for i in range(num_urls):
    schedule_container = st.container()
    render_bus_schedule(drivers[i], waits[i], urls[i], schedule_container)

warning_container = st.container()
render_global_warnings(drivers, warning_container)

# MEMORY LEAK MITIGATION 2: Explicitly garbage collect dangling strings after the main pass runs
gc.collect()
