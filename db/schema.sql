CREATE TABLE IF NOT EXISTS grid_cells (
    id          SERIAL PRIMARY KEY,
    city        TEXT    NOT NULL,
    lat_min     REAL,   lat_max REAL,
    lon_min     REAL,   lon_max REAL,
    grid_size   REAL,                         -- degrees
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS listings (
    id              TEXT PRIMARY KEY,          -- Airbnb listing_id
    city            TEXT NOT NULL,
    grid_cell_id    INTEGER REFERENCES grid_cells(id),
    lat             REAL,   lon REAL,
    room_type       TEXT,
    bedrooms        INTEGER,
    bathrooms       REAL,
    max_guests      INTEGER,
    nightly_price   REAL,
    cleaning_fee    REAL,
    service_fee     REAL,
    neighbourhood   TEXT,
    first_seen_at   TEXT,
    last_seen_at    TEXT
);

CREATE TABLE IF NOT EXISTS listing_details (
    listing_id      TEXT PRIMARY KEY REFERENCES listings(id),
    review_count    INTEGER,
    review_score    REAL,
    host_since      TEXT,
    superhost       INTEGER,                  -- 0 | 1
    amenities       TEXT,                     -- JSON array
    property_type   TEXT,
    description     TEXT,
    scraped_at      TEXT
);

CREATE TABLE IF NOT EXISTS calendar_snapshots (
    id          SERIAL PRIMARY KEY,
    listing_id  TEXT    NOT NULL REFERENCES listings(id),
    date        TEXT    NOT NULL,             -- YYYY-MM-DD
    status      TEXT    NOT NULL,             -- 'available' | 'blocked'
    price       REAL,
    scraped_at  TEXT    NOT NULL,
    UNIQUE(listing_id, date, scraped_at)
);

CREATE TABLE IF NOT EXISTS booking_events (
    id          SERIAL PRIMARY KEY,
    listing_id  TEXT    NOT NULL REFERENCES listings(id),
    date        TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,             -- 'booked' | 'cancelled'
    detected_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS occupancy_estimates (
    id                  SERIAL PRIMARY KEY,
    listing_id          TEXT    NOT NULL REFERENCES listings(id),
    year                INTEGER,
    month               INTEGER,
    estimated_occupancy REAL,                 -- 0.0–1.0
    confidence_score    REAL,                 -- 0.0–1.0
    model_version       TEXT,
    estimated_at        TIMESTAMPTZ DEFAULT NOW()
);
