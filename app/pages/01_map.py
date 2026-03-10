import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd

from analysis.metrics import get_listings_df, get_occupancy_df

st.set_page_config(page_title="Listing Map", layout="wide")
st.title("Listing Map")

city = st.session_state.get("selected_city", "goa")

listings_df = get_listings_df(city)
occ_df = get_occupancy_df(city)

if listings_df.empty:
    st.warning("No listings found. Run `python main.py scrape` first.")
    st.stop()

if not occ_df.empty:
    latest_occ = (
        occ_df.sort_values(["listing_id", "year", "month"])
        .groupby("listing_id")
        .last()
        .reset_index()[["listing_id", "estimated_occupancy"]]
    )
    listings_df = listings_df.merge(
        latest_occ, left_on="id", right_on="listing_id", how="left"
    )
else:
    listings_df["estimated_occupancy"] = None

map_df = listings_df.dropna(subset=["lat", "lon"])

center_lat = map_df["lat"].mean()
center_lon = map_df["lon"].mean()

colour_by = st.selectbox("Colour markers by", ["Occupancy", "Price"])
show_heatmap = st.checkbox("Show heatmap layer")

m = folium.Map(location=[center_lat, center_lon], zoom_start=11)


def _occ_color(occ):
    if occ is None or (isinstance(occ, float) and occ != occ):
        return "gray"
    if occ >= 0.7:
        return "darkred"
    if occ >= 0.5:
        return "orange"
    if occ >= 0.3:
        return "blue"
    return "lightblue"


def _price_color(price):
    if price is None or (isinstance(price, float) and price != price):
        return "gray"
    if price >= 10000:
        return "darkred"
    if price >= 5000:
        return "orange"
    if price >= 2000:
        return "blue"
    return "lightblue"


for _, row in map_df.iterrows():
    if colour_by == "Occupancy":
        color = _occ_color(row.get("estimated_occupancy"))
        popup_val = f"{row.get('estimated_occupancy', 'N/A'):.1%}" if isinstance(row.get("estimated_occupancy"), float) else "N/A"
        popup_text = f"ID: {row['id']}<br>Occ: {popup_val}<br>Price: ₹{row.get('nightly_price', 'N/A')}"
    else:
        color = _price_color(row.get("nightly_price"))
        popup_text = f"ID: {row['id']}<br>Price: ₹{row.get('nightly_price', 'N/A')}<br>Type: {row.get('room_type', 'N/A')}"

    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=5,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=folium.Popup(popup_text, max_width=200),
    ).add_to(m)

if show_heatmap and not map_df.empty:
    from folium.plugins import HeatMap

    heat_data = map_df[["lat", "lon"]].dropna().values.tolist()
    HeatMap(heat_data, radius=12).add_to(m)

st_folium(m, width=1100, height=600)

st.caption(f"Showing {len(map_df)} listings in {city.title()}")
