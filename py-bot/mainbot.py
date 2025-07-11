import os
import asyncio
import aiohttp
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.utils.markdown import hcode, hbold, hlink
from aiogram.client.session.aiohttp import AiohttpSession

# логированиe с ротацией + консольны вывод
handler = RotatingFileHandler('bot.log', maxBytes=50*1024*1024, backupCount=25) # 50 mb, 25 archives
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.basicConfig(
    handlers=[handler, console_handler],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('GROUP_ID') # reserved chat_id
API_URL = os.getenv('API_NIMS_HIGHTEMP')
API_TOKEN = os.getenv('TOKEN_NIMS_HIGHTEMP')
PROXY_URL = os.getenv('PROXY_URL')

SENT_ALARM_FILE = 'sent_alarms.json'  

COMMON_ENGINEERS = [username.strip() for username in os.getenv('COMMON_ENGINEERS', '').split(',') if username.strip()]
REGION_ENGINEERS = {}
regions = ["TASHKENTREGION","ANDIJAN","NAMANGAN","FERGANA","TASHKENT","BUKHARA","SURKHANDARYA","DJIZZAK","SIRDARYA","NAVOI","SAMARKAND","KHOREZM","KARAKALPAKISTAN","KASHKADARYA"]
for region in regions:
    engineers_key = 'TASHKENT_ENGINEERS' if region == 'TASHKENTREGION' else f'{region}_ENGINEERS' # Для TASHKENTREGION используем TASHKENT_ENGINEERS
    engineers_str = os.getenv(engineers_key, '')
    if engineers_str:
        REGION_ENGINEERS['region'] = [username.strip() for username in engineers_str.split(',') if username.strip()]

# init the highTempBot
bot = Bot(token=TELEGRAM_TOKEN, session=AiohttpSession(proxy=str(PROXY_URL))) # , session=AiohttpSession(proxy=str(PROXY_URL))


def get_region(alarm):
    me = alarm.get('me', '')
    region = alarm.get('region', '').strip().upper()
    """Определяет ID Telegram-группы по первым двум символам site_id из переменных окружения"""
    region_mapping = {
        'ANDIJAN': os.getenv('CHAT_ID_AN'),
        'BUKHARA': os.getenv('CHAT_ID_BH'),
        'DJIZZAK': os.getenv('CHAT_ID_DZ'),
        'FERGANA': os.getenv('CHAT_ID_FR'),
        'KARAKALPAKISTAN': os.getenv('CHAT_ID_KR'),
        'KASHKADARYA': os.getenv('CHAT_ID_KS'),
        'KHOREZM': os.getenv('CHAT_ID_KH'),
        'NAVOI': os.getenv('CHAT_ID_NV'),
        'SAMARKAND': os.getenv('CHAT_ID_SM'),
        'SIRDARYA': os.getenv('CHAT_ID_SR'),
        'SURKHANDARYA': os.getenv('CHAT_ID_SU'),
    }

    if region and region in region_mapping:
        chat_id = region_mapping.get(region)
        if chat_id:
            logging.info(f"Using API region {region} with chat_id {chat_id} for alarms {me}")
            return chat_id, region
        else:
            logging.warning(f"No chat_id found for API region {region} for alarm {me}")
        
    # Fallback регион из API
    chat_id = TELEGRAM_CHAT_ID
    logging.warning(f"Invalid or missing region {region} for alarm {me}, using default chat id {chat_id}")
    return chat_id, region if region else "UNKNOWN"



def load_sent_alarms():
    """Функция загружает список отправленных аварий из JSON-файла"""
    try:
        with open(SENT_ALARM_FILE, 'r') as file:
            sent_alarms = set(json.load(file))
            logging.debug(f"Loaded {len(sent_alarms)} sent alarms from {SENT_ALARM_FILE}")
            return sent_alarms
    except (FileNotFoundError, json.JSONDecodeError):
        logging.info(f"No existing alarms file found or invalid JSON, starting with empty set.")
        return set()
    

def save_sent_alarms(sent_alarms):
    """Функция сохраняет список отправленных аварий в JSON-файл"""
    try:
        with open(SENT_ALARM_FILE, 'w') as file:
            json.dump(list(sent_alarms), file)
        logging.debug(f"Saved {len(sent_alarms)} alarms to {SENT_ALARM_FILE}")
    except Exception as e:
        logging.error(f"Failed to save alarms to {SENT_ALARM_FILE}: {e}")


async def fetch_alarms():
    """Функция получает аварии с API NIMS"""
    try: 
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Token {API_TOKEN}"}
            async with session.get(API_URL, headers=headers, ssl=False) as response:
                if response.status == 200:
                    data = await response.json()
                    logging.debug(f"Received API response with {len(data)} alarms")
                    return data
                else:
                    logging.error(f"API error: {response.status}")
                    return []
    except Exception as e:
        logging.error(f"Failed to fetch alarms from API: {e}")
        return []
            

async def send_alarm_message(alarm):
    """Функция отправляет сообщение о новой аварии в соответствующую региональную группу"""
    try:
        start_time = datetime.fromisoformat(alarm['alarmraisedtime'].replace('Z', '+00:00'))
        start_time = start_time.astimezone(timezone(timedelta(hours=5))) # +05:00
        formatted_time = start_time.strftime('%d.%m.%Y %H:%M:%S')
    except (ValueError, KeyError) as e:
        formatted_time = alarm.get('alarmraisedtime', 'Неизвестно')
        logging.warning(f"Failed to format time for alarm {alarm.get('me', 'unknown')}: {e}")

    me = alarm.get('me', '')
    chat_id, region = get_region(alarm)
    if chat_id is None:
        logging.error(f"Skipping message for alarm {me}: no valid chat_id")
        return
    logging.debug(f"Sending message for alarm {me} to chat_id {chat_id}")

    # forming engineers mention
    engineer_mentions = COMMON_ENGINEERS.copy() 
    # for TASHKENTREGION we r using TASHKENT ENGINEERS
    engineer_region = 'TASHKENT' if region == 'TASHKENTREGION' else region 
    region_engineers = REGION_ENGINEERS.get(engineer_region, [])
    if not region_engineers:
        logging.warning(f"No engineers defined for region {engineer_region}")
    engineer_mentions.extend(region_engineers)


    engineers_text = f"👷 {hbold('Инженеры')}: {', '.join(engineer_mentions)}\n" if engineer_mentions else ""

    message = (
        f"\n"
        f"⚠️ {hbold('Link')}: {hcode(alarm['me'])}\n"
        f"📛 {hbold('Alarm')}: {hcode(alarm['codename'])}\n"
        f"💬 {hbold('Comment')}: {hcode(alarm['comment'])}\n"
        f"⏰ {hbold('Start Time')}: {hcode(formatted_time)}\n"
        f"🔗 {hbold('Sites Behind')}: {hcode(alarm['sitesbehind'])}\n"
        f"{hbold('Last 3 days count')}: {hcode(alarm['last_3days_count'])}"
        f"{engineers_text}"
    )

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='HTML'
        )
        logging.info(f"Sent message for alarm on link {me} to chat_id {chat_id}")
    except Exception as e:
        logging.error(f"Failed to send message for alarm {me} to chat_id {chat_id}: {e}")


async def main():
    """Main Function: получает аварии, отправляет новые и обновляет список отправленных"""
    while True:
        sent_alarms = load_sent_alarms()
        links_with_hightemp = await fetch_alarms()

        if not links_with_hightemp:
            logging.info("Нет новых аварий для отправки.")
            save_sent_alarms(set())
        else:
            current_hightemp_links = {link['me'] for link in links_with_hightemp}
            new_hightemp_alarms = [link for link in links_with_hightemp if link['me'] not in sent_alarms]

            if not new_hightemp_alarms:
                logging.info("Аварии уже были отправлены, новых нет.")
            else:
                logging.info(f"Найдено {len(new_hightemp_alarms)} новых аварий. Отправка в Telegram...")
                for i, link in enumerate(new_hightemp_alarms, 1):
                    try:
                        await send_alarm_message(link)
                        sent_alarms.add(link['me'])
                        logging.info(f"Отправлено {i}/{len(new_hightemp_alarms)}")
                    except Exception as e:
                        logging.error(f"Ошибка при отправке {i}-го сообщения: {e}")
                    await asyncio.sleep(6.0)
        
            updated_sent_alarms = sent_alarms & current_hightemp_links
            save_sent_alarms(updated_sent_alarms | {link['me'] for link in new_hightemp_alarms})
        
        logging.info("Ожидание 5 минут до следующей проверки...")
        await asyncio.sleep(300)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info('Bot stopped by User')
    except Exception as e:
        logging.error(f"Unexpected error in main: {e}")

























# import os
# import asyncio
# import aiohttp
# import json
# from datetime import datetime
# from pathlib import Path
# from dotenv import load_dotenv
# from aiogram import Bot
# from aiogram.utils.markdown import hcode, hbold

# # Загрузка переменных окружения
# env_path = Path(__file__).resolve().parent.parent / '.env'
# load_dotenv(dotenv_path=env_path)

# TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# TELEGRAM_CHAT_ID = os.getenv('GROUP_ID')
# API_URL = os.getenv('API_NIMS_HIGHTEMP')
# API_TOKEN = os.getenv('TOKEN_NIMS_HIGHTEMP')

# SENT_ALARMS_FILE = "sent_alarms.json" # файл для хранения отправленных аварий

# bot = Bot(token=TELEGRAM_TOKEN)

# def load_sent_alarms():
#     """Функия загружает список отправленных аварий из JSON-файла"""
#     try:
#         with open(SENT_ALARMS_FILE, 'r') as f:
#             return set(json.load(f))
#     except (FileNotFoundError, json.JSONDecodeError):
#         return set()

# def save_sent_alarms(sent_alarms):
#     """Функия сохраняет список отправленных аварий в JSON-файл"""
#     with open(SENT_ALARMS_FILE, 'w') as f:
#         json.dump(list(sent_alarms), f)

# async def fetch_alarms():
#     """Получение аварий с API вызова"""
#     async with aiohttp.ClientSession() as session:
#         headers = {"Authorization": f"Token {API_TOKEN}"}
#         async with session.get(API_URL, headers=headers) as response:
#             if response.status == 200:
#                 data = await response.json()
#                 return data
#             else:
#                 print(f"Ошибка API: {response.status}")
#                 return []

# async def send_alarm_message(alarm):
#     """Отправляет сообщение о новой аварии"""
#     try: # Преобразование времени
#         start_time = datetime.fromisoformat(alarm['alarmraisedtime'].replace('Z', '+00:00'))
#         formatted_time = start_time.strftime('%d %B %Y, %H:%M:%S')
#     except (ValueError, KeyError):
#         formatted_time = alarm.get('alarmraisedtime', 'Неизвестно')

#     message = (
#         f"\n"
#         f"⚠️ {hbold('Link')}: {hcode(alarm['me'])}\n"
#         f"📛 {hbold('Alarm')}: {hcode(alarm['codename'])}\n"
#         f"💬 {hbold('Comment')}: {hcode(alarm['comment'])}\n"
#         f"⏰ {hbold('Start Time')}: {hcode(formatted_time)}\n"
#         f"🔗 {hbold('Sites Behind')}: {hcode(alarm['sitesbehind'])}\n"
#     )

#     await bot.send_message(
#         chat_id=TELEGRAM_CHAT_ID,
#         text=message,
#         parse_mode='HTML'
#     )

# async def main():
#     """Main Function: получает аварии, отправляет новые и обновляет список отправленных"""
#     while True:
#         sent_alarms = load_sent_alarms() # загрузка списка ранее отправленных аварий
        
#         alarms = await fetch_alarms() # Получаем новые аварии
        
#         if not alarms:
#             print("Нет новых аварий для отправки.")
#             save_sent_alarms(set())  # Чистка JSON, если нет аварий
#         else:
#             current_alarm_ids = {alarm['me'] for alarm in alarms} # множество линков текущих аварий из API
            
#             # Фильтруем только новые аварии на линках (не отправленные ранее)
#             new_alarms = [alarm for alarm in alarms if alarm['me'] not in sent_alarms] # was alarmcode now me
            
#             if not new_alarms:
#                 print("Все аварии уже были отправлены.")
#             else:
#                 print(f"Найдено {len(new_alarms)} новых аварий. Отправка в Telegram...")
#                 for i, alarm in enumerate(new_alarms, 1):
#                     try:
#                         await send_alarm_message(alarm)
#                         sent_alarms.add(alarm['me'])  # Добавляем линк в отправленные, исправлено alarmcode на me
#                         print(f"Отправлено {i}/{len(new_alarms)}")
#                     except Exception as e:
#                         print(f"Ошибка при отправке {i}-го сообщения: {e}")
#                     await asyncio.sleep(5.0)

#             # Обновляем JSON, оставляя только линки, которые всё ещё в API или только что отправлены
#             updated_sent_alarms = sent_alarms & current_alarm_ids
#             save_sent_alarms(updated_sent_alarms | {alarm['me'] for alarm in new_alarms}) # was alarmcode now me

#         # Ждём 5 минут перед следующим циклом
#         print("Ожидание 5 минут до следующей проверки...")
#         await asyncio.sleep(300)

# if __name__ == "__main__":
#     asyncio.run(main())
    

