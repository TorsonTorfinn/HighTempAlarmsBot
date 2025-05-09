import os 
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('GROUP_ID')

bot = Bot(token=TELEGRAM_TOKEN)

async def send_alarm_message(alarm):
    """Отправляет сообщение о новой аварии"""
    message = (
        f"\n"
        f"🆔 `{alarm['id']}`\n\n"

        f"⚠️ *Link*: `{alarm['link']}`\n"
        f"📛 *Alarm*: `{alarm['alarm_name']}`\n"
        f"🚨 *Severity*: `{alarm['alarm_severity']}`\n"
        f"🔌 *Position*: `{alarm['position']}`\n"
        f"⏰ *Start Time*: `{alarm['start_time']}`\n"
        f"⚙️ *Sites Behind Count*: `{alarm['sites_behind']}`\n"
        f"🔗 *Sites Behind*: `{alarm['mess']}`\n"
    )

    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode='Markdown'
    )
