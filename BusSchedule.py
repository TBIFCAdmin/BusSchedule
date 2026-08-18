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
# Global Terminal CSS Injection (Optimized & Responsive High-Visibility Theme)
st.markdown(
    """
    <style>
    /* 1. Global Reset & Layout Constraints */
    header, footer, [data-testid="stToolbar"] { display: none !important; }

    html, body, [data-testid="stAppViewContainer"] { 
      height: 100vh; 
      overflow: hidden !important; 
      background-color: #0A0F1D !important; 
    }
        /* Hide scrollbars for Chrome, Safari and Opera */
    *::-webkit-scrollbar {
      display: none !important;
    }

    /* Hide scrollbars for IE, Edge and Firefox */
    * {
      -ms-overflow-style: none !important;  /* IE and Edge */
      scrollbar-width: none !important;  /* Firefox */
    }

    .block-container { 
      padding: 3vh 3vw !important; 
      height: 100vh; 
      display: flex; 
      flex-direction: column; 
      justify-content: flex-start; 
      background-color: #0A0F1D; 
      box-sizing: border-box; 
    }

    /* 2. Responsive Typography */
    .display-title { 
      color: #FFFFFF; 
      font-size: calc(1.8rem + 1vw); 
      font-weight: 900; 
      letter-spacing: -0.05em; 
      text-transform: uppercase; 
      margin: 0; 
      padding: 0; 
    }

    .display-subtitle { 
      color: #8E9AA8; 
      font-size: calc(0.9rem + 0.3vw); 
      font-weight: 500; 
      margin-top: 0.2vh; 
      margin-bottom: 2vh; 
      text-transform: uppercase; 
      letter-spacing: 0.05em; 
    }

    .schedule-header { 
      font-size: calc(1.1rem + 0.4vw); 
      font-weight: 800; 
      color: #00FFCC; 
      text-transform: uppercase; 
      border-left: 0.4vw solid #00FFCC; 
      padding-left: 1vw; 
      margin-top: .5vh; 
      margin-bottom: 0.5vh; 
    }

    /* 3. Optimized Transit Board Grid */
    table { 
      width: 100%; 
      border: none; 
      background-color: #111625; 
      margin-bottom: 0.5vh !important;
      border-collapse: collapse; 
      border: 1px solid #1C243B; 
    }

    th { 
      padding: 0.8vh 1vw !important; 
      font-size: calc(0.8rem + 0.3vw); 
      border: none; 
      color: #8E9AA8 !important; 
      text-align: left; 
      background-color: #171E31; 
      text-transform: uppercase; 
      font-weight: 700; 
      letter-spacing: 0.05em; 
    }

    table td { 
      border: none; 
      padding: 0.8vh 1vw !important; /* 🏃‍♂️ Slashed vertical padding from 1.2vh to 0.8vh */
      font-size: calc(0.9rem + 0.3vw); /* 🔍 Slightly dropped scale base to fit more rows */
      color: #FFFFFF !important; 
      border-bottom: 1px solid #1C243B; 
      font-variant-numeric: tabular-nums; 
    }

    /* 4. High-Visibility Column Controls */
    td:first-child { 
      color: #000000 !important; 
      font-weight: 900; 
      text-align: center; 
      width: 10%; 
    }

    td:nth-child(2) { font-weight: 600; color: #FFFFFF; }
    td:last-child { font-weight: 800; color: #00FFCC !important; text-align: right; }
    th:last-child { text-align: right; }

    /* 5. Static, CPU-Friendly Alert Ribbon */
    .warning-banner { 
      background-color: #FF3B30; 
      color: #FFFFFF; 
      padding: 1.5vh 2vw; 
      border-radius: 4px; 
      font-weight: 900; 
      font-size: calc(1rem + 0.2vw); 
      text-transform: uppercase; 
      margin-top: auto; 
      text-align: center; 
      width: 100%; 
      letter-spacing: 0.05em; 
      box-sizing: border-box; 
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. Public Display Font Scaling Architecture
if st.session_state.has_warnings or num_urls > 2:
    st.write(
        '<style>'
        '.display-title {font-size: 3.5vh !important;}'
        '.display-subtitle {font-size: 1.6vh !important;}'
        '.schedule-header {font-size: 1.6vh !important;}'
        'th {font-size: 2.0vh !important; padding: 10px 14px;}'
        'table td {font-size: 2.2vh !important}'
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
        'table td {font-size: 3.6vh !important}'
        '</style>',
        unsafe_allow_html=True
    )

# Helper function to match exact Thunder Bay Transit System color profiles

def get_route_style(route_short_name):
    name = str(route_short_name).strip().upper()

    color_map = {
        "1": {"bg": "#E31B23", "fg": "#FFFFFF"},  # Mainline (Red)
        "2": {"bg": "#008751", "fg": "#FFFFFF"},  # Crosstown (Green)
        "3C": {"bg": "#9B7D0D", "fg": "#FFFFFF"},  # Memorial (Ocean Blue)
        "3M": {"bg": "#FF8200", "fg": "#0A0F1D"},  # Memorial Alt (Orange)
        "3T": {"bg": "#702082", "fg": "#FFFFFF"},  # Junction (Purple)
        "3J": {"bg": "#EE2B74","fg": "#FFFFFF"},  # JUMBO GARDENS
        "4": {"bg": "#0038A8", "fg": "#FFFFFF"},  # Neebing (Navy Blue)
        "7": {"bg": "#FFD100", "fg": "#0A0F1D"},  # Hudson (Yellow)
        "9": {"bg": "#00A699", "fg": "#FFFFFF"},  # Junot (Teal)
        "11": {"bg": "#E87722", "fg": "#FFFFFF"},  # John (Burnt Amber)
        "12": {"bg": "#D96B27", "fg": "#FFFFFF"},  # East End (Copper)
        "14": {"bg": "#4A777A", "fg": "#FFFFFF"},  # Arthur (Slate)
        "16": {"bg": "#005A9C", "fg": "#FFFFFF"},  # Balmoral (Royal Blue)
        "17": {"bg": "#BF4F9D", "fg": "#FFFFFF"},  # Current River (Pink)
    }

    if name in color_map:
        return color_map[name]

    return {"bg": "#FFB800", "fg": "#000000"}



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
            lambda d: len([el for el in d.find_elements(By.CSS_SELECTOR, "span[data-bind*='Dest']") if el.text.strip()]) > 0
        )

        # Pull elements safely
        destinations = [el.text.strip() for el in driver_instance.find_elements(By.CSS_SELECTOR, "span[data-bind*='Dest']") if
                        el.text.strip()]

        # --- FIXED FOR LINUX HEADLESS: RAW ATTRIBUTE SCRAPER ---
        # NextLift embeds route information in raw html properties.
        # Using get_attribute("textContent") bypasses headless frame occlusion entirely.
        routes = []
        route_elements = driver_instance.find_elements(By.CSS_SELECTOR, "span[data-bind*='RowLabel']:not(.font-weight-line)")
        #destinations = [el.text.strip() for el in route_elements if el.text.strip()]

        for el in route_elements:
            # Force pull from raw text layer, skipping Selenium's visibility engine rules
            route_num = el.get_attribute("textContent")
            if route_num:
                route_num = route_num.strip()

            style_dict = get_route_style(route_num)

            routes.append({
                "number": route_num if route_num else "?",
                "bg": style_dict["bg"],
                "fg": style_dict["fg"]
            })

        # Process arrival times via raw layers
        times = []
        time_elements = driver_instance.find_elements(By.CSS_SELECTOR, "span[data-bind*='Next']")
        for el in time_elements:
            text = el.get_attribute("textContent")
            if text:
                times.append(text.strip())

        # Zip elements together into customized layout structures
    # Ensure arrays map to each other properly
        total_items = max(len(destinations), len(routes), len(times))

        table_rows = ""
        for idx in range(total_items):
            dest = destinations[idx] if idx < len(destinations) else "N/A"
            arrival_time = times[idx] if idx < len(times) else "N/A"

            # Pull data safely from routes array
            if idx < len(routes):
                route_data = routes[idx]
            else:
                # Universal fallback if index is missing entirely
                route_data = {"number": "?", "bg": "#FFB800", "fg": "#000000"}

            # Custom tag markup
            styled_route = (
                f'<span style="background-color: {route_data["bg"]} !important; '
                f'color: {route_data["fg"]} !important; '
                #f'padding: 10px 0px; '  # Balanced vertical padding, no side gaps
                f'display: block; '  # Forces element to take up 100% cell width
                f'width: 100%; '  # Fills cell boundary
                f'text-align: center; '
                f'font-weight: 900;'
                f'box-shadow: inset 0px 0px 4px rgba(0,0,0,0.15);">'  # Subtler interior shadow
                f'{route_data["number"]}</span>'
            )

            # Build raw HTML row directly to bypass tabulate structural strips
            table_rows += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #333;">{styled_route}</td>
                <td style="padding: 10px; border-bottom: 1px solid #333; color: white;">{dest}</td>
                <td style="padding: 10px; border-bottom: 1px solid #333; color: #8E9AA8;">{arrival_time}</td>
            </tr>
            """

    except (TimeoutException, StaleElementReferenceException):
        pass

    txtHeader = st.session_state[f"Header-{url}"]
    output_html = f'<p class="schedule-header">{txtHeader}</p>'

    if table_rows:
        # Strip newlines from rows and wrap into a continuous HTML string
        clean_rows = table_rows.replace("\n", "").strip()

        output_html += (
            f'<table style="width: 100%; border-collapse: collapse; text-align: left;">'
            f'<thead>'
            f'<tr style="border-bottom: 1px solid #555;">'
            f'<th style="color: #8E9AA8;">Route</th>'
            f'<th style="color: #8E9AA8;">Destination</th>'
            f'<th style="color: #8E9AA8;">Scheduled Arrival</th>'
            f'</tr>'
            f'</thead>'
            f'<tbody>{clean_rows}</tbody>'
            f'</table>'
        )
    else:
        output_html += '<p style="color: #8E9AA8; font-size: 2.6vh; font-style: italic; padding: 20px;">No upcoming departures scheduled for this terminal block.</p>'

    # Use native st.html to ensure strict, pure HTML injection without Markdown processing interference
    container.html(output_html)


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
#st.markdown('<p class="display-title">Live Transit Arrival Times</p>', unsafe_allow_html=True)


for i in range(num_urls):
    schedule_container = st.container()
    render_bus_schedule(drivers[i], waits[i], urls[i], schedule_container)

warning_container = st.container()
render_global_warnings(drivers, warning_container)

# MEMORY LEAK MITIGATION 2: Explicitly garbage collect dangling strings after the main pass runs
gc.collect()
