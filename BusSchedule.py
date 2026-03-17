import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from tabulate import tabulate

import time
st.set_page_config(layout="wide")

options = Options()
options.add_argument("--headless=new")

driver = webdriver.Chrome(options)
wait = WebDriverWait(driver,15)
driver.get("https://nextlift.ca/#f=Clavet%20%26%20Cumberland%20(1128)")

driver2= webdriver.Chrome(options)
wait2 = WebDriverWait(driver2,15)
driver2.get("https://nextlift.ca/#f=Clavet%20%26%20Cumberland%20(1180)")
st.write('<b><style> .block-container {padding-top: 5rem; padding-bottom: 0rem; padding-left: 5rem; padding-right: 5rem;} table {width: 100%; border: none; background-color: #003360;} th {border: none; font-size: 44px} table td {border: none; font-size: 36px} td:first-child {background-color: rgb(191, 79, 157); color: rgb(255, 255, 255)}</style></b>', unsafe_allow_html=True)


@st.fragment(run_every="60s")
def Get_Page_Warning(local_driver, local_wait):
    try:
        dynamic_element = local_wait.until(EC.presence_of_element_located((By.ID, "noResults")))
        warnings = local_driver.find_elements(By.ID, "noResults")
        for x in warnings:
            if x.text != "":
                st.markdown(f'<p style="font-weight: bold; font-size:36px; color:orange;">{x.text}</p>', unsafe_allow_html=True)
    except TimeoutException:
        pass
        
    


@st.fragment(run_every="60s")
def Get_Page_Info(local_driver, local_wait):
    try:
        dynamic_element = local_wait.until(EC.presence_of_element_located((By.CLASS_NAME, "header-result")))
        txtHeader = local_driver.find_element(By.CLASS_NAME, "header-result").text
    except TimeoutException:
        txtHeader="Header Took too long to load"

    if txtHeader == "":
        txtHeader = "No header Result pulled"

    st.markdown(f'<p style="font-weight: bold; font-size:36px;">{txtHeader}</p>', unsafe_allow_html=True)
    list_of_lists =[]
    try:
        dynamic_element = local_wait.until(EC.presence_of_element_located((By.CLASS_NAME, "header-main")))
        elements = local_driver.find_elements(By.CLASS_NAME, "header-main")
        for x in elements:
            if x.text != "":
                sublist = ["17", x.text]
                list_of_lists.append(sublist)

    except TimeoutException:
        st.write("Line details took too long")

    elements = local_driver.find_elements(By.CLASS_NAME, "line-prop-addon-image-container-time")
    y=0
    for x in elements:
        if x.text != "":
            list_of_lists[y].append(x.text)
            y=y+1

    table = tabulate(
        list_of_lists,
        headers=["Route", "Destination", "Arrival"],
        tablefmt="html"
    )
                     


    st.markdown(table, unsafe_allow_html=True)

    
Get_Page_Info(driver,wait)
Get_Page_Info(driver2,wait2)
Get_Page_Warning(driver,wait)


