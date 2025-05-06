from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

username = os.getenv('USERNAME_ZENIC')
password = os.getenv('PASSWORD_ZENIC')
chrome_driver_env = os.getenv('chrome_driver')
download_path = os.getenv('zenic_alarm_download_path')
home_url=os.getenv('home_url')
alarms_url=os.getenv('alarms_url')

print(username)
print(password)
print(home_url)
print(alarms_url)

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--ignore-ssl-errors')
chrome_options.add_argument('--disable-autofill')
chrome_options.add_experimental_option('prefs', {'download.default_directory': download_path,
                                                 'download.prompt_for_download': False,
                                                 'download.directory_upgrade': True,
                                                 'safebrowsing.enabled': True})

chrome_service = Service(chrome_driver_env)
driver = webdriver.Chrome(service=chrome_service, options=chrome_options)

try:
    driver.get(home_url)
    
    username_field = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="inputUserName"]')))
    username_field.send_keys(username)
    password_field = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="inputCiphercode"]')))
    password_field.send_keys(password)
    WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="loginBut"]'))).click()
    WebDriverWait(driver, 50).until(EC.url_to_be(home_url))

    time.sleep(2)
    driver.get(alarms_url)
    WebDriverWait(driver, 50).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="default"]/plx-dropdown-pop-window/div/div/div[3]/div/span'))).click()
    

    iframe = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "page-mainIframefm")))
    driver.switch_to.frame(iframe)

    export_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="operationBar"]/div[1]/div/div[1]/alarm-export/div/div/button'))) 
    export_btn.click()
    
    export_btn2 = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="fmbody"]/div/cmcc-export-operation[2]/export-operation'))) # //*[@id="fmbody"]/div/cmcc-export-operation[2]
    export_btn2.click()

    export_btn3 = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="exportOkBtn"]')))
    export_btn3.click()
    time.sleep(10)

finally:
    driver.quit()


