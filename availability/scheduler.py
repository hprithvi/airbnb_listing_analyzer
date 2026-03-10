from __future__ import annotations

import asyncio
import time

import schedule

from db.database import fetch_all


def _get_cities() -> list[str]:
    rows = fetch_all("SELECT DISTINCT city FROM listings")
    return [r["city"] for r in rows] or ["goa", "bengaluru"]


def run_calendar_scrape():
    from availability.calendar_scraper import scrape_city_calendar
    from analysis.snapshot_diff import run_diff_for_city

    cities = _get_cities()
    for city in cities:
        print(f"[scheduler] Calendar scrape: {city}")
        asyncio.run(scrape_city_calendar(city))
        print(f"[scheduler] Running snapshot diff: {city}")
        run_diff_for_city(city)


def run_listing_refresh():
    from scraper.grid import generate_grid
    from scraper.listing_scraper import scrape_city_listings

    cities = _get_cities()
    for city in cities:
        print(f"[scheduler] Refreshing listings: {city}")
        cells = generate_grid(city, grid_size=0.01)
        asyncio.run(scrape_city_listings(city, cells))


def start_scheduler():
    schedule.every().day.at("02:00").do(run_calendar_scrape)
    schedule.every().monday.do(run_listing_refresh)

    print("[scheduler] Started. Calendar scrape at 02:00 daily; listing refresh every Monday.")
    while True:
        schedule.run_pending()
        time.sleep(60)
