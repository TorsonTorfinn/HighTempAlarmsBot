from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv
import os
import asyncio

load_dotenv(dotenv_path='.env')

TG_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
GROUP_ID = int(os.getenv('GROUP_ID'))
print(GROUP_ID)
bot = Bot(token=TG_BOT_TOKEN)

async def send_test_message():
    try:
        await bot.send_message(chat_id=GROUP_ID, text='Тестовое сообщение, бот успешно запущен.')
        print("Сообщение успешно доставлено")
    except TelegramError as e:
        print(f'telegram error: {e}')
    

if __name__ == '__main__':
    asyncio.run(send_test_message())


