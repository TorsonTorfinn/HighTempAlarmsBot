"""
Данный модуль отвечает за фильтрацию данных, которые получаются из модулей zenic & ftp_sitebehinds, а также за анализ и подготовку данных для дальнейшей отправил через бота.
1. Фильтрация аварий из ZenicOne (ZTE);
2. Сравнение с данными из файла SiteBehinds;
3. Логика отправки сообщений без дублирования.
"""

import json
from pathlib import Path
from zenicone import get_zenicone_alarms
from ftp_sitebehinds import download_latest_ftp_file, read_sitebehinds_csv

SENT_ALARMS_PATH = Path(__file__).resolve().parent.parent / 'data' / 'sent_alarms.json'

from dotenv import load_dotenv
import os

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

ftp_params = (
    os.getenv('FTP_SITEBEHIND_HOST'),
    os.getenv('FTP_SITEBEHIND_USER'),
    os.getenv('FTP_SITEBEHIND_PASS')
)


def load_sent_alarms():
    """Загружает уже отправленные аварии из json"""
    if SENT_ALARMS_PATH.exists():
        with open(SENT_ALARMS_PATH, 'r', encoding='utf-8') as jf:
            return set(json.load(jf))
    return set()


def save_sent_alarms(sent_alarms):
    """Сохраняет обновлённый список отправленных аварий"""
    with open(SENT_ALARMS_PATH, 'w', encoding='utf-8') as jf:
        json.dump(list(sent_alarms), jf, indent=2)


def get_alarms_to_send():
    """main func-загружает данные, фильтрует и отдаёт список новых аварий"""
    df_zenic = get_zenicone_alarms() # loading alarms from zenicone

    # load the data about sites behind
    sitebehind_filepath = download_latest_ftp_file(*ftp_params)
    df_sitebehind = read_sitebehinds_csv(sitebehind_filepath)

    filtered_alarms = filter_alarms(df_zenic, df_sitebehind) # doing filtration of alarms

    sent_alarms = load_sent_alarms() #загружаем уже отправленные аварии

    current_alarm_ids = set([alarm['id'] for alarm in filtered_alarms]) # уник множество id актуальных аварий

    updated_sent_alarms = sent_alarms.intersection(current_alarm_ids) # delete from json unactive alarms, updating form zenicone uploaded files

    new_alarms = []
    new_sent_ids = set()
    for alarm in filtered_alarms:
        alarm_id = alarm['id']
        if alarm_id not in sent_alarms:
            new_alarms.append(alarm)
            new_sent_ids.add(alarm_id)

    final_sent_alarms = updated_sent_alarms.union(new_sent_ids)
    save_sent_alarms(final_sent_alarms)

    return new_alarms


def filter_alarms(df_zenic, df_sitebehind):
    """фильтрует аварии зеника"""
    df_filtered_sitebehind = df_sitebehind[df_sitebehind['SITES_BEHIND'] >= 2]
    sitebehind_dict = dict(zip(df_filtered_sitebehind['SITEB'], zip(df_filtered_sitebehind['MESS'], df_filtered_sitebehind['SITES_BEHIND'])))
    filtered_alarms = []

    for _, row in df_zenic.iterrows():
        link = row['ME']
        left_side = link[:6]

        mess_info = sitebehind_dict.get(left_side) # есть ли сайт из zenicOne в siteB больше отборки >= 2 sites behind
        
        if mess_info:
            mess, sites_behind = mess_info
            alarm = {
                'id': f'{link}-{row['Alarm Code']}',
                'link': link,
                'alarm_name': row['Alarm Code Name'],
                'alarm_severity': row['Alarm Severity'],
                'comment': row['Comment Information'],
                'start_time': row['Occurrence Time'],
                'mess': mess,
                'sites_behind': sites_behind
            }
            filtered_alarms.append(alarm)

    return filtered_alarms

if __name__ == '__main__':
    alarms = get_alarms_to_send()
    for alarm in alarms:
        print(alarm)