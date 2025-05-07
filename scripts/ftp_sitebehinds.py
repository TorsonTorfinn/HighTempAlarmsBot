import os
import re
from pathlib import Path
from ftplib import FTP
from dotenv import load_dotenv
from datetime import datetime

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

ftp_host = os.getenv('FTP_SITEBEHIND_HOST')
ftp_user = os.getenv('FTP_SITEBEHIND_USER')
ftp_pass = os.getenv('FTP_SITEBEHIND_PASS')
ftp_dir = '/sitebehind'
local_download_path = Path(os.getenv('sitebehind_download_path'))

FILENAME_REGEX = re.compile(r'(\d{4}-\d{2}-\d{2})_rr_sitebehinds\.csv')


def parse_date_from_filename(filename):
    match = FILENAME_REGEX.search(filename)
    if match:
        return datetime.strptime(match.group(1), '%Y-%m-%d')
    return None


def download_latest_ftp_file():
    ftp = FTP(ftp_host)
    ftp.login(ftp_user, ftp_pass)
    ftp.cwd(ftp_dir)

    files = ftp.nlst()
    filtered_files = []
    for filename in files:
        if FILENAME_REGEX.match(filename):
            file_date = parse_date_from_filename(filename)
            if file_date:
                filtered_files.append((filename, file_date))

    if not filtered_files:
        print(f"There's no files.")
        ftp.quit()
        return
    
    filtered_files.sort(key=lambda x: x[1], reverse=True)
    latest_file = filtered_files[0][0]
    local_file_path = local_download_path / latest_file

    with open(local_file_path, 'wb') as f:
        ftp.retrbinary(f"RETR {latest_file}", f.write)
    
    ftp.quit()
    print(f"File {latest_file} successfully downloaded in {local_file_path}")

if __name__ == '__main__':
    download_latest_ftp_file()