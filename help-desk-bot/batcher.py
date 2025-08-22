import logging
from pathlib import Path
from dotenv import load_dotenv
import os
from aiogram import Bot, Dispatcher


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
HD_TELEGRAM_TOKEN = os.getenv('HD_TG_TOKEN')

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

alarms_storage = {}

async def send_to_telegram(bot, message, chat_id):
    pass

async def format_phones(phone_str):
    pass


async def format_table(alarms, ws_type):
    pass


async def send_batch_messages(bot):
    pass


async def websocket_handler(uri, ws_type, bot):
    pass 


async def main():
    bot = Bot(token=HD_TELEGRAM_TOKEN)
    dp = Dispatcher

    tasks = [
        websocket_handler(os.getenv('WEBSOCKET_DOWN'), "SITE DOWN", bot),
        websocket_handler(os.getenv('WEBSOCKET_POWER'), "MAINS POWER", bot),
        send_batch_messages(bot),
    ]

