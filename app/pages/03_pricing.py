import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.express as px
import pandas as pd

from analysis.metrics import get_listings_df, compute_revenue_estimates

st.set_page_config(page_title="Pricing & Revenue", layout="wide")
st.title("Pricing & Revenue")

city = st.session_state.get("selected_city", "goa")
listings_df = get_listings_df(city)

if listings_df.empty:
    st.warning("No listings found. Run `python main.py scrape` first.")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Nightly Price", "Fees", "Revenue Estimates"])

with tab1:
    price_df = listings_df.dropna(subset=["nightly_price", "room_type"])
    fig = px.box(
        price_df,
        x="room_type",
        y="nightly_price",
        title=f"Nightly Price by Room Type — {city.title()}",
        labels={"nightly_price": "Nightly Price (₹)", "room_type": "Room Type"},
        points="outliers",
    )
    st.plotly_chart(fig, use_container_width=True)

    if not price_df.empty:
        adr_summary = (
            price_df.groupby("room_type")["nightly_price"]
            .agg(["mean", "median", "count"])
            .rename(columns={"mean": "Mean (₹)", "median": "Median (₹)", "count": "Listings"})
            .reset_index()
        )
        st.dataframe(adr_summary, use_container_width=True)

with tab2:
    fee_df = listings_df.dropna(subset=["cleaning_fee"])
    if fee_df.empty:
        st.info("No cleaning fee data available yet.")
    else:
        fig2 = px.histogram(
            fee_df,
            x="cleaning_fee",
            title="Cleaning Fee Distribution",
            labels={"cleaning_fee": "Cleaning Fee (₹)"},
            nbins=40,
        )
        st.plotly_chart(fig2, use_container_width=True)

with tab3:
    rev_df = compute_revenue_estimates(city)
    if rev_df.empty:
        st.info("No revenue estimates available. Run `python main.py analyze` first.")
    else:
        fig3 = px.histogram(
            rev_df.dropna(subset=["estimated_revenue"]),
            x="estimated_revenue",
            title="Estimated Monthly Revenue per Listing",
            labels={"estimated_revenue": "Revenue (₹)"},
            nbins=50,
        )
        st.plotly_chart(fig3, use_container_width=True)

        neighbourhood_rev = (
            rev_df.groupby("neighbourhood")["estimated_revenue"]
            .mean()
            .reset_index()
            .sort_values("estimated_revenue", ascending=False)
        )
        fig4 = px.bar(
            neighbourhood_rev.head(20),
            x="neighbourhood",
            y="estimated_revenue",
            title="Avg Monthly Revenue by Neighbourhood (Top 20)",
            labels={"estimated_revenue": "Avg Revenue (₹)", "neighbourhood": "Neighbourhood"},
        )
        st.plotly_chart(fig4, use_container_width=True)
