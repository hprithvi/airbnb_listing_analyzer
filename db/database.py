import os
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection():
    url = os.getenv("DATABASE_URL")
    if url:
        conn = psycopg2.connect(url, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=int(os.getenv("DB_PORT", "5432")),
            sslmode=os.getenv("DB_SSLMODE", "require"),
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    for stmt in open(SCHEMA_PATH).read().split(";"):
        if stmt.strip():
            cur.execute(stmt)
    conn.commit()
    cur.close()
    conn.close()


def upsert_grid_cell(city: str, lat_min: float, lat_max: float,
                     lon_min: float, lon_max: float, grid_size: float) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO grid_cells (city, lat_min, lat_max, lon_min, lon_max, grid_size)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (city, lat_min, lat_max, lon_min, lon_max, grid_size),
    )
    row_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return row_id


def upsert_listing(listing: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO listings
            (id, city, grid_cell_id, lat, lon, room_type, bedrooms, bathrooms,
             max_guests, nightly_price, cleaning_fee, service_fee, neighbourhood,
             first_seen_at, last_seen_at)
        VALUES
            (%(id)s, %(city)s, %(grid_cell_id)s, %(lat)s, %(lon)s, %(room_type)s,
             %(bedrooms)s, %(bathrooms)s, %(max_guests)s, %(nightly_price)s,
             %(cleaning_fee)s, %(service_fee)s, %(neighbourhood)s, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE SET
            last_seen_at    = NOW(),
            nightly_price   = EXCLUDED.nightly_price,
            cleaning_fee    = EXCLUDED.cleaning_fee,
            service_fee     = EXCLUDED.service_fee,
            neighbourhood   = EXCLUDED.neighbourhood
        """,
        listing,
    )
    conn.commit()
    cur.close()
    conn.close()


def upsert_listing_details(details: dict):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO listing_details
            (listing_id, review_count, review_score, host_since, superhost,
             amenities, property_type, description, scraped_at)
        VALUES
            (%(listing_id)s, %(review_count)s, %(review_score)s, %(host_since)s,
             %(superhost)s, %(amenities)s, %(property_type)s, %(description)s, NOW())
        ON CONFLICT (listing_id) DO UPDATE SET
            review_count  = EXCLUDED.review_count,
            review_score  = EXCLUDED.review_score,
            superhost     = EXCLUDED.superhost,
            amenities     = EXCLUDED.amenities,
            description   = EXCLUDED.description,
            scraped_at    = EXCLUDED.scraped_at
        """,
        details,
    )
    conn.commit()
    cur.close()
    conn.close()


def insert_calendar_snapshot(listing_id: str, date: str, status: str,
                              price: float, scraped_at: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO calendar_snapshots (listing_id, date, status, price, scraped_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (listing_id, date, scraped_at) DO NOTHING
        """,
        (listing_id, date, status, price, scraped_at),
    )
    conn.commit()
    cur.close()
    conn.close()


def insert_booking_event(listing_id: str, date: str, event_type: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO booking_events (listing_id, date, event_type) VALUES (%s, %s, %s)",
        (listing_id, date, event_type),
    )
    conn.commit()
    cur.close()
    conn.close()


def upsert_occupancy_estimate(listing_id: str, year: int, month: int,
                               estimated_occupancy: float, confidence_score: float,
                               model_version: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO occupancy_estimates
            (listing_id, year, month, estimated_occupancy, confidence_score, model_version)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (listing_id, year, month, estimated_occupancy, confidence_score, model_version),
    )
    conn.commit()
    cur.close()
    conn.close()


def fetch_all(query: str, params: tuple = ()) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def fetch_one(query: str, params: tuple = ()):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row
