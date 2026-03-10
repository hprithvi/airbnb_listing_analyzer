from __future__ import annotations

import asyncio
import json

import httpx

from db.database import fetch_all, upsert_listing_details
from scraper.auth import get_auth, invalidate_auth
from scraper.rate_limiter import AsyncRateLimiter, random_user_agent

_BASE_URL = "https://www.airbnb.com/api/v2/pdp_listing_details/{listing_id}"
_CURRENCY = "INR"
_LOCALE = "en-IN"


def _extract_details(listing_id: str, data: dict) -> dict:
    pdp = data.get("pdp_listing_detail") or data.get("listing") or {}
    primary_host = pdp.get("primary_host") or {}
    reviews = pdp.get("reviews_module") or {}

    amenities_raw = pdp.get("listing_amenities") or []
    amenities = [a.get("name") for a in amenities_raw if a.get("is_present")]

    review_count = (
        pdp.get("review_details_interface", {}).get("review_count")
        or pdp.get("review_count")
        or reviews.get("review_count")
        or 0
    )
    review_score = (
        pdp.get("review_details_interface", {}).get("review_score")
        or pdp.get("review_score")
        or pdp.get("star_rating")
    )

    return {
        "listing_id": listing_id,
        "review_count": review_count,
        "review_score": review_score,
        "host_since": primary_host.get("created_at"),
        "superhost": 1 if primary_host.get("is_superhost") else 0,
        "amenities": json.dumps(amenities),
        "property_type": pdp.get("property_type"),
        "description": pdp.get("description") or pdp.get("summary"),
    }


async def scrape_listing_details(
    listing_id: str,
    rate_limiter: AsyncRateLimiter,
    client: httpx.AsyncClient,
) -> bool:
    auth = await get_auth()
    headers = {
        "x-airbnb-api-key": auth["api_key"],
        "User-Agent": random_user_agent(),
        "Accept": "application/json",
        "Accept-Language": "en-IN,en;q=0.9",
        "Referer": f"https://www.airbnb.com/rooms/{listing_id}",
    }
    cookies = auth["cookies"]
    url = _BASE_URL.format(listing_id=listing_id)
    params = {
        "_format": "for_rooms_show",
        "locale": _LOCALE,
        "currency": _CURRENCY,
    }

    async with rate_limiter.throttle():
        try:
            resp = await client.get(url, params=params, headers=headers, cookies=cookies, timeout=30)
        except httpx.RequestError as exc:
            print(f"  [detail] Network error for {listing_id}: {exc}")
            return False

    if resp.status_code == 401:
        invalidate_auth()
        return False

    if resp.status_code != 200:
        print(f"  [detail] HTTP {resp.status_code} for {listing_id}")
        return False

    data = resp.json()
    details = _extract_details(listing_id, data)
    upsert_listing_details(details)
    return True


async def scrape_city_details(city: str) -> int:
    rows = fetch_all(
        "SELECT id FROM listings WHERE city = ? ORDER BY last_seen_at DESC",
        (city,),
    )
    listing_ids = [r["id"] for r in rows]
    print(f"  Fetching details for {len(listing_ids)} listings in {city}")

    rate_limiter = AsyncRateLimiter(concurrency=1, min_delay=3.0, max_delay=5.0)
    success = 0
    async with httpx.AsyncClient() as client:
        for i, lid in enumerate(listing_ids, 1):
            ok = await scrape_listing_details(lid, rate_limiter, client)
            if ok:
                success += 1
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(listing_ids)} ({success} OK)")
    return success
