import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from aiogram.client.session.aiohttp import AiohttpSession


env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "test_evo_runtime"
LOGS_DIR = RUNTIME_DIR / "logs"
STATE_FILE = RUNTIME_DIR / "state.json"
REPORT_FILE = RUNTIME_DIR / "report.png"
SCRIPT_LOG_FILE = LOGS_DIR / "bot.log"

for directory in (RUNTIME_DIR, LOGS_DIR):
    directory.mkdir(parents=True, exist_ok=True)


API_URL = os.getenv("NIMS_API_ACTIVE_ALARMS")
API_TOKEN = os.getenv("NIMS_TOKEN")
BOT_TOKEN = os.getenv("NCC_OPER_BOT_TOKEN")
CHAT_ID = int(os.getenv("NCC_OPER_CHAT_ID"))
PROXY_URL = os.getenv('PROXY_URL')

CHECK_INTERVAL = 15
REPORT_INTERVAL = 60
REPORT_JOB_INTERVAL = 15
POWER_THRESHOLD = 40
CHECK_CLOSE_COUNT = 2


logger = logging.getLogger("TEST_EVO")
logger.setLevel(logging.INFO)
logger.handlers.clear()

formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

file_handler = RotatingFileHandler(
    SCRIPT_LOG_FILE,
    maxBytes=5 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


session = AiohttpSession(proxy=str(PROXY_URL)) if PROXY_URL else AiohttpSession()
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=session,
)
dp = Dispatcher()


def now_str():
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def load_state():
    if not STATE_FILE.exists():
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def parse_iso(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def mark_regions_report_sent(regions):
    now_iso = datetime.now().isoformat(timespec="seconds")
    for region in regions:
        if region in state:
            state[region]["last_report_sent_at"] = now_iso


def get_due_hourly_regions():
    now = datetime.now()
    due = []

    for region, region_state in state.items():
        if region_state.get("status") != "active":
            continue

        last_sent = parse_iso(region_state.get("last_report_sent_at"))
        if last_sent is None:
            due.append(region)
            continue

        minutes_passed = (now - last_sent).total_seconds() / 60
        if minutes_passed >= REPORT_INTERVAL:
            due.append(region)

    return sorted(due)


state = load_state()
last_stats = {}
job_lock = asyncio.Lock()


async def fetch_alarms():
    headers = {"Authorization": API_TOKEN}
    logger.info("API REQUEST START")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(API_URL, headers=headers, ssl=False) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info("API OK | alarms=%s", len(data))
                    return data

                logger.error("API STATUS | code=%s", resp.status)
    except Exception:
        logger.exception("API ERROR")

    return None


def process_alarms(data):
    logger.info("PROCESS START")

    stats = defaultdict(lambda: {"power": 0, "dg": 0, "mg": 0, "site_down": 0,})

    for alarm in data:
        region = (alarm.get("region") or "UNKNOWN").upper()
        alarm_type = alarm.get("alarmtype") or ""
        alarm_name = alarm.get("alarmobjectname", "")

        if alarm_type == "power":
            stats[region]["power"] += 1
        elif alarm_type == "dg":
            if "_FG_" in alarm_name:
                stats[region]["dg"] += 1
            else:
                stats[region]["mg"] += 1
        elif alarm_type == "site_down":
            stats[region]["site_down"] += 1

    logger.info("PROCESS DONE | regions=%s", len(stats))
    return stats


async def update_state(stats):
    started = []
    finished = []

    logger.info("STATE UPDATE START")

    all_regions = sorted(set(state.keys()) | set(stats.keys()))

    for region in all_regions:
        values = stats.get(region, {"power": 0, "dg": 0, "mg": 0, "site_down": 0},)
        power = values["power"]

        if region not in state:
            state[region] = {
                "status": "closed",
                "start_time": None,
                "check_count": 0,
                "last_report_sent_at": None,
            }

        region_state = state[region]
        region_state.setdefault("last_report_sent_at", None)
        status_before = region_state["status"]

        if power >= POWER_THRESHOLD:
            if status_before != "active":
                region_state["status"] = "active"
                region_state["start_time"] = now_str()
                region_state["check_count"] = 0
                region_state["last_report_sent_at"] = None
                started.append(region)
                logger.warning("MO START | region=%s | power=%s", region, power)
            else:
                region_state["check_count"] = 0

        else:
            if status_before == "active":
                region_state["status"] = "check"
                region_state["check_count"] = 1
                logger.warning("CHECK START | region=%s | power=%s", region, power)
            elif status_before == "check":
                region_state["check_count"] += 1
                logger.info(
                    "CHECK PROGRESS | region=%s | check_count=%s | power=%s",
                    region,
                    region_state["check_count"],
                    power,
                )

                if region_state["check_count"] >= CHECK_CLOSE_COUNT:
                    region_state["status"] = "closed"
                    finished.append(region)
                    logger.warning("MO END | region=%s | power=%s", region, power)
                    region_state["start_time"] = None
                    region_state["check_count"] = 0
                    region_state["last_report_sent_at"] = None

    return started, finished


def get_active_regions():
    return sorted(region for region, region_state in state.items() if region_state.get("status") == "active")


def generate_image(stats, regions):
    regions = sorted(regions)

    if not regions:
        return None

    logger.info("GENERATE IMAGE | active_regions=%s", regions)

    rows = ["Время МО ЭП", "Нет ЭП", "ДГ", "МГ", "Кол-во недоступных БС",]

    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font = ImageFont.load_default()

    def text_width(text):
        box = font.getbbox(str(text))
        return box[2] - box[0]

    def draw_center(draw, x, y, w, h, text, bold=False):
        text = str(text)
        width = text_width(text)
        text_x = x + (w - width) // 2
        text_y = y + (h - 18) // 2
        if bold:
            draw.text((text_x + 1, text_y), text, fill="black", font=font)
        draw.text((text_x, text_y), text, fill="black", font=font)

    col_widths = []
    first_col = max(text_width(item) for item in rows + ["Регион"]) + 40
    col_widths.append(first_col)

    for region in regions:
        max_text = region
        region_stats = stats.get(
            region,
            {"power": 0, "dg": 0, "mg": 0, "site_down": 0},
        )
        values = [
            state[region]["start_time"] or "",
            region_stats["power"],
            region_stats["dg"],
            region_stats["mg"],
            region_stats["site_down"],
        ]
        for value in values:
            if text_width(value) > text_width(max_text):
                max_text = value
        col_widths.append(text_width(max_text) + 40)

    row_height = 50
    width = sum(col_widths)
    height = row_height * (len(rows) + 1)

    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    x = 0
    for column_width in col_widths:
        draw.line((x, 0, x, height), fill="black", width=2)
        x += column_width
    draw.line((x, 0, x, height), fill="black", width=2)

    for i in range(len(rows) + 2):
        y = i * row_height
        draw.line((0, y, width, y), fill="black", width=2)

    x = 0
    for column_width in col_widths:
        draw.rectangle((x, 0, x + column_width, row_height), fill="#FFF59D")
        x += column_width

    x = 0
    draw_center(draw, x, 0, col_widths[0], row_height, "Регион", bold=True)
    x += col_widths[0]

    for idx, region in enumerate(regions):
        draw_center(draw, x, 0, col_widths[idx + 1], row_height, region, bold=True)
        x += col_widths[idx + 1]

    for row_idx, row_name in enumerate(rows):
        y = row_height * (row_idx + 1)
        draw_center(draw, 0, y, col_widths[0], row_height, row_name)
        x = col_widths[0]

        for idx, region in enumerate(regions):
            region_stats = stats.get(
                region,
                {"power": 0, "dg": 0, "mg": 0, "site_down": 0},
            )

            if row_name == "Время МО ЭП":
                value = state[region]["start_time"] or ""
            elif row_name == "Нет ЭП":
                value = region_stats["power"]
            elif row_name == "ДГ":
                value = region_stats["dg"]
            elif row_name == "МГ":
                value = region_stats["mg"]
            else:
                value = region_stats["site_down"]

            draw_center(draw, x, y, col_widths[idx + 1], row_height, value)
            x += col_widths[idx + 1]

    image.save(REPORT_FILE)
    logger.info("IMAGE SAVED | path=%s", REPORT_FILE)
    return REPORT_FILE


async def send_report(stats, regions, reason):
    regions = sorted(regions)
    logger.info("SEND REPORT | reason=%s | regions=%s", reason, regions)

    if not regions:
        logger.info("NO REGIONS TO REPORT | reason=%s", reason)
        return False

    path = generate_image(stats, regions)
    if not path:
        logger.warning("REPORT IMAGE NOT GENERATED")
        return False

    await bot.send_photo(chat_id=CHAT_ID, photo=FSInputFile(path))
    logger.info("REPORT SENT | reason=%s | regions=%s", reason, regions)
    mark_regions_report_sent(regions)
    save_state(state)
    return True


async def send_finished(regions):
    if not regions:
        return

    logger.info("SEND FINISHED | regions=%s", regions)

    for region in regions:
        await bot.send_message(
            CHAT_ID,
            f"В регионе <b>{region}</b> массовые отключения завершены.",
        )


async def check_job():
    global last_stats

    async with job_lock:
        logger.info("=== CHECK JOB ===")
        data = await fetch_alarms()

        if data is None:
            logger.warning("CHECK SKIPPED | no data from API")
            return

        stats = process_alarms(data)
        started, finished = await update_state(stats)

        save_state(state)
        last_stats = stats

        if started:
            # Start report includes only regions that became active in this check cycle.
            # If several regions started together, they are sent as one combined table.
            await send_report(stats, started, reason="start")

        if finished:
            await send_finished(finished)


async def report_job():
    async with job_lock:
        logger.info("=== REPORT JOB ===")

        if not last_stats:
            logger.info("NO DATA FOR HOURLY REPORT")
            return

        due_regions = get_due_hourly_regions()
        if not due_regions:
            logger.info("SKIP HOURLY REPORT | no regions reached 60 min since last report")
            return

        await send_report(last_stats, due_regions, reason="hourly")


async def main():
    logger.info("BOT START")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_job, "interval", minutes=CHECK_INTERVAL)
    # Run hourly-due scan every 15 minutes; each region is sent only when 60+ minutes elapsed.
    scheduler.add_job(report_job, "interval", minutes=REPORT_JOB_INTERVAL)
    scheduler.start()

    await check_job()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
