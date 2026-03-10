from __future__ import annotations

from db.database import fetch_all, fetch_one, insert_booking_event, get_connection


def _get_listing_ids(city: str) -> list[str]:
    rows = fetch_all("SELECT id FROM listings WHERE city = ?", (city,))
    return [r["id"] for r in rows]


def _diff_listing(listing_id: str):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT date, status, scraped_at
        FROM calendar_snapshots
        WHERE listing_id = ?
        ORDER BY date, scraped_at
        """,
        (listing_id,),
    ).fetchall()
    conn.close()

    by_date: dict[str, list[tuple[str, str]]] = {}
    for row in rows:
        by_date.setdefault(row["date"], []).append((row["scraped_at"], row["status"]))

    events_to_insert = []
    for date, snapshots in by_date.items():
        if len(snapshots) < 2:
            continue
        snapshots_sorted = sorted(snapshots, key=lambda x: x[0])
        for i in range(1, len(snapshots_sorted)):
            prev_status = snapshots_sorted[i - 1][1]
            curr_status = snapshots_sorted[i][1]
            if prev_status == curr_status:
                continue
            if prev_status == "available" and curr_status == "blocked":
                events_to_insert.append((listing_id, date, "booked"))
            elif prev_status == "blocked" and curr_status == "available":
                events_to_insert.append((listing_id, date, "cancelled"))

    for listing_id, date, event_type in events_to_insert:
        insert_booking_event(listing_id, date, event_type)

    return len(events_to_insert)


def run_diff_for_city(city: str) -> int:
    listing_ids = _get_listing_ids(city)
    total_events = 0
    for lid in listing_ids:
        total_events += _diff_listing(lid)
    print(f"[diff] {city}: {total_events} booking events detected across {len(listing_ids)} listings")
    return total_events
