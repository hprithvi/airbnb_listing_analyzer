from __future__ import annotations

from db.database import upsert_grid_cell

CITY_BBOXES: dict[str, dict[str, float]] = {
    "goa": {"lat_min": 14.89, "lat_max": 15.80, "lon_min": 73.67, "lon_max": 74.33},
    "bengaluru": {"lat_min": 12.83, "lat_max": 13.14, "lon_min": 77.45, "lon_max": 77.78},
}


def _nominatim_bbox(city: str) -> dict[str, float]:
    from geopy.geocoders import Nominatim

    geo = Nominatim(user_agent="airbnb_str_scraper/1.0")
    location = geo.geocode(city, exactly_one=True)
    if location is None:
        raise ValueError(f"Could not geocode city: {city}")
    raw = location.raw
    bb = raw.get("boundingbox")
    if bb:
        return {
            "lat_min": float(bb[0]),
            "lat_max": float(bb[1]),
            "lon_min": float(bb[2]),
            "lon_max": float(bb[3]),
        }
    lat, lon = location.latitude, location.longitude
    delta = 0.3
    return {
        "lat_min": lat - delta,
        "lat_max": lat + delta,
        "lon_min": lon - delta,
        "lon_max": lon + delta,
    }


def generate_grid(city: str, grid_size: float = 0.01) -> list[dict]:
    city_key = city.lower().replace(" ", "_")
    bbox = CITY_BBOXES.get(city_key) or _nominatim_bbox(city)

    cells = []
    lat = bbox["lat_min"]
    while lat < bbox["lat_max"]:
        lon = bbox["lon_min"]
        while lon < bbox["lon_max"]:
            cell_id = upsert_grid_cell(
                city=city_key,
                lat_min=round(lat, 6),
                lat_max=round(min(lat + grid_size, bbox["lat_max"]), 6),
                lon_min=round(lon, 6),
                lon_max=round(min(lon + grid_size, bbox["lon_max"]), 6),
                grid_size=grid_size,
            )
            cells.append(
                {
                    "cell_id": cell_id,
                    "lat_min": round(lat, 6),
                    "lat_max": round(min(lat + grid_size, bbox["lat_max"]), 6),
                    "lon_min": round(lon, 6),
                    "lon_max": round(min(lon + grid_size, bbox["lon_max"]), 6),
                }
            )
            lon += grid_size
        lat += grid_size

    return cells
