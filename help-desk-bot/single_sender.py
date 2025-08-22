import os
import asyncio
import logging
import websockets
import json
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка .env
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
HD_TELEGRAM_TOKEN = os.getenv('HD_TG_TOKEN')

# Словарь групп Telegram
REGION_GROUPS = {
    "ANDIJAN": int(os.getenv("TEST_CHAT_ID_AN")),
    "BUKHARA": int(os.getenv("TEST_CHAT_ID_BH")),
    "DJIZZAK": int(os.getenv("TEST_CHAT_ID_DZ")),
    "FERGANA": int(os.getenv("TEST_CHAT_ID_FR")),
    "KHOREZM": int(os.getenv("TEST_CHAT_ID_KR")),
    "KASHKADARYA": int(os.getenv("TEST_CHAT_ID_KS")),
    "KARAKALPAKISTAN": int(os.getenv("TEST_CHAT_ID_KH")),
    "NAVOI": int(os.getenv("TEST_CHAT_ID_NV")),
    "SAMARKAND": int(os.getenv("TEST_CHAT_ID_SM")),
    "SIRDARYA": int(os.getenv("TEST_CHAT_ID_SR")),
    "SURKHANDARYA": int(os.getenv("TEST_CHAT_ID_SU")),
    "TASHKENT": int(os.getenv("TEST_CHAT_ID_TS")),
    "TASHKENTREGION": int(os.getenv("TEST_CHAT_ID_TS")),  # То же chat_id, что для TASHKENT
}

# Словарь инженеров
ENGINEERS = {
    "COMMON": os.getenv("COMMON_ENGINEERS").split(","),
    "ANDIJAN": os.getenv("HD_ANDIJAN_ENGINEERS").split(","),
    "KHOREZM": os.getenv("HD_KHOREZM_ENGINEERS").split(","),
    "KARAKALPAKISTAN": os.getenv("HD_KARAKALPAKISTAN_ENGINEERS").split(","),
    "NAMANGAN": os.getenv("HD_NAMANGAN_ENGINEERS").split(","),
    "SAMARKAND": os.getenv("HD_SAMARKAND_ENGINEERS").split(","),
    "BUKHARA": os.getenv("HD_BUKHARA_ENGINEERS").split(","),
    "NAVOI": os.getenv("HD_NAVOI_ENGINEERS").split(","),
    "TASHKENT": os.getenv("HD_TASHKENT_ENGINEERS").split(","),
    "FERGANA": os.getenv("HD_FERGANA_ENGINEERS").split(","),
    "SURKHANDARYA": os.getenv("HD_SURKHANDARYA_ENGINEERS").split(","),
    "SIRDARYA": os.getenv("HD_SIRDARYA_ENGINEERS").split(","),
    "DJIZZAK": os.getenv("HD_DJIZZAK_ENGINEERS").split(","),
    "KASHKADARYA": os.getenv("HD_KASHKADARYA_ENGINEERS").split(","),
}

async def send_to_telegram(bot, message, chat_id):
    """Отправка сообщения в Telegram-группу с задержкой."""
    try:
        await asyncio.sleep(7)  # Задержка 7 секунд перед отправкой
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Сообщение отправлено в чат {chat_id}: {message}")
    except Exception as e:
        logger.error(f"Ошибка при отправке в Telegram (chat_id={chat_id}): {e}")

async def format_message(data, ws_type):
    """Форматирование сообщения для Telegram."""
    site = data.get('alarmobjectname', 'Unknown')
    alarm_code_name = data.get('codename', 'Unknown')
    alarm_time = data.get('alarmraisedtime', 'Unknown')
    comment = data.get('comment', 'Unknown')
    power_alarm = data.get('power', 'Unknown')
    dg_start = data.get('dg', 'Unknown')
    battery_low = data.get('battery', 'Unknown')
    door_alarm = data.get('door', 'Unknown')
    sites_behind = data.get('sitesbehind', 'Unknown')
    dg_engineer = data.get('dg_engineer', 'Unknown')
    dg_engineer_phone = data.get('dg_engineer_phone', 'Unknown')
    region = data.get('region', 'Unknown')

    # Получаем инженеров для региона и общие инженеры
    region_engineers = ENGINEERS.get(region, [])
    common_engineers = ENGINEERS.get('COMMON', [])
    all_engineers = list(set(region_engineers + common_engineers))

    # Форматируем имена инженеров и телефоны
    engineer_mentions = ', '.join(all_engineers) if all_engineers else 'Нет данных'
    engineer_names = dg_engineer if dg_engineer != 'Unknown' else 'Нет данных'
    # Добавляем + к номерам телефонов
    if dg_engineer_phone != 'Unknown':
        phones = ', '.join([f'+{phone.strip()}' for phone in dg_engineer_phone.split(',')])
    else:
        phones = 'Нет данных'

    if ws_type == 'power':
        message = (
            "🚨 Mains Power\n"
            f"🏢 Site: {site}\n"
            f"⚠️ Alarm: {alarm_code_name}\n"
            f"⏰ Mains Power from: {alarm_time}\n"
            f"🔋 Battery Low: {battery_low}\n"
            f"⚙️ DG started From: {dg_start}\n"
            f"🚪 Door opened From: {door_alarm}\n"
            f"📝 Comments: {comment}\n"
            f"🔗 Sites Behind: {sites_behind}\n"
            f"👷 NCC Engineers: {engineer_mentions}\n"
            f"👤 DG Engineers: {engineer_names}\n"
            f"📞 Phone: {phones}"
        )
    elif ws_type == 'sitedown':
        message = (
            "🚨 Site Down\n"
            f"🏢 Site: {site}\n"
            f"⚠️ Alarm: {alarm_code_name}\n"
            f"⏰ Site Down From: {alarm_time}\n"
            f"🔌 Mains Power From: {power_alarm}\n"
            f"🔋 Battery Low From: {battery_low}\n"
            f"⚙️ DG started From: {dg_start}\n"
            f"🚪 Door opened From: {door_alarm}\n"
            f"📝 Cooment: {comment}\n"
            f"🔗 Sites Behinds: {sites_behind}\n"
            f"👷 NCC Engineers: {engineer_mentions}\n"
            f"👤 DG Engineers: {engineer_names}\n"
            f"📞 Phone: {phones}"
        )
    else:
        logger.error(f"Неизвестный тип WebSocket: {ws_type}")
        message = None
    return message, region

async def websocket_handler(uri, ws_type, bot):
    """Обработка WebSocket-соединения."""
    while True:
        try:
            async with websockets.connect(uri) as ws:
                logger.info(f"Успешно подключено к {uri}")
                while True:
                    message = await ws.recv()
                    try:
                        data_list = json.loads(message)
                        for data in data_list:
                            message_text, region = await format_message(data, ws_type)
                            if message_text is None:
                                continue
                            chat_id = REGION_GROUPS.get(region)
                            if chat_id:
                                await send_to_telegram(bot, message_text, chat_id)
                            else:
                                logger.warning(f"Регион {region} не найден в REGION_GROUPS")
                    except json.JSONDecodeError:
                        logger.error(f"Ошибка декодирования JSON: {message}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Соединение с {uri} закрыто. Повтор через 5 секунд...")
        except Exception as e:
            logger.error(f"Ошибка WebSocket {uri}: {e}. Повтор через 5 секунд...")
        await asyncio.sleep(5)

async def main():
    """Запуск бота и WebSocket-обработчиков."""
    bot = Bot(token=HD_TELEGRAM_TOKEN)
    dp = Dispatcher()

    tasks = [
        websocket_handler(os.getenv('WEBSOCKET_DOWN'), "SITE DOWN", bot),
        websocket_handler(os.getenv('WEBSOCKET_POWER'), "MAINS POWER", bot),
    ]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())