#!/usr/bin/env python3
"""
Airbnb India STR Scraper — CLI entry point.

Usage:
    python main.py scrape    --city goa [--grid-size 0.01]
    python main.py details   --city goa
    python main.py calendar  --city goa
    python main.py analyze   --city goa
    python main.py scheduler
    python main.py app
"""
from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from db.database import init_db


def cmd_scrape(args):
    from scraper.grid import generate_grid
    from scraper.listing_scraper import scrape_city_listings

    init_db()
    print(f"[scrape] Generating grid for {args.city} (grid_size={args.grid_size}°)")
    cells = generate_grid(args.city, grid_size=args.grid_size)
    print(f"[scrape] {len(cells)} grid cells generated")
    total = asyncio.run(scrape_city_listings(args.city, cells))
    print(f"[scrape] Done. Total listings upserted: {total}")


def cmd_details(args):
    from scraper.detail_scraper import scrape_city_details

    init_db()
    print(f"[details] Fetching listing details for {args.city}")
    count = asyncio.run(scrape_city_details(args.city))
    print(f"[details] Done. {count} listings updated")


def cmd_calendar(args):
    from availability.calendar_scraper import scrape_city_calendar

    init_db()
    print(f"[calendar] Scraping calendar snapshots for {args.city}")
    total = asyncio.run(scrape_city_calendar(args.city))
    print(f"[calendar] Done. {total} day-rows inserted")


def cmd_analyze(args):
    from analysis.snapshot_diff import run_diff_for_city
    from analysis.occupancy import run_baseline_estimates, run_ml_estimates, train_ml_model

    init_db()
    print(f"[analyze] Running snapshot diff for {args.city}")
    events = run_diff_for_city(args.city)
    print(f"[analyze] {events} booking events detected")

    print("[analyze] Running baseline occupancy estimates")
    run_baseline_estimates(args.city)

    print("[analyze] Training ML model")
    train_ml_model()

    print("[analyze] Running ML occupancy estimates")
    run_ml_estimates()

    print("[analyze] Done")


def cmd_scheduler(_args):
    from availability.scheduler import start_scheduler

    init_db()
    start_scheduler()


def cmd_app(_args):
    app_path = Path(__file__).parent / "app" / "streamlit_app.py"
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path)],
        check=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Airbnb India STR Scraper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_scrape = subparsers.add_parser("scrape", help="Discover listings via grid search")
    p_scrape.add_argument("--city", required=True, help="City name (e.g. goa, bengaluru)")
    p_scrape.add_argument("--grid-size", type=float, default=0.01, help="Grid cell size in degrees")

    p_details = subparsers.add_parser("details", help="Fetch listing details")
    p_details.add_argument("--city", required=True)

    p_cal = subparsers.add_parser("calendar", help="Snapshot calendar availability")
    p_cal.add_argument("--city", required=True)

    p_analyze = subparsers.add_parser("analyze", help="Diff snapshots + run occupancy estimates")
    p_analyze.add_argument("--city", required=True)

    subparsers.add_parser("scheduler", help="Start the daily background scheduler")
    subparsers.add_parser("app", help="Launch the Streamlit dashboard")

    args = parser.parse_args()

    dispatch = {
        "scrape": cmd_scrape,
        "details": cmd_details,
        "calendar": cmd_calendar,
        "analyze": cmd_analyze,
        "scheduler": cmd_scheduler,
        "app": cmd_app,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
