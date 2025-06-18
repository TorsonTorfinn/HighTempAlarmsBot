# import asyncio
# from analyze_data import get_alarms_to_send
# from telegram_utils import send_alarm_message

# async def main():
#     """Главная функция: получает аварии и отправляет их по очереди с задержкой"""
#     alarms = get_alarms_to_send()
    
#     if not alarms:
#         print("Нет новых аварий для отправки.")
#         return

#     print(f"Найдено {len(alarms)} новых аварий. Отправка в Telegram...")

#     for i, alarm in enumerate(alarms, 1):
#         try:
#             await send_alarm_message(alarm)
#             print(f"Отправлено {i}/{len(alarms)}")
#         except Exception as e:
#             print(f"Ошибка при отправке {i}-го сообщения: {e}")
#         await asyncio.sleep(1.0)  # задержка 1 секунда

# if __name__ == '__main__':
#     asyncio.run(main())


import asyncio
from analyze_data import get_alarms_to_send
from telegram import Bot
from telegram_utils import send_alarm_message      # твоя функция
import os
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("GROUP_ID")
bot = Bot(token=TELEGRAM_TOKEN)


async def run_once():
    """
    Одна проверка: если есть аварии – рассылаем все по очереди,
    если нет – шлём «Нет новых аварий для отправки.»
    """
    alarms = get_alarms_to_send()

    if not alarms:
        print("Нет новых аварий для отправки.")
        try:
            await bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text="Нет новых аварий для отправки."
            )
        except Exception as e:
            print(f"Ошибка при отправке сообщения: {e}")
        return

    print(f"Найдено {len(alarms)} новых аварий. Отправка в Telegram...")
    for i, alarm in enumerate(alarms, 1):
        try:
            await send_alarm_message(alarm)
            print(f"Отправлено {i}/{len(alarms)}")
        except Exception as e:
            print(f"Ошибка при отправке {i}-го сообщения: {e}")
        await asyncio.sleep(1.0)      # пауза между сообщениями


async def main():
    """Запускаем run_once() каждые 5 минут бесконечно."""
    print("Бот запущен. Проверяем аварии каждые 5 минут…")
    while True:
        await run_once()
        await asyncio.sleep(300)       # 5 минут ожидания


if __name__ == "__main__":
    asyncio.run(main())



