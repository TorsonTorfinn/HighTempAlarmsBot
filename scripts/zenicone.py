import os
import time
from pathlib import Path
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

username = os.getenv('USERNAME_ZENIC')
password = os.getenv('PASSWORD_ZENIC')
chromedriver = os.getenv('chrome_driver')
download_path = os.getenv('zenic_alarm_download_path')
zenic_home_url = os.getenv('home_url')
zenic_alarms_url = os.getenv('alarms_url')


def get_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--disable-autofill')
    chrome_options.add_experimental_option('prefs',
                                           {
                                               'download.default_directory': download_path,
                                               'download.prompt_for_download': False,
                                               'download.directory_upgrade': True,
                                               'safebrowsing.enabled': True
                                           })
    
    service = Service(chromedriver)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver


def download_zenic_hightemp_alarms():
    driver = get_driver()
    try:
        driver.get(zenic_home_url)
        time.sleep(1)
        wait = WebDriverWait(driver, 40)
        username_field = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="inputUserName"]')))
        username_field.send_keys(username)
        time.sleep(1)
        password_field = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="inputCiphercode"]')))
        password_field.send_keys(password)
        time.sleep(1)
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="loginBut"]'))).click()
        wait.until(EC.url_to_be(zenic_home_url))
        time.sleep(3)
        driver.get(zenic_alarms_url)
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="default"]/plx-dropdown-pop-window/div/div/div[3]/div/span'))).click() 

        iframe = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "page-mainIframefm")))
        driver.switch_to.frame(iframe) 
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="condition-tree"]/button'))).click() 
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="1"]/div/div[2]/div[1]/span/span'))).click() 
        export_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="operationBar"]/div[1]/div/div[1]/alarm-export/div/div/button'))) 
        export_btn.click()
        
        export_btn2 = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="fmbody"]/div/cmcc-export-operation[2]/export-operation'))) 
        export_btn2.click()
        time.sleep(1)
        display_columns = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="exportDlg"]/div[1]/div/div[2]/label[2]/div')))
        display_columns.click()
        time.sleep(1)
        export_btn3 = WebDriverWait(driver, 40).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="exportOkBtn"]'))) 
        export_btn3.click()
        time.sleep(10)

    finally:
        driver.quit()


if __name__ == '__main__':
    download_zenic_hightemp_alarms()