
import asyncio
from analyze_data import get_alarms_to_send
from telegram_utils import send_alarm_message

async def main():
    """Главная функция: получает аварии и отправляет их"""
    alarms = get_alarms_to_send()
    
    if not alarms:
        print("Нет новых аварий для отправки.")
        return

    print(f"Найдено {len(alarms)} новых аварий. Отправка в Telegram...")

    tasks = [send_alarm_message(alarm) for alarm in alarms]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
