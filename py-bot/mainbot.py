import os
import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.utils.markdown import hcode, hbold

# Загрузка переменных окружения
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('GROUP_ID')
API_URL = os.getenv('API_NIMS_HIGHTEMP')
API_TOKEN = os.getenv('TOKEN_NIMS_HIGHTEMP')

SENT_ALARMS_FILE = "sent_alarms.json" # файл для хранения отправленных аварий

bot = Bot(token=TELEGRAM_TOKEN)

def load_sent_alarms():
    """Функия загружает список отправленных аварий из JSON-файла"""
    try:
        with open(SENT_ALARMS_FILE, 'r') as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_sent_alarms(sent_alarms):
    """Функия сохраняет список отправленных аварий в JSON-файл"""
    with open(SENT_ALARMS_FILE, 'w') as f:
        json.dump(list(sent_alarms), f)

async def fetch_alarms():
    """Получение аварий с API вызова"""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Token {API_TOKEN}"}
        async with session.get(API_URL, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                print(f"Ошибка API: {response.status}")
                return []

async def send_alarm_message(alarm):
    """Отправляет сообщение о новой аварии"""
    try: # Преобразование времени
        start_time = datetime.fromisoformat(alarm['alarmraisedtime'].replace('Z', '+00:00'))
        formatted_time = start_time.strftime('%d %B %Y, %H:%M:%S')
    except (ValueError, KeyError):
        formatted_time = alarm.get('alarmraisedtime', 'Неизвестно')

    message = (
        f"\n"
        f"⚠️ {hbold('Link')}: {hcode(alarm['me'])}\n"
        f"📛 {hbold('Alarm')}: {hcode(alarm['codename'])}\n"
        f"💬 {hbold('Comment')}: {hcode(alarm['comment'])}\n"
        f"⏰ {hbold('Start Time')}: {hcode(formatted_time)}\n"
        f"🔗 {hbold('Sites Behind')}: {hcode(alarm['sitesbehind'])}\n"
    )

    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode='HTML'
    )

async def main():
    """Main Function: получает аварии, отправляет новые и обновляет список отправленных"""
    while True:
        sent_alarms = load_sent_alarms() # загрузка списка ранее отправленных аварий
        
        alarms = await fetch_alarms() # Получаем новые аварии
        
        if not alarms:
            print("Нет новых аварий для отправки.")
            save_sent_alarms(set())  # Чистка JSON, если нет аварий
        else:
            current_alarm_ids = {alarm['me'] for alarm in alarms} # множество линков текущих аварий из API
            
            # Фильтруем только новые аварии на линках (не отправленные ранее)
            new_alarms = [alarm for alarm in alarms if alarm['me'] not in sent_alarms] # was alarmcode now me
            
            if not new_alarms:
                print("Все аварии уже были отправлены.")
            else:
                print(f"Найдено {len(new_alarms)} новых аварий. Отправка в Telegram...")
                for i, alarm in enumerate(new_alarms, 1):
                    try:
                        await send_alarm_message(alarm)
                        sent_alarms.add(alarm['alarmcode'])  # Добавляем линк в отправленные
                        print(f"Отправлено {i}/{len(new_alarms)}")
                    except Exception as e:
                        print(f"Ошибка при отправке {i}-го сообщения: {e}")
                    await asyncio.sleep(5.0)

            # Обновляем JSON, оставляя только линки, которые всё ещё в API или только что отправлены
            updated_sent_alarms = sent_alarms & current_alarm_ids
            save_sent_alarms(updated_sent_alarms | {alarm['me'] for alarm in new_alarms}) # was alarmcode now me

        # Ждём 5 минут перед следующим циклом
        print("Ожидание 5 минут до следующей проверки...")
        await asyncio.sleep(300)

if __name__ == "__main__":
    asyncio.run(main())