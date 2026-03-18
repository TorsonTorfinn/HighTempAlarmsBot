import asyncio
import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from collections import defaultdict
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# ================= CONFIG =================
API_URL = os.getenv("NIMS_API_ACTIVE_ALARMS")
API_TOKEN = os.getenv("NIMS_TOKEN")

BOT_TOKEN = os.getenv("NCC_OPER_BOT_TOKEN")
CHAT_ID = int(os.getenv("NCC_OPER_CHAT_ID"))

CHECK_INTERVAL = 15
REPORT_INTERVAL = 60
POWER_THRESHOLD = 40

STATE_FILE = BASE_DIR / "state.json"
LOGS_DIR = BASE_DIR / "logs"
REPORT_FILE = BASE_DIR / "report.png"

# ================= LOGGING =================
LOGS_DIR.mkdir(exist_ok=True)

logger = logging.getLogger("NCC_OPER")
logger.setLevel(logging.DEBUG)

file_handler = RotatingFileHandler(
    LOGS_DIR / "bot.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)

formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(message)s"
)

file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ================= BOT =================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

# ================= STATE =================
def load_state():
    if not STATE_FILE.exists():
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

    logger.info("API REQUEST START")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers, ssl=False) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"API OK | alarms: {len(data)}")
                    return data
                else:
                    logger.error(f"API STATUS: {resp.status}")
    except Exception:
        logger.exception("API ERROR")

    return None

# ================= PROCESS =================
def process_alarms(data):
    logger.info("PROCESS START")

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

    logger.info(f"PROCESS DONE | regions={len(stats)}")
    return stats

# ================= STATE LOGIC =================
async def update_state(stats):
    started = []
    finished = []

    logger.info("STATE UPDATE START")

    all_regions = sorted(set(state.keys()) | set(stats.keys()))

    for region in all_regions:
        values = stats.get(region, {
            "power": 0,
            "dg": 0,
            "mg": 0,
            "site_down": 0
        })
        power = values["power"]

        if region not in state:
            state[region] = {
                "status": "closed",
                "start_time": None,
                "check_count": 0
            }

        st = state[region]
        status = st["status"]

        # ACTIVE
        if power >= POWER_THRESHOLD:
            if status != "active":
                st["status"] = "active"
                st["start_time"] = datetime.now().strftime("%d.%m.%Y %H:%M")
                st["check_count"] = 0
                started.append(region)
                logger.warning(f"MO START | {region} | power={power}")

        # BELOW
        else:
            if status == "active":
                st["status"] = "check"
                st["check_count"] = 1
                logger.warning(f"CHECK START | {region}")

            elif status == "check":
                st["check_count"] += 1
                logger.info(f"CHECK | {region} | {st['check_count']}")

                if st["check_count"] >= 2:
                    st["status"] = "closed"
                    st["start_time"] = None
                    st["check_count"] = 0
                    finished.append(region)
                    logger.warning(f"MO END | {region}")

    return started, finished

# ================= IMAGE =================
def generate_image(stats):
    regions = sorted([
        r for r in stats
        if state.get(r, {}).get("status") == "active"
    ])

    if not regions:
        return None

    logger.info(f"GENERATE IMAGE | regions={regions}")

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

    def text_size(text):
        return font.getbbox(str(text))[2]

    def draw_center(draw, xy, w, h, text, bold=False):
        tw = text_size(text)
        x = xy[0] + (w - tw) // 2
        y = xy[1] + (h - 18) // 2
        if bold:
            draw.text((x+1, y), str(text), fill="black", font=font)
        draw.text((x, y), str(text), fill="black", font=font)

    col_widths = []
    first_col = max(text_size(r) for r in rows + ["Регион"]) + 40
    col_widths.append(first_col)

    for region in regions:
        max_text = region
        vals = [
            state[region]["start_time"] or "",
            stats[region]["power"],
            stats[region]["dg"],
            stats[region]["mg"],
            stats[region]["site_down"]
        ]
        for v in vals:
            if text_size(v) > text_size(max_text):
                max_text = v
        col_widths.append(text_size(max_text) + 40)

    row_h = 50
    width = sum(col_widths)
    height = row_h * (len(rows) + 1)

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    # grid
    x = 0
    for w in col_widths:
        draw.line((x, 0, x, height), fill="black", width=2)
        x += w
    draw.line((x, 0, x, height), fill="black", width=2)

    for i in range(len(rows) + 2):
        y = i * row_h
        draw.line((0, y, width, y), fill="black", width=2)

    # header bg
    x = 0
    for w in col_widths:
        draw.rectangle((x, 0, x + w, row_h), fill="#FFF59D")
        x += w

    # header
    x = 0
    draw_center(draw, (x, 0), col_widths[0], row_h, "Регион", True)
    x += col_widths[0]

    for i, r in enumerate(regions):
        draw_center(draw, (x, 0), col_widths[i+1], row_h, r, True)
        x += col_widths[i+1]

    # rows
    for i, row in enumerate(rows):
        y = row_h * (i + 1)
        draw_center(draw, (0, y), col_widths[0], row_h, row)

        x = col_widths[0]

        for j, r in enumerate(regions):
            if row == "Время МО ЭП":
                val = state[r]["start_time"] or ""
            elif row == "Нет ЭП":
                val = stats[r]["power"]
            elif row == "ДГ":
                val = stats[r]["dg"]
            elif row == "МГ":
                val = stats[r]["mg"]
            else:
                val = stats[r]["site_down"]

            draw_center(draw, (x, y), col_widths[j+1], row_h, val)
            x += col_widths[j+1]

    img.save(REPORT_FILE)

    logger.info("IMAGE SAVED")

    return REPORT_FILE

# ================= SEND =================
async def send_report(stats):
    active = [r for r, info in state.items() if info.get("status") == "active"]

    logger.info(f"ACTIVE REGIONS: {active}")

    if not active:
        logger.info("NO ACTIVE - SKIP")
        return

    path = generate_image(stats)

    if not path:
        logger.warning("NO IMAGE GENERATED")
        return

    await bot.send_photo(CHAT_ID, FSInputFile(path))
    logger.info("REPORT SENT")

async def send_finished(regions):
    if not regions:
        return

    logger.info(f"FINISHED: {regions}")

    for r in regions:
        await bot.send_message(
            CHAT_ID,
            f"✅ В регионе <b>{r}</b> МО завершено"
        )

async def send_started(regions, stats):
    if not regions:
        return

    logger.info(f"STARTED: {regions}")

    path = generate_image(stats)

    if not path:
        logger.warning("NO IMAGE GENERATED FOR STARTED REGIONS")
        return

    await bot.send_photo(CHAT_ID, FSInputFile(path))
    logger.info("STARTED REPORT SENT")

# ================= JOBS =================
async def check_job():
    global last_stats

    logger.info("=== CHECK JOB ===")

    data = await fetch_alarms()
    if data is None:
        logger.warning("CHECK SKIPPED | API unavailable, keeping last successful stats")
        return

    stats = process_alarms(data)

    started, finished = await update_state(stats)

    if started:
        await send_started(started, stats)

    if finished:
        await send_finished(finished)

    save_state(state)
    last_stats = stats

async def report_job():
    logger.info("=== REPORT JOB ===")

    # Refresh state right before the hourly report so we don't send stale data.
    await check_job()

    if last_stats:
        await send_report(last_stats)
    else:
        logger.info("NO DATA")

# ================= MAIN =================
async def main():
    logger.info("BOT START")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_job, "interval", minutes=CHECK_INTERVAL)
    scheduler.add_job(report_job, "interval", minutes=REPORT_INTERVAL)
    scheduler.start()

    await check_job()
    await report_job()

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
