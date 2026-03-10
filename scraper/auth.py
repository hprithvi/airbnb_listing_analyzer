from __future__ import annotations

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv, set_key

load_dotenv()

ENV_PATH = Path(".env")
_AUTH_CACHE: dict | None = None


async def _harvest_tokens() -> dict:
    from playwright.async_api import async_playwright

    email = os.getenv("AIRBNB_EMAIL", "")
    password = os.getenv("AIRBNB_PASSWORD", "")
    if not email or not password:
        raise ValueError("AIRBNB_EMAIL and AIRBNB_PASSWORD must be set in .env")

    api_key = None
    cookies_dict: dict = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        async def intercept(request):
            nonlocal api_key
            key = request.headers.get("x-airbnb-api-key")
            if key:
                api_key = key

        page = await context.new_page()
        page.on("request", intercept)

        await page.goto("https://www.airbnb.com/login", wait_until="networkidle")
        await page.fill('input[name="email"]', email)
        await page.click('button[data-testid="signup-login-submit-btn"]')
        await page.wait_for_selector('input[name="password"]', timeout=10000)
        await page.fill('input[name="password"]', password)
        await page.click('button[data-testid="signup-login-submit-btn"]')
        await page.wait_for_url("https://www.airbnb.com/**", timeout=20000)

        if api_key is None:
            local_key = await page.evaluate("localStorage.getItem('apiKey')")
            if local_key:
                api_key = local_key

        raw_cookies = await context.cookies()
        cookies_dict = {c["name"]: c["value"] for c in raw_cookies}

        await browser.close()

    if not api_key:
        api_key = "d306zoyjsyarp7ifhu67rjxn52tv0t20"

    return {"api_key": api_key, "cookies": cookies_dict}


async def get_auth() -> dict:
    global _AUTH_CACHE

    cached_key = os.getenv("AIRBNB_API_KEY", "")
    if cached_key and _AUTH_CACHE is None:
        _AUTH_CACHE = {"api_key": cached_key, "cookies": {}}

    if _AUTH_CACHE:
        return _AUTH_CACHE

    tokens = await _harvest_tokens()
    _AUTH_CACHE = tokens

    if ENV_PATH.exists():
        set_key(str(ENV_PATH), "AIRBNB_API_KEY", tokens["api_key"])

    return _AUTH_CACHE


def invalidate_auth():
    global _AUTH_CACHE
    _AUTH_CACHE = None
