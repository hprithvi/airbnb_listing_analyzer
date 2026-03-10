import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from db.database import init_db, fetch_all

st.set_page_config(
    page_title="Airbnb STR Analytics",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()


def get_cities() -> list[str]:
    rows = fetch_all("SELECT DISTINCT city FROM listings ORDER BY city")
    cities = [r["city"] for r in rows]
    return cities or ["goa", "bengaluru"]


def get_neighbourhoods(city: str) -> list[str]:
    rows = fetch_all(
        "SELECT DISTINCT neighbourhood FROM listings WHERE city = ? AND neighbourhood IS NOT NULL ORDER BY neighbourhood",
        (city,),
    )
    return [r["neighbourhood"] for r in rows]


cities = get_cities()

with st.sidebar:
    st.title("Filters")
    selected_city = st.selectbox("City", cities)
    neighbourhoods = get_neighbourhoods(selected_city)
    selected_neighbourhoods = st.multiselect(
        "Neighbourhoods",
        options=neighbourhoods,
        default=neighbourhoods,
    )
    room_types = ["Entire home/apt", "Private room", "Hotel room", "Shared room"]
    selected_room_types = st.multiselect(
        "Room Types",
        options=room_types,
        default=room_types,
    )
    st.markdown("---")
    st.caption("Airbnb India STR Scraper")

st.session_state["selected_city"] = selected_city
st.session_state["selected_neighbourhoods"] = selected_neighbourhoods
st.session_state["selected_room_types"] = selected_room_types

st.title("Airbnb Short-Term Rental Analytics")
st.markdown(f"**City:** {selected_city.title()}")

from analysis.metrics import get_listings_df, get_occupancy_df

listings_df = get_listings_df(selected_city)
occ_df = get_occupancy_df(selected_city)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Listings", len(listings_df))

if not listings_df.empty and "nightly_price" in listings_df.columns:
    median_price = listings_df["nightly_price"].dropna().median()
    col2.metric("Median Nightly Price", f"₹{median_price:,.0f}" if median_price == median_price else "N/A")
else:
    col2.metric("Median Nightly Price", "N/A")

if not occ_df.empty:
    mean_occ = occ_df["estimated_occupancy"].mean()
    col3.metric("Avg Occupancy", f"{mean_occ:.1%}")
else:
    col3.metric("Avg Occupancy", "N/A")

if not listings_df.empty:
    unique_hoods = listings_df["neighbourhood"].nunique()
    col4.metric("Neighbourhoods", unique_hoods)
else:
    col4.metric("Neighbourhoods", "N/A")

st.markdown("---")
st.info("Use the sidebar to navigate to individual analysis pages.")
