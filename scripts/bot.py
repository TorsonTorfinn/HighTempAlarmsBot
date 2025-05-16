import asyncio
from analyze_data import get_alarms_to_send
from telegram_utils import send_alarm_message

async def main():
    """Главная функция: получает аварии и отправляет их по очереди с задержкой"""
    alarms = get_alarms_to_send()
    
    if not alarms:
        print("Нет новых аварий для отправки.")
        return

    print(f"Найдено {len(alarms)} новых аварий. Отправка в Telegram...")

    for i, alarm in enumerate(alarms, 1):
        try:
            await send_alarm_message(alarm)
            print(f"Отправлено {i}/{len(alarms)}")
        except Exception as e:
            print(f"Ошибка при отправке {i}-го сообщения: {e}")
        await asyncio.sleep(1.0)  # задержка 1 секунда

if __name__ == '__main__':
    asyncio.run(main())
