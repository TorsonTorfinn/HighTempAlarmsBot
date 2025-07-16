import os
import asyncio
import logging
import websockets
import json
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv
from pathlib import Path

# setting logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# load env
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
HD_TELEGRAM_TOKEN = os.getenv('HD_TG_TOKEN')

# dict of region groups
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
}

# settin engineers dict
ENGINEERS = {
    "COMMON": os.getenv("COMMON_ENGINEERS").split(","),
    "ANDIJAN": os.getenv("ANDIJAN_ENGINEERS").split(","),
    "KHOREZM": os.getenv("KHOREZM_ENGINEERS").split(","),
    "KARAKALPAKISTAN": os.getenv("KARAKALPAKISTAN_ENGINEERS").split(","),
    "NAMANGAN": os.getenv("NAMANGAN_ENGINEERS").split(","),
    "SAMARKAND": os.getenv("SAMARKAND_ENGINEERS").split(","),
    "BUKHARA": os.getenv("BUKHARA_ENGINEERS").split(","),
    "NAVOI": os.getenv("NAVOI_ENGINEERS").split(","),
    "TASHKENT": os.getenv("TASHKENT_ENGINEERS").split(","),
    "FERGANA": os.getenv("FERGANA_ENGINEERS").split(","),
    "SURKHANDARYA": os.getenv("SURKHANDARYA_ENGINEERS").split(","),
    "SIRDARYA": os.getenv("SIRDARYA_ENGINEERS").split(","),
    "DJIZZAK": os.getenv("DJIZZAK_ENGINEERS").split(","),
    "KASHKADARYA": os.getenv("KASHKADARYA_ENGINEERS").split(","),
}

