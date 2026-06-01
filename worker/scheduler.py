"""
Background scheduler: runs a scan every 90-120 minutes.
Nighttime sleep window: 23:30 – 07:30.
"""
import asyncio
import logging
import os
import random
import sys
from datetime import datetime, time as dtime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal, init_db
from app.services.diff_engine import process_scan
from worker.scraper import run_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("scheduler")

SLEEP_START = dtime(23, 30)
SLEEP_END = dtime(7, 30)
MIN_INTERVAL = int(os.getenv("SCAN_INTERVAL_MIN", "90"))
MAX_INTERVAL = int(os.getenv("SCAN_INTERVAL_MAX", "120"))


def _is_sleep_time() -> bool:
    now = datetime.now().time()
    if SLEEP_START > SLEEP_END:  # crosses midnight
        return now >= SLEEP_START or now < SLEEP_END
    return SLEEP_START <= now < SLEEP_END


def _seconds_until_wake() -> int:
    from datetime import timedelta
    now = datetime.now()
    wake = now.replace(hour=SLEEP_END.hour, minute=SLEEP_END.minute, second=0, microsecond=0)
    if now.time() >= SLEEP_END:
        wake += timedelta(days=1)
    return max(0, int((wake - now).total_seconds()))


async def _execute_scan() -> None:
    logger.info("Starting Instagram scan…")
    result = await run_scan()

    if result is None:
        logger.error("Scan returned no result")
        return

    db = SessionLocal()
    try:
        snapshot = process_scan(
            db=db,
            scraped_users=result["users"],
            total_count=result["total_count"],
            duration=result["duration"],
            profile_data=result.get("profile"),
        )
        logger.info(
            "Snapshot #%d — total: %d | +%d -%d",
            snapshot.id, snapshot.total_count,
            snapshot.added_count, snapshot.removed_count,
        )
    except Exception as e:
        logger.exception("Failed to persist scan results: %s", e)
    finally:
        db.close()


async def main_loop() -> None:
    logger.info("IGToxic Worker starting…")
    init_db()
    logger.info("Database ready")

    while True:
        if _is_sleep_time():
            secs = _seconds_until_wake()
            logger.info("Sleep mode — resuming in %dm %ds", secs // 60, secs % 60)
            await asyncio.sleep(secs + random.randint(60, 300))
            continue

        await _execute_scan()

        wait = random.uniform(MIN_INTERVAL, MAX_INTERVAL) * 60
        logger.info("Next scan in %.1f min", wait / 60)
        await asyncio.sleep(wait)


if __name__ == "__main__":
    asyncio.run(main_loop())
