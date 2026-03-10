import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.express as px
import pandas as pd

from analysis.metrics import get_occupancy_df

st.set_page_config(page_title="Occupancy Trends", layout="wide")
st.title("Occupancy Trends")

city = st.session_state.get("selected_city", "goa")
occ_df = get_occupancy_df(city)

if occ_df.empty:
    st.warning("No occupancy data. Run `python main.py analyze` first.")
    st.stop()

occ_df["period"] = occ_df["year"].astype(str) + "-" + occ_df["month"].astype(str).str.zfill(2)

tab1, tab2 = st.tabs(["By Neighbourhood", "Listing Drill-down"])

with tab1:
    neighbourhood_occ = (
        occ_df.groupby(["period", "neighbourhood"])["estimated_occupancy"]
        .mean()
        .reset_index()
    )
    hoods = neighbourhood_occ["neighbourhood"].dropna().unique().tolist()
    selected = st.multiselect("Select neighbourhoods", hoods, default=hoods[:5] if len(hoods) > 5 else hoods)
    filtered = neighbourhood_occ[neighbourhood_occ["neighbourhood"].isin(selected)]

    fig = px.line(
        filtered,
        x="period",
        y="estimated_occupancy",
        color="neighbourhood",
        title=f"Monthly Average Occupancy — {city.title()}",
        labels={"estimated_occupancy": "Occupancy Rate", "period": "Month"},
    )
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    listing_ids = occ_df["listing_id"].unique().tolist()
    selected_listing = st.selectbox("Select listing", listing_ids)
    listing_occ = occ_df[occ_df["listing_id"] == selected_listing].sort_values("period")

    fig2 = px.bar(
        listing_occ,
        x="period",
        y="estimated_occupancy",
        title=f"Occupancy for Listing {selected_listing}",
        labels={"estimated_occupancy": "Occupancy Rate", "period": "Month"},
        color="confidence_score",
        color_continuous_scale="Blues",
    )
    fig2.update_yaxes(tickformat=".0%", range=[0, 1])
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(listing_occ[["period", "estimated_occupancy", "confidence_score", "model_version"]])
