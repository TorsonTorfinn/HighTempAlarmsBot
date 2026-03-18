import asyncio
import os
import json
from datetime import datetime
from collections import defaultdict

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

# ================= CONFIG =================
API_URL = os.getenv("NIMS_API_ACTIVE_ALARMS")
API_TOKEN = os.getenv("NIMS_TOKEN")

BOT_TOKEN = os.getenv("NCC_OPER_BOT_TOKEN")
CHAT_ID = int(os.getenv("NCC_OPER_CHAT_ID"))

CHECK_INTERVAL = 15
REPORT_INTERVAL = 60
POWER_THRESHOLD = 9

STATE_FILE = "state.json"

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# ================= STATE =================
def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


state = load_state()
last_stats = {}

# ================= API =================
async def fetch_alarms():
    headers = {"Authorization": API_TOKEN}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers, ssl=False) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    print("API STATUS:", resp.status)

    except Exception as e:
        print("API ERROR:", e)

    return []


# ================= PROCESS =================
def process_alarms(data):
    stats = defaultdict(lambda: {
        "power": 0,
        "dg": 0,
        "mg": 0,
        "site_down": 0
    })

    for alarm in data:
        region = (alarm.get("region") or "UNKNOWN").upper()
        alarmtype = alarm.get("alarmtype") or ""
        name = alarm.get("alarmobjectname", "")

        if alarmtype == "power":
            stats[region]["power"] += 1

        elif alarmtype == "dg":
            if "_FG_" in name:
                stats[region]["dg"] += 1
            else:
                stats[region]["mg"] += 1

        elif alarmtype == "site_down":
            stats[region]["site_down"] += 1

    return stats


# ================= MO LOGIC =================
async def update_state(stats):
    finished_regions = []

    for region, values in stats.items():
        power = values["power"]

        if region not in state:
            state[region] = {
                "mo_active": False,
                "mo_start_time": None,
                "power_below_count": 0
            }

        region_state = state[region]

        # START MO
        if power >= POWER_THRESHOLD and not region_state["mo_active"]:
            region_state["mo_active"] = True
            region_state["mo_start_time"] = datetime.now().strftime("%d.%m.%Y %H:%M")
            region_state["power_below_count"] = 0

        # CHECK END MO
        elif power < POWER_THRESHOLD and region_state["mo_active"]:
            region_state["power_below_count"] += 1

            if region_state["power_below_count"] >= 2:
                region_state["mo_active"] = False
                region_state["mo_start_time"] = None
                region_state["power_below_count"] = 0

                finished_regions.append(region)

        else:
            region_state["power_below_count"] = 0

    return finished_regions


# ================= IMAGE =================
def generate_image(stats):
    regions = sorted([
        r for r in stats
        if state.get(r, {}).get("mo_active")
    ])

    if not regions:
        return None

    rows = [
        "Время МО ЭП",
        "Нет ЭП",
        "ДГ",
        "МГ",
        "Кол-во недоступных БС"
    ]

    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()

    # ===== helper =====
    def text_size(text):
        return font.getbbox(str(text))[2]

    def draw_center(draw, xy, box_w, box_h, text, bold=False):
        w = text_size(text)
        x = xy[0] + (box_w - w) // 2
        y = xy[1] + (box_h - 18) // 2

        if bold:
            draw.text((x+1, y), str(text), fill="black", font=font)
        draw.text((x, y), str(text), fill="black", font=font)

    # ===== calculate dynamic widths =====
    col_widths = []

    # первая колонка (названия строк)
    first_col_width = max(text_size(r) for r in rows + ["Регион"]) + 40
    col_widths.append(first_col_width)

    # остальные колонки (по регионам)
    for region in regions:
        max_text = region

        values = [
            state[region]["mo_start_time"] or "",
            stats[region]["power"],
            stats[region]["dg"],
            stats[region]["mg"],
            stats[region]["site_down"]
        ]

        for v in values:
            if text_size(v) > text_size(max_text):
                max_text = v

        col_widths.append(text_size(max_text) + 40)

    row_height = 50

    width = sum(col_widths)
    height = row_height * (len(rows) + 1)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # ===== рисуем сетку =====
    x = 0
    for w in col_widths:
        draw.line((x, 0, x, height), fill="black", width=2)
        x += w
    draw.line((x, 0, x, height), fill="black", width=2)

    for i in range(len(rows) + 2):
        y = i * row_height
        draw.line((0, y, width, y), fill="black", width=2)

    # ===== жёлтая шапка =====
    x = 0
    for w in col_widths:
        draw.rectangle((x, 0, x + w, row_height), fill="#FFF59D")
        x += w

    # ===== header =====
    x = 0
    draw_center(draw, (x, 0), col_widths[0], row_height, "Регион", bold=True)

    x += col_widths[0]

    for i, region in enumerate(regions):
        draw_center(draw, (x, 0), col_widths[i+1], row_height, region, bold=True)
        x += col_widths[i+1]

    # ===== rows =====
    for r, row_name in enumerate(rows):
        y = row_height * (r + 1)

        # первая колонка
        draw_center(draw, (0, y), col_widths[0], row_height, row_name)

        x = col_widths[0]

        for i, region in enumerate(regions):
            if row_name == "Время МО ЭП":
                val = state[region]["mo_start_time"] or ""

            elif row_name == "Нет ЭП":
                val = stats[region]["power"]

            elif row_name == "ДГ":
                val = stats[region]["dg"]

            elif row_name == "МГ":
                val = stats[region]["mg"]

            elif row_name == "Кол-во недоступных БС":
                val = stats[region]["site_down"]

            draw_center(draw, (x, y), col_widths[i+1], row_height, val)
            x += col_widths[i+1]

    path = "report.png"
    img.save(path)

    return path


# ================= SEND =================
from aiogram.types import FSInputFile

async def send_report(stats):
    active_regions = [r for r in stats
        if state.get(r, {}).get("mo_active")]

    if not active_regions:
        print("NO ACTIVE MO - SKIP REPORT")
        return

    path = generate_image(stats)
    photo = FSInputFile(path)
    await bot.send_photo(chat_id=CHAT_ID, photo=photo)


async def send_finished(regions):
    for region in regions:
        await bot.send_message(
            CHAT_ID,
            f"✅ В регионе <b>{region}</b> массовые отключения завершены"
        )


# ================= JOBS =================
async def check_job():
    global last_stats

    print("CHECKING API...")

    data = await fetch_alarms()
    stats = process_alarms(data)

    finished = await update_state(stats)

    if finished:
        await send_finished(finished)

    save_state(state)

    last_stats = stats


async def report_job():
    print("SENDING REPORT...")

    if last_stats:
        await send_report(last_stats)
    else:
        print("NO DATA YET")


# ================= MAIN =================
async def main():
    scheduler = AsyncIOScheduler()

    scheduler.add_job(check_job, "interval", minutes=CHECK_INTERVAL)
    scheduler.add_job(report_job, "interval", minutes=REPORT_INTERVAL)

    scheduler.start()

    # 👉 первый запуск сразу
    await check_job()
    await report_job()

    print("BOT STARTED")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())