import json
import os
import logging
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

COOKIES_PATH = Path(os.getenv("COOKIES_PATH", "/data/ig_session.json"))


def save_cookies(cookies: List[Dict]) -> None:
    COOKIES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(COOKIES_PATH, "w") as f:
        json.dump(cookies, f)
    logger.info("Session cookies saved to %s", COOKIES_PATH)


def load_cookies() -> Optional[List[Dict]]:
    if not COOKIES_PATH.exists():
        return None
    try:
        with open(COOKIES_PATH) as f:
            cookies = json.load(f)
        if not cookies:
            return None
        return cookies
    except Exception as e:
        logger.warning("Failed to load cookies: %s", e)
        return None


def clear_cookies() -> None:
    if COOKIES_PATH.exists():
        COOKIES_PATH.unlink()
        logger.info("Session cookies cleared")


def get_user_id_from_cookies(cookies: List[Dict]) -> Optional[str]:
    for c in cookies:
        if c.get("name") == "ds_user_id":
            return c.get("value")
    return None
