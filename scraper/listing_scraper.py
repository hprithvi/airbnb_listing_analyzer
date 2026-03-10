from __future__ import annotations

import asyncio
import base64
import json
import re

from db.database import upsert_listing
from scraper.rate_limiter import AsyncRateLimiter

# Matches the Hyperloop data-deferred-state-0 script tag
_DEFERRED_RE = re.compile(
    r'<script id="data-deferred-state-0"[^>]*type="application/json"[^>]*>(.*?)</script>',
    re.DOTALL,
)

_CITY_SLUG = {
    "goa": "Goa--India",
    "bengaluru": "Bengaluru--Karnataka--India",
    "bangalore": "Bengaluru--Karnataka--India",
}

_debug_path_printed = False


def _search_url(city: str, cell: dict, cursor: str | None = None) -> str:
    slug = _CITY_SLUG.get(city.lower(), f"{city.title()}--India")
    params = [
        f"ne_lat={cell['lat_max']}",
        f"ne_lng={cell['lon_max']}",
        f"sw_lat={cell['lat_min']}",
        f"sw_lng={cell['lon_min']}",
        "currency=INR",
        "search_type=user_map_move",
        "tab_id=home_tab",
    ]
    if cursor:
        params.append(f"cursor={cursor}")
    return f"https://www.airbnb.co.in/s/{slug}/homes?{'&'.join(params)}"


def _parse_niobe(html: str) -> dict:
    """Extract niobeClientData cache from the Hyperloop data-deferred-state-0 tag."""
    m = _DEFERRED_RE.search(html)
    if not m:
        return {}
    try:
        outer = json.loads(m.group(1))
        niobe = outer.get("niobeClientData", [])
        # niobe = [[key_str, data_dict], ...]
        if niobe and isinstance(niobe[0], list) and len(niobe[0]) > 1:
            return niobe[0][1]
    except (json.JSONDecodeError, IndexError, TypeError):
        pass
    return {}


def _find_search_results(data: dict) -> list[dict]:
    global _debug_path_printed
    try:
        results = data["data"]["presentation"]["staysSearch"]["results"]["searchResults"]
        if not _debug_path_printed:
            print("  [debug] path=niobe staysSearch.results.searchResults")
            _debug_path_printed = True
        return results
    except (KeyError, TypeError):
        pass
    if not _debug_path_printed:
        print(f"  [debug] niobe data keys: {list(data.keys())}")
        _debug_path_printed = True
    return []


def _find_next_cursor(data: dict) -> str | None:
    try:
        return (
            data["data"]["presentation"]["staysSearch"]
            ["results"]["paginationInfo"]["nextPageCursor"]
        )
    except (KeyError, TypeError):
        return None


def _decode_listing_id(raw_id: str) -> str:
    """Decode base64 Relay ID 'DemandStayListing:12345' → '12345'."""
    try:
        # Add padding in case it's missing
        padding = 4 - len(raw_id) % 4
        padded = raw_id + ("=" * (padding % 4))
        decoded = base64.b64decode(padded).decode("utf-8", errors="replace")
        return decoded.split(":")[-1]
    except Exception:
        return raw_id


def _extract_listing(raw: dict, city: str, grid_cell_id: int) -> dict | None:
    demand = raw.get("demandStayListing") or {}
    raw_id = demand.get("id")
    if not raw_id:
        return None

    lid = _decode_listing_id(raw_id)

    coord = (demand.get("location") or {}).get("coordinate") or {}
    lat = coord.get("latitude")
    lon = coord.get("longitude")

    # Nightly price: parse "N nights x ₹X,XXX.XX" from explanation
    nightly_price = None
    try:
        price_details = (
            (raw.get("structuredDisplayPrice") or {})
            .get("explanationData", {})
            .get("priceDetails") or []
        )
        for group in price_details:
            for item in group.get("items", []):
                m = re.search(r"x\s*[₹$]?([\d,]+(?:\.\d+)?)", item.get("description", ""))
                if m:
                    nightly_price = float(m.group(1).replace(",", ""))
                    break
            if nightly_price is not None:
                break
    except Exception:
        pass

    # Bedrooms: parse "1 bedroom" from structuredContent.primaryLine
    bedrooms = None
    try:
        for item in (raw.get("structuredContent") or {}).get("primaryLine", []):
            if item.get("type") == "BEDINFO":
                m = re.search(r"(\d+)\s+bedroom", item.get("body", ""))
                if m:
                    bedrooms = int(m.group(1))
                    break
    except Exception:
        pass

    return {
        "id": str(lid),
        "city": city,
        "grid_cell_id": grid_cell_id,
        "lat": lat,
        "lon": lon,
        "room_type": None,
        "bedrooms": bedrooms,
        "bathrooms": None,
        "max_guests": None,
        "nightly_price": nightly_price,
        "cleaning_fee": None,
        "service_fee": None,
        "neighbourhood": None,
    }


async def scrape_listings_for_cell(
    cell: dict,
    city: str,
    rate_limiter: AsyncRateLimiter,
    page,
) -> int:
    cursor = None
    total = 0

    while True:
        url = _search_url(city, cell, cursor)
        async with rate_limiter.throttle():
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as exc:
                print(f"  [listing] Navigation error for cell {cell}: {exc}")
                break

        html = await page.content()
        niobe_data = _parse_niobe(html)

        if not niobe_data:
            print(f"  [listing] Niobe data not found for cell {cell}")
            print(f"  [listing] HTML snippet: {html[:300]!r}")
            break

        search_results = _find_search_results(niobe_data)

        listings_found = 0
        for item in search_results:
            extracted = _extract_listing(item, city, cell["cell_id"])
            if extracted:
                upsert_listing(extracted)
                listings_found += 1

        total += listings_found

        next_cursor = _find_next_cursor(niobe_data)
        if next_cursor and next_cursor != cursor:
            cursor = next_cursor
        else:
            break

    return total


async def scrape_city_listings(city: str, grid_cells: list[dict]) -> int:
    from playwright.async_api import async_playwright

    rate_limiter = AsyncRateLimiter(concurrency=1, min_delay=3.0, max_delay=5.0)
    total = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await context.new_page()

        for i, cell in enumerate(grid_cells, 1):
            print(f"  Scraping cell {i}/{len(grid_cells)}: lat [{cell['lat_min']}, {cell['lat_max']}]")
            count = await scrape_listings_for_cell(cell, city, rate_limiter, page)
            total += count
            print(f"    Found {count} listings (total so far: {total})")

        await browser.close()

    return total
