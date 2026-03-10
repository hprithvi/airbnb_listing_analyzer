import sys
#sys.path.insert(0, '..')

import pandas as pd
import matplotlib.pyplot as plt
from db.database import init_db, fetch_all

#init_db()

import streamlit as st
from sqlalchemy import create_engine

engine = create_engine(st.secrets["DATABASE_URL"])

# Load listings
rows = fetch_all('SELECT * FROM listings')
df = pd.DataFrame([dict(r) for r in rows])
print(df.shape)
df.head()

# Price distribution
df['nightly_price'].dropna().hist(bins=50, figsize=(10, 4))
plt.title('Nightly Price Distribution')
plt.xlabel('Price (INR)')
plt.ylabel('Count')
plt.tight_layout()
plt.show()

# Room type breakdown
df['room_type'].value_counts().plot(kind='bar', figsize=(8, 4))
plt.title('Listings by Room Type')
plt.tight_layout()
plt.show()

# Calendar snapshot overview
cal_rows = fetch_all(
    '''
    SELECT date, status, COUNT(*) as count
    FROM calendar_snapshots
    GROUP BY date, status
    ORDER BY date
    '''
)
cal_df = pd.DataFrame([dict(r) for r in cal_rows])
cal_df.head(20)


# Occupancy estimates
from analysis.metrics import get_occupancy_df
occ = get_occupancy_df()
occ.head()