from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder
import joblib

from db.database import fetch_all, upsert_occupancy_estimate, get_connection

MODEL_PATH = Path("db/occupancy_model.pkl")
MODEL_VERSION_BASELINE = "baseline_v1"
MODEL_VERSION_ML = "gbr_v1"


def _load_booking_data() -> pd.DataFrame:
    rows = fetch_all(
        """
        SELECT
            be.listing_id,
            EXTRACT(YEAR FROM be.date::date)::int AS year,
            EXTRACT(MONTH FROM be.date::date)::int AS month,
            COUNT(*) AS booked_days
        FROM booking_events be
        WHERE be.event_type = 'booked'
        GROUP BY be.listing_id, year, month
        """
    )
    return pd.DataFrame([dict(r) for r in rows])


def _load_observed_days() -> pd.DataFrame:
    rows = fetch_all(
        """
        SELECT
            listing_id,
            EXTRACT(YEAR FROM date::date)::int AS year,
            EXTRACT(MONTH FROM date::date)::int AS month,
            COUNT(DISTINCT date) AS observed_days
        FROM calendar_snapshots
        GROUP BY listing_id, year, month
        """
    )
    return pd.DataFrame([dict(r) for r in rows])


def _load_listing_features() -> pd.DataFrame:
    rows = fetch_all(
        """
        SELECT
            l.id AS listing_id,
            l.nightly_price,
            l.room_type,
            l.bedrooms,
            l.neighbourhood,
            ld.review_score,
            ld.review_count,
            ld.superhost
        FROM listings l
        LEFT JOIN listing_details ld ON ld.listing_id = l.id
        """
    )
    return pd.DataFrame([dict(r) for r in rows])


def _compute_baseline(city: str | None = None) -> pd.DataFrame:
    booking_df = _load_booking_data()
    observed_df = _load_observed_days()

    if booking_df.empty or observed_df.empty:
        return pd.DataFrame()

    merged = observed_df.merge(booking_df, on=["listing_id", "year", "month"], how="left")
    merged["booked_days"] = merged["booked_days"].fillna(0)
    merged["observed_days"] = merged["observed_days"].clip(lower=1)
    merged["occupancy"] = (merged["booked_days"] / merged["observed_days"]).clip(0, 1)
    merged["confidence"] = (merged["observed_days"] / 30).clip(0, 1)
    return merged


def run_baseline_estimates(city: str | None = None):
    df = _compute_baseline(city)
    if df.empty:
        print("[occupancy] No data for baseline estimates.")
        return 0

    count = 0
    for _, row in df.iterrows():
        upsert_occupancy_estimate(
            listing_id=row["listing_id"],
            year=int(row["year"]),
            month=int(row["month"]),
            estimated_occupancy=round(float(row["occupancy"]), 4),
            confidence_score=round(float(row["confidence"]), 4),
            model_version=MODEL_VERSION_BASELINE,
        )
        count += 1
    print(f"[occupancy] Baseline: {count} estimates inserted")
    return count


def _encode_features(df: pd.DataFrame) -> pd.DataFrame:
    cat_cols = ["room_type", "neighbourhood"]
    for col in cat_cols:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].fillna("unknown").astype(str))
    return df


def train_ml_model():
    baseline = _compute_baseline()
    if baseline.empty:
        print("[occupancy] Not enough data to train ML model.")
        return None

    features_df = _load_listing_features()
    df = baseline.merge(features_df, on="listing_id", how="left")

    feature_cols = [
        "nightly_price", "room_type", "bedrooms", "review_score",
        "review_count", "neighbourhood", "superhost",
    ]
    df = df.dropna(subset=["occupancy"] + feature_cols)
    if len(df) < 10:
        print("[occupancy] Insufficient data rows for ML training.")
        return None

    df = _encode_features(df)
    X = df[feature_cols].fillna(0)
    y = df["occupancy"]

    model = GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=42)
    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_cols": feature_cols}, MODEL_PATH)
    print(f"[occupancy] ML model trained on {len(df)} rows, saved to {MODEL_PATH}")
    return model


def run_ml_estimates():
    if not MODEL_PATH.exists():
        model_bundle = None
    else:
        model_bundle = joblib.load(MODEL_PATH)

    if model_bundle is None:
        model_bundle_trained = train_ml_model()
        if model_bundle_trained is None:
            return 0
        model_bundle = joblib.load(MODEL_PATH)

    model = model_bundle["model"]
    feature_cols = model_bundle["feature_cols"]

    observed_df = _load_observed_days()
    features_df = _load_listing_features()
    df = observed_df.merge(features_df, on="listing_id", how="left")
    df = _encode_features(df)
    df_valid = df.dropna(subset=feature_cols)

    if df_valid.empty:
        print("[occupancy] No valid rows for ML inference.")
        return 0

    X = df_valid[feature_cols].fillna(0)
    preds = model.predict(X).clip(0, 1)

    count = 0
    for i, (_, row) in enumerate(df_valid.iterrows()):
        confidence = min(1.0, float(row["observed_days"]) / 30)
        upsert_occupancy_estimate(
            listing_id=row["listing_id"],
            year=int(row["year"]),
            month=int(row["month"]),
            estimated_occupancy=round(float(preds[i]), 4),
            confidence_score=round(confidence, 4),
            model_version=MODEL_VERSION_ML,
        )
        count += 1

    print(f"[occupancy] ML: {count} estimates inserted")
    return count
