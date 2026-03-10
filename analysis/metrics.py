from __future__ import annotations

import pandas as pd

from db.database import fetch_all


def get_listings_df(city: str | None = None) -> pd.DataFrame:
    if city:
        rows = fetch_all(
            "SELECT * FROM listings WHERE city = ?",
            (city,),
        )
    else:
        rows = fetch_all("SELECT * FROM listings")
    return pd.DataFrame([dict(r) for r in rows])


def get_listing_details_df() -> pd.DataFrame:
    rows = fetch_all("SELECT * FROM listing_details")
    return pd.DataFrame([dict(r) for r in rows])


def get_occupancy_df(city: str | None = None, model_version: str | None = None) -> pd.DataFrame:
    query = """
        SELECT oe.*, l.city, l.neighbourhood, l.room_type, l.nightly_price
        FROM occupancy_estimates oe
        JOIN listings l ON l.id = oe.listing_id
    """
    conditions = []
    params: list = []
    if city:
        conditions.append("l.city = ?")
        params.append(city)
    if model_version:
        conditions.append("oe.model_version = ?")
        params.append(model_version)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    rows = fetch_all(query, tuple(params))
    return pd.DataFrame([dict(r) for r in rows])


def compute_adr(city: str | None = None) -> pd.DataFrame:
    df = get_listings_df(city)
    if df.empty:
        return pd.DataFrame()
    adr = (
        df.dropna(subset=["nightly_price"])
        .groupby("neighbourhood")["nightly_price"]
        .agg(["mean", "median", "count"])
        .rename(columns={"mean": "adr_mean", "median": "adr_median", "count": "listing_count"})
        .reset_index()
    )
    return adr


def compute_revenue_estimates(city: str | None = None) -> pd.DataFrame:
    occ = get_occupancy_df(city)
    listings = get_listings_df(city)
    if occ.empty or listings.empty:
        return pd.DataFrame()

    merged = occ.merge(
        listings[["id", "nightly_price", "neighbourhood", "room_type"]],
        left_on="listing_id",
        right_on="id",
        how="left",
        suffixes=("", "_l"),
    )
    merged = merged.dropna(subset=["nightly_price", "estimated_occupancy"])
    import calendar
    merged["days_in_month"] = merged.apply(
        lambda r: calendar.monthrange(int(r["year"]), int(r["month"]))[1], axis=1
    )
    merged["occupied_days"] = merged["estimated_occupancy"] * merged["days_in_month"]
    merged["estimated_revenue"] = merged["occupied_days"] * merged["nightly_price"]
    return merged


def neighbourhood_summary(city: str | None = None) -> pd.DataFrame:
    rev = compute_revenue_estimates(city)
    listings = get_listings_df(city)
    details = get_listing_details_df()

    if listings.empty:
        return pd.DataFrame()

    full = listings.merge(details, left_on="id", right_on="listing_id", how="left")

    summary = (
        full.groupby("neighbourhood")
        .agg(
            listing_count=("id", "count"),
            mean_price=("nightly_price", "mean"),
            mean_review_score=("review_score", "mean"),
            superhost_pct=("superhost", "mean"),
        )
        .reset_index()
    )

    if not rev.empty:
        occ_summary = (
            rev.groupby("neighbourhood_x")
            .agg(mean_occupancy=("estimated_occupancy", "mean"))
            .reset_index()
            .rename(columns={"neighbourhood_x": "neighbourhood"})
        )
        summary = summary.merge(occ_summary, on="neighbourhood", how="left")

    return summary
