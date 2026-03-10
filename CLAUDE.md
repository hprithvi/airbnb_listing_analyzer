# Airbnb Listing Analyzer

## Project Overview

A tool to analyze Airbnb listings — fetching, processing, and surfacing insights from listing data.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Discover listings
python main.py scrape --city goa --grid-size 0.01

# Fetch listing details
python main.py details --city goa

# Snapshot calendar availability
python main.py calendar --city goa

# Run snapshot diff + occupancy estimates
python main.py analyze --city goa

# Start daily background scheduler
python main.py scheduler

# Launch Streamlit dashboard
python main.py app
# or directly:
streamlit run app/streamlit_app.py
```

## Architecture

- **Entry point**: `main.py` (CLI with subcommands: scrape, details, calendar, analyze, scheduler, app)
- **Data sources**: Airbnb API (ExploreSearch, pdp_listing_details, calendar_months) via httpx; auth tokens harvested via Playwright
- **Output**: SQLite at `db/airbnb.db`; Streamlit dashboard at `app/`

## Code Style & Conventions

- Keep functions small and single-purpose
- Prefer explicit over implicit
- No dead code or commented-out blocks
- Do not add docstrings or type annotations to code that wasn't changed

## Workflow

- Never auto-commit — always confirm before committing
- Never push without explicit user approval
- Prefer editing existing files over creating new ones
- Do not over-engineer; solve only what is asked

# Airbnb India STR Scraper

## Project Purpose
Scrape Airbnb listing and calendar data for Goa and Bengaluru to replicate
Airbtics-style market analytics at small scale.

## Tech Stack
- Python 3.11+
- httpx (async HTTP)
- Playwright (auth token harvest)
- SQLite (via sqlite3)
- Pandas + Matplotlib for analysis
- scikit-learn + joblib (ML occupancy model)
- Streamlit + Folium + Plotly (dashboard)
- schedule (cron-like task scheduling)
- fake-useragent + geopy

## Project Structure
/scraper      → grid.py, auth.py, rate_limiter.py, listing_scraper.py, detail_scraper.py
/availability → calendar_scraper.py, scheduler.py
/db           → schema.sql, database.py
/analysis     → snapshot_diff.py, occupancy.py, metrics.py
/app          → streamlit_app.py + pages/ (map, occupancy, pricing, ratings)
/notebooks    → exploration.ipynb

## Key Constraints
- Rate limit all requests: 1 req per 3-5 seconds minimum
- Never use sudo for anything
- All secrets (API keys, proxy credentials) go in .env, never hardcoded
- .env must be in .gitignore
- Use rotating user-agents
- Data lives in SQLite at /db/airbnb.db

## Data Model (core tables)
- grid_cells(id, city, lat_min, lat_max, lon_min, lon_max, grid_size)
- listings(id, city, grid_cell_id, lat, lon, room_type, bedrooms, nightly_price, ...)
- listing_details(listing_id, amenities, review_count, superhost, ...)
- calendar_snapshots(listing_id, date, status, price, scraped_at)
- booking_events(listing_id, date, event_type)
- occupancy_estimates(listing_id, year, month, estimated_occupancy, confidence_score, model_version)

## Do Not Touch
- Do not modify db/schema.sql without asking first
- Do not change the rate limiting logic without asking first
- Do not delete db/occupancy_model.pkl without asking first