import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.express as px
import pandas as pd

from analysis.metrics import get_listings_df, get_listing_details_df

st.set_page_config(page_title="Ratings & Hosts", layout="wide")
st.title("Ratings & Hosts")

city = st.session_state.get("selected_city", "goa")
listings_df = get_listings_df(city)
details_df = get_listing_details_df()

if listings_df.empty:
    st.warning("No listings found. Run `python main.py scrape` first.")
    st.stop()

merged = listings_df.merge(details_df, left_on="id", right_on="listing_id", how="left")

tab1, tab2 = st.tabs(["Review Scores", "Superhost"])

with tab1:
    score_df = merged.dropna(subset=["review_score", "neighbourhood"])
    if score_df.empty:
        st.info("No review score data yet. Run `python main.py details` first.")
    else:
        neighbourhood_scores = (
            score_df.groupby("neighbourhood")["review_score"]
            .mean()
            .reset_index()
            .sort_values("review_score", ascending=True)
        )
        fig = px.bar(
            neighbourhood_scores.tail(20),
            x="review_score",
            y="neighbourhood",
            orientation="h",
            title=f"Average Review Score by Neighbourhood — {city.title()}",
            labels={"review_score": "Avg Review Score", "neighbourhood": "Neighbourhood"},
        )
        fig.update_xaxes(range=[0, 5])
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.histogram(
            score_df,
            x="review_score",
            nbins=30,
            title="Review Score Distribution",
            labels={"review_score": "Review Score"},
        )
        st.plotly_chart(fig2, use_container_width=True)

with tab2:
    sh_df = merged.dropna(subset=["superhost"])
    if sh_df.empty:
        st.info("No superhost data yet. Run `python main.py details` first.")
    else:
        total = len(sh_df)
        superhost_count = int(sh_df["superhost"].sum())
        regular_count = total - superhost_count

        pie_df = pd.DataFrame({
            "Type": ["Superhost", "Regular Host"],
            "Count": [superhost_count, regular_count],
        })
        fig3 = px.pie(
            pie_df,
            names="Type",
            values="Count",
            title=f"Superhost % — {city.title()}",
            color_discrete_sequence=["#FF5A5F", "#484848"],
        )
        st.plotly_chart(fig3, use_container_width=True)

        if "neighbourhood" in sh_df.columns:
            nh_sh = (
                sh_df.groupby("neighbourhood")["superhost"]
                .mean()
                .reset_index()
                .rename(columns={"superhost": "superhost_pct"})
                .sort_values("superhost_pct", ascending=False)
            )
            fig4 = px.bar(
                nh_sh.head(20),
                x="neighbourhood",
                y="superhost_pct",
                title="Superhost % by Neighbourhood (Top 20)",
                labels={"superhost_pct": "Superhost %", "neighbourhood": "Neighbourhood"},
            )
            fig4.update_yaxes(tickformat=".0%")
            st.plotly_chart(fig4, use_container_width=True)
