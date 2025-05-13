import os
import time
import zipfile
import pandas as pd
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
    """Функция скачивает архивированный файл с авариями из ZenicOne"""
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
        wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="loginBut"]'))).click()
        wait.until(EC.url_to_be(zenic_home_url))
        time.sleep(2)
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
        time.sleep(8)

    finally:
        try: 
            driver.switch_to.default_content()
            time.sleep(1)
            user_btn = driver.find_element(By.XPATH, '//*[@id="header_dropdown_user"]')
            user_btn.click()
            logout = driver.find_element(By.XPATH, '//*[@id="header_dropdown_user"]/div/ptl-user-dropdown/ul/li[5]/a')
            logout.click()
            time.sleep(1)
            logout_btn = driver.find_element(By.XPATH, '/html/body/plx-modal-window/div[2]/div/div[3]/div/div/button[1]') 
            logout_btn.click()
            time.sleep(2)
        except Exception:
            pass
        driver.quit()



def get_latest_zip_file(folder_path):
    """Возвращает путь к ластовому скачанному ZIP'y"""
    zip_files = list(Path(folder_path).glob('*.zip'))
    if not zip_files:
        raise FileNotFoundError('There is no ZIP files.')
    
    latest_zip = max(zip_files, key=lambda x: x.stat().st_mtime)
    return latest_zip


def extract_xlsx_from_zip(zip_filepath, extract_to_folder):
    """Извлекает xlsx файл из.zip"""
    with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
        zip_ref.extractall(extract_to_folder)
        extracted_files = zip_ref.namelist() # poluchil spisok faylov
    return extracted_files

def process_zenic_hightemp_excel(excel_filepath):
    df = pd.read_excel(excel_filepath)
    return df


def get_zenicone_alarms():
    """Func скачивает zip, извлекает xlsx, возвращает df с авариями."""
    download_zenic_hightemp_alarms() # Скачиваю зип

    zip_filepath = get_latest_zip_file(download_path) 
    extracted_files = extract_xlsx_from_zip(zip_filepath, download_path)

    excel_filepath = Path(download_path) / extracted_files[0]

    zenic_hightemp_alarms_df = process_zenic_hightemp_excel(excel_filepath)

    return zenic_hightemp_alarms_df


if __name__ == '__main__':
    df = get_zenicone_alarms()
    print(df.head())