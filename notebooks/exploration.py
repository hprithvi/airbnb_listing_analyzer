import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / '.env')

import pandas as pd
import matplotlib.pyplot as plt
from db.database import fetch_all, get_connection

# Verify connection
conn = get_connection()
conn.close()
print("[db] Connected to Supabase successfully")

# Load listings
rows = fetch_all('SELECT * FROM listings')
df = pd.DataFrame([dict(r) for r in rows])
print(df.shape)
print(df.head())

# Price distribution
# if sum(df['nightly_price'])>100:
#     df['nightly_price'].dropna().hist(bins=50, figsize=(10, 4))
#     plt.title('Nightly Price Distribution')
#     plt.xlabel('Price (INR)')
#     plt.ylabel('Count')
#     plt.tight_layout()
#     plt.show()

# Room type breakdown
# df['room_type'].value_counts().plot(kind='bar', figsize=(8, 4))
# plt.title('Listings by Room Type')
# plt.tight_layout()
# plt.show()

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
print(cal_df.head(20))

# Occupancy estimates
from analysis.metrics import get_occupancy_df
occ = get_occupancy_df()
print(occ.head())
