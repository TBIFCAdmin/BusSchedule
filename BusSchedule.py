import os
import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from tabulate import tabulate
import time

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
@st.cache_resource
def get_cached_drivers_dynamic(count):
    drivers = []
    waits = []
    for i in range(count):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")

        # Unique port and profile mappings to stop collision/crosstalk bugs
        options.add_argument(f"--remote-debugging-port={9222 + i}")
        options.add_argument(f"--user-data-dir=/tmp/chrome_user_data_{i}")
        options.add_argument(f"--disk-cache-dir=/tmp/chrome_disk_cache_{i}")

        options.add_argument("--remote-allow-origins=*")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-crash-reporter")
        options.add_argument("--disable-in-process-stack-traces")
        options.add_argument("--disable-logging")
        options.add_argument("--log-level=3")

        try:
            d = webdriver.Chrome(options=options)
            d.set_page_load_timeout(30)
            d.set_script_timeout(30)
            w = WebDriverWait(d, 20)
            drivers.append(d)
            waits.append(w)
        except Exception as e:
            st.error(f"Failed to boot worker thread {i}: {str(e)}")

    return drivers, waits

drivers, waits = get_cached_drivers_dynamic(num_urls)


# 4. Schedule Fragment Function
@st.fragment(run_every="20s")
def render_bus_schedule(driver_instance, wait_instance, url, container):
    driver_instance.get(url)
    #driver_instance.refresh()

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
        wait_instance.until(EC.presence_of_element_located((By.CLASS_NAME, "header-main")))

        destinations = [el.text.strip() for el in driver_instance.find_elements(By.CLASS_NAME, "header-main") if
                        el.text.strip()]
        times = [el.text.strip() for el in
                 driver_instance.find_elements(By.CLASS_NAME, "line-prop-addon-image-container-time") if
                 el.text.strip()]

        for idx, dest in enumerate(destinations):
            arrival_time = times[idx] if idx < len(times) else "N/A"
            list_of_lists.append(["17", dest, arrival_time])

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
        output_html += table
    else:
        output_html += "<p style='color: #8E9AA8; font-size: 2.6vh; font-style: italic; padding: 20px;'>No upcoming departures scheduled for this terminal block.</p>"

    container.markdown(output_html, unsafe_allow_html=True)


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
                try:
                    text = x.text.strip()
                    if text:
                        unique_warnings.add(text)
                except StaleElementReferenceException:
                    continue
        except TimeoutException:
            pass

    found_warnings = len(unique_warnings) > 0

    if found_warnings != st.session_state.has_warnings:
        st.session_state.has_warnings = found_warnings
        st.rerun()

    if unique_warnings:
        combined_text = "  ⚠️  ".join(unique_warnings)
        html_banner = f'<div class="warning-banner">SYSTEM NOTICE: {combined_text}</div>'
        container.markdown(html_banner, unsafe_allow_html=True)
    else:
        container.empty()


# 5. Render Layout Core Blocks
st.markdown('<p class="display-title">Live Transit Departures</p>', unsafe_allow_html=True)
st.markdown('<p class="display-subtitle">Real-time tracking network monitor</p>', unsafe_allow_html=True)

# Schedules are stacked in a single full-width vertical layout
for i in range(num_urls):
    schedule_container = st.container()
    render_bus_schedule(drivers[i], waits[i], urls[i], schedule_container)

# Render global notices and system warning flags at the absolute bottom
warning_container = st.container()
render_global_warnings(drivers, warning_container)
