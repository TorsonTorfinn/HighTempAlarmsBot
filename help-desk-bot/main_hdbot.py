import os
import logging
import asyncio
import websockets
import json
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.types import BufferedInputFile
from aiogram.enums import ParseMode
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime


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

alarm_storage = {}


async def send_to_telegram(bot, photo, caption, chat_id):
    try:
        await asyncio.sleep(7)
        if photo:
            await bot.send_photo(
                chat_id=chat_id,
                photo=BufferedInputFile(photo.read(), filename='table.png'),
                caption=caption,
                parse_mode='HTML')
            logger.info(f'Table Picture was sent to the chat: {chat_id}')
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=caption,
                parse_mode='HTML')
            logger.info(f'Message was sent to the chat - {chat_id}: {caption[:20]}...')
    except Exception as e:
        logger.error(f"Error while sending to the Telegram (chat_id={chat_id}): {e}")


def format_phone_numbers(phone_str):
    if not phone_str or phone_str == 'Unknow':
        return 'No actual data of phone numbers'
    return ', '.join([f'+{phone.strip()}' for phone in phone_str.split(',')])


def generate_table_image(alarms, ws_type): 
    if not alarms:
        return None
    
    sorted_alarms = sorted(
        alarms,
        key=lambda x: datetime.fromisoformat(x.get('alarmraisedtime', '0000-00-00T00:00:00').replace('Z', '+00:00')),
        reverse=True)

    columns = ['Site', 'Alarm', 'Occured Time', 'DG Engineer']
    rows = []
    for data in sorted_alarms:
        site = data.get('alarmobjectname', 'Unknown')
        alarm = data.get('codename', 'Unknown')
        alarm_time = data.get('alarmraisedtime', 'Unknown').replace('T', ' ')
        dg_engineer = data.get('dg_engineer', 'Unknown')
        rows.append([site, alarm, alarm_time, dg_engineer])
    
    fig, ax = plt.subplots(figsize=(12, len(rows) * 0.5 + 1))
    ax.axis('off')
    ax.set_title(f'Alarm Type: {ws_type.upper()}', fontsize=14, fontweight='bold')
    table = ax.table(cellText=rows, colLabels=columns, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.2)
    table.auto_set_column_width(col=range(len(columns)))

    buff = BytesIO()
    plt.savefig(buff, format='png', bbox_inches='tight')
    buff.seek(0)
    plt.close(fig)
    return buff

async def send_batch_messages(bot): # batch messages formatter
    while True:
        await asyncio.sleep(900)
        logger.info(f'Current state of Alarm Storage: {alarm_storage}')
        for region, types in alarm_storage.items():
            chat_id = REGION_GROUPS.get(region)
            if not chat_id:
                logger.warning(f'Region: {region} was not found in REGION_GROUPS')
                continue

            region_engineers_ncc = ENGINEERS.get(region, [])
            common_engineers_ncc = ENGINEERS.get('COMMON_ENGINEERS', [])
            ncc_engineers = list(set(region_engineers_ncc + common_engineers_ncc))
            ncc_tags = ', '.join([tag for tag in ncc_engineers if tag]) or 'No data NCC engineer tag data'

            has_alarms = False
            for ws_type, alarms in types.items():
                image_buff = generate_table_image(alarms, ws_type)
                if image_buff:
                    has_alarms = True
                    dg_engineers = set()
                    for data in alarms:
                        dg_engineer = data.get('dg_engineer', 'Unknown')
                        dg_engineer_phone = data.get('dg_engineer_phone', 'Unknown')
                        if dg_engineer != 'Unknown' and dg_engineer_phone != 'Unknown':
                            dg_engineers.add(f"{dg_engineer} ({format_phone_numbers(dg_engineer_phone)})")
                    
                    caption = (
                        f"Alarms in {region} in 15 min:\n\n"
                        f"DG engineers: {', '.join(dg_engineers) or 'No DG engineers data'}\n"
                        f"NCC engineers: {ncc_tags}"
                    )
                    logger.info(f"Creating caption for telegram notification {region}: {caption}")
                    await send_to_telegram(bot, image_buff, caption, chat_id)

            if not has_alarms:
                logger.info(f"There are no alarms about: {region} region")
            
        alarm_storage.clear()


async def websocket_handler(uri, ws_type, bot): # handling ws data into storage dict 
    while True:
        try:
            async with websockets.connect(uri) as ws_connection:
                logger.info(f'Successfully connected to the {uri}')
                while True:
                    message = await ws_connection.recv()
                    logger.info(f'Successfuly received message from ws: {uri}')
                    try:
                        data_list = json.loads(message)
                        for data in data_list:
                            region = data.get('region', 'Unknown')
                            logger.info(f'Processed: region={region}, ws_type={ws_type}, data={data}')
                            if region not in alarm_storage:
                                alarm_storage[region] = {}
                            if ws_type not in alarm_storage[region]:
                                alarm_storage[region][ws_type] = []
                            alarm_storage[region][ws_type].append(data)
                    except json.JSONDecodeError:
                        logger.error(f'JSON decode error: {message}')
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"Connection with {uri} was closed. Reconnecting in 5 sec...") 
        except Exception as e:
            logger.error(f'WebSocket error {uri}: {e}; Reconnect in 5 sec...')
        await asyncio.sleep(5)


async def main():
    bot = Bot(token=HD_TELEGRAM_TOKEN)
    dp = Dispatcher()
    tasks = [
        websocket_handler(os.getenv('WEBSOCKET_DOWN'), 'down', bot),
        websocket_handler(os.getenv('WEBSOCKET_POWER'), 'power', bot),
        send_batch_messages(bot)
    ]
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())

