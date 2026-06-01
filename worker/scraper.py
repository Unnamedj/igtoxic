"""
Instagram Following scraper.
Hybrid approach: Playwright handles login/cookies, aiohttp handles data fetching.
"""
import asyncio
import logging
import os
import random
import time
from typing import Dict, List, Optional, Tuple

import aiohttp
from playwright.async_api import async_playwright, BrowserContext, Page

from worker.session_manager import (
    save_cookies, load_cookies, clear_cookies, get_user_id_from_cookies,
)

logger = logging.getLogger(__name__)

IG_USER = os.environ["IG_USERNAME"]    # cuenta que hace login (la "espía")
IG_PASS = os.environ["IG_PASSWORD"]
IG_TARGET = os.environ.get("IG_TARGET", IG_USER)  # cuenta a monitorear

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Mobile/15E148 Instagram/303.0.0.11.109"
    ),
    "X-IG-App-ID": "936619743392459",
    "Accept": "*/*",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


async def _jitter(low: float = 0.8, high: float = 2.5) -> None:
    await asyncio.sleep(random.uniform(low, high))


async def _do_login(page: Page) -> bool:
    logger.info("Performing fresh Instagram login…")
    await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
    await _jitter(2, 4)

    try:
        await page.fill('input[name="username"]', IG_USER, timeout=10000)
        await _jitter(0.5, 1.2)
        await page.fill('input[name="password"]', IG_PASS, timeout=10000)
        await _jitter(0.3, 0.8)
        await page.click('button[type="submit"]', timeout=10000)
    except Exception as e:
        logger.error("Login form interaction failed: %s", e)
        return False

    try:
        await page.wait_for_function(
            "() => !window.location.href.includes('/accounts/login')",
            timeout=30000,
        )
    except Exception:
        logger.error("Login did not redirect — wrong credentials or challenge required")
        return False

    await _jitter(2, 4)

    for text in ["Not Now", "Ahora no", "Not now", "Save Info"]:
        try:
            btn = await page.wait_for_selector(f'button:has-text("{text}")', timeout=4000)
            if btn:
                await btn.click()
                await _jitter(1, 2)
                break
        except Exception:
            pass

    for text in ["Not Now", "Ahora no", "Block", "Turn Off"]:
        try:
            btn = await page.wait_for_selector(f'button:has-text("{text}")', timeout=4000)
            if btn:
                await btn.click()
                await _jitter(1, 2)
                break
        except Exception:
            pass

    logger.info("Login successful")
    return True


async def _get_authenticated_context():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    context = await browser.new_context(
        viewport={"width": 390, "height": 844},
        user_agent=HEADERS["User-Agent"],
        locale="es-ES",
    )

    cookies = load_cookies()
    if cookies:
        await context.add_cookies(cookies)
        page = await context.new_page()
        await page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
        await _jitter(2, 3)
        current_url = page.url
        await page.close()
        if "accounts/login" not in current_url and "challenge" not in current_url:
            logger.info("Reusing saved session")
            return context, playwright, browser

        logger.info("Saved cookies expired, logging in again…")
        clear_cookies()

    page = await context.new_page()
    success = await _do_login(page)
    await page.close()

    if not success:
        await browser.close()
        await playwright.stop()
        return None, None, None

    new_cookies = await context.cookies()
    save_cookies(new_cookies)
    return context, playwright, browser


async def _cookies_to_jar(cookies: List[Dict]) -> Dict[str, str]:
    return {c["name"]: c["value"] for c in cookies}


async def _get_following_count_and_user_id(
    context: BrowserContext,
) -> Tuple[Optional[int], Optional[str]]:
    page = await context.new_page()
    try:
        await page.goto(
            f"https://www.instagram.com/{IG_TARGET}/",
            wait_until="domcontentloaded",
            timeout=30000,
        )
        await _jitter(2, 4)

        raw_cookies = await context.cookies()
        jar = await _cookies_to_jar(raw_cookies)

        async with aiohttp.ClientSession(cookies=jar) as session:
            url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={IG_TARGET}"
            async with session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    user = data.get("data", {}).get("user", {})
                    count = user.get("edge_follow", {}).get("count")
                    uid = user.get("id")  # ID del perfil objetivo
                    if count is not None and uid:
                        return int(count), uid

        # DOM fallback
        for sel in [
            f'a[href="/{IG_TARGET}/following/"] span',
            'a[href*="following"] span',
        ]:
            try:
                el = await page.wait_for_selector(sel, timeout=5000)
                if el:
                    text = (await el.inner_text()).replace(",", "").replace(".", "").strip()
                    return int(text), user_id
            except Exception:
                continue

        return None, user_id
    finally:
        await page.close()


async def _fetch_all_following(user_id: str, cookies_list: List[Dict]) -> List[Dict]:
    jar = await _cookies_to_jar(cookies_list)
    all_users: List[Dict] = []
    cursor = None
    page_num = 0

    async with aiohttp.ClientSession(cookies=jar) as session:
        while True:
            url = (
                f"https://www.instagram.com/api/v1/friendships/{user_id}/following/?count=200"
            )
            if cursor:
                url += f"&max_id={cursor}"

            try:
                async with session.get(
                    url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 429:
                        logger.warning("Rate limited — backing off 90s")
                        await asyncio.sleep(90)
                        continue
                    if resp.status != 200:
                        logger.error("API returned %d on page %d", resp.status, page_num)
                        break
                    data = await resp.json()
            except asyncio.TimeoutError:
                logger.warning("Timeout on page %d, retrying in 10s", page_num)
                await asyncio.sleep(10)
                continue
            except Exception as e:
                logger.error("Request error on page %d: %s", page_num, e)
                break

            users = data.get("users", [])
            for u in users:
                all_users.append({
                    "username": u.get("username", ""),
                    "full_name": u.get("full_name", ""),
                    "profile_pic_url": u.get("profile_pic_url", ""),
                })

            logger.info("Page %d: +%d users (total: %d)", page_num, len(users), len(all_users))

            next_cursor = data.get("next_max_id")
            if not next_cursor or not users:
                break

            cursor = next_cursor
            page_num += 1
            await _jitter(1.0, 2.5)

    return all_users


async def run_scan() -> Optional[Dict]:
    t0 = time.time()

    context, playwright, browser = await _get_authenticated_context()
    if context is None:
        logger.error("Could not establish authenticated context")
        return None

    try:
        count, user_id = await _get_following_count_and_user_id(context)

        if count is None:
            logger.error("Could not read following count from profile")
            return None

        logger.info("Following count: %d | user_id: %s", count, user_id)

        if not user_id:
            logger.error("Could not determine user_id")
            return None

        cookies_list = await context.cookies()
        users = await _fetch_all_following(user_id, cookies_list)

        save_cookies(await context.cookies())

        duration = int(time.time() - t0)
        logger.info("Scan done in %ds — %d followings", duration, len(users))

        return {"users": users, "total_count": count, "duration": duration}

    finally:
        await browser.close()
        await playwright.stop()
