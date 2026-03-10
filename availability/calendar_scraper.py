from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from db.database import fetch_all, fetch_one, insert_calendar_snapshot
from scraper.auth import get_auth, invalidate_auth
from scraper.rate_limiter import AsyncRateLimiter, random_user_agent

_BASE_URL = "https://www.airbnb.com/api/v2/calendar_months"
_CURRENCY = "INR"
_LOCALE = "en-IN"
_SKIP_IF_SCRAPED_WITHIN_HOURS = 20
_MONTHS_TO_FETCH = 6


def _was_recently_scraped(listing_id: str) -> bool:
    row = fetch_one(
        "SELECT MAX(scraped_at) as last FROM calendar_snapshots WHERE listing_id = ?",
        (listing_id,),
    )
    if not row or not row["last"]:
        return False
    last_dt = datetime.fromisoformat(row["last"])
    if last_dt.tzinfo is None:
        last_dt = last_dt.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_SKIP_IF_SCRAPED_WITHIN_HOURS)
    return last_dt > cutoff


async def _fetch_calendar(
    listing_id: str,
    rate_limiter: AsyncRateLimiter,
    client: httpx.AsyncClient,
) -> int:
    if _was_recently_scraped(listing_id):
        return 0

    auth = await get_auth()
    headers = {
        "x-airbnb-api-key": auth["api_key"],
        "User-Agent": random_user_agent(),
        "Accept": "application/json",
        "Accept-Language": "en-IN,en;q=0.9",
        "Referer": f"https://www.airbnb.com/rooms/{listing_id}",
    }
    cookies = auth["cookies"]

    now = datetime.now(timezone.utc)
    params = {
        "listing_id": listing_id,
        "month": now.month,
        "year": now.year,
        "count": _MONTHS_TO_FETCH,
        "locale": _LOCALE,
        "currency": _CURRENCY,
    }

    async with rate_limiter.throttle():
        try:
            resp = await client.get(
                _BASE_URL, params=params, headers=headers, cookies=cookies, timeout=30
            )
        except httpx.RequestError as exc:
            print(f"  [calendar] Network error for {listing_id}: {exc}")
            return 0

    if resp.status_code == 401:
        invalidate_auth()
        return 0

    if resp.status_code != 200:
        print(f"  [calendar] HTTP {resp.status_code} for {listing_id}")
        return 0

    data = resp.json()
    scraped_at = datetime.now(timezone.utc).isoformat()
    count = 0

    for month_data in data.get("calendar_months", []):
        for day in month_data.get("days", []):
            date_str = day.get("date")
            available = day.get("available", False)
            status = "available" if available else "blocked"
            price_info = day.get("price") or {}
            local_price = price_info.get("local_price")
            price = float(local_price) if local_price is not None else None
            insert_calendar_snapshot(listing_id, date_str, status, price, scraped_at)
            count += 1

    return count


async def scrape_city_calendar(city: str) -> int:
    rows = fetch_all(
        "SELECT id FROM listings WHERE city = ? ORDER BY last_seen_at DESC",
        (city,),
    )
    listing_ids = [r["id"] for r in rows]
    print(f"  Scraping calendar for {len(listing_ids)} listings in {city}")

    rate_limiter = AsyncRateLimiter(concurrency=1, min_delay=3.0, max_delay=5.0)
    total_days = 0
    scraped_listings = 0

    async with httpx.AsyncClient() as client:
        for i, lid in enumerate(listing_ids, 1):
            days = await _fetch_calendar(lid, rate_limiter, client)
            if days > 0:
                scraped_listings += 1
                total_days += days
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(listing_ids)} ({scraped_listings} scraped, {total_days} day-rows)")

    print(f"  Calendar scrape done: {scraped_listings} listings, {total_days} day-rows inserted")
    return total_days
