"""
Check extremum point count from CSV data
"""
import pandas as pd
from scipy.signal import argrelextrema
import numpy as np

# Read the data
df = pd.read_csv('btcusdt_1d.csv')
print(f"Total rows in CSV: {len(df)}")

# Capitalize column names
df.columns = [col.capitalize() for col in df.columns]

# Convert time column to datetime
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

# Method 1: Count all highs and lows in raw data
all_highs = df['High'].values
all_lows = df['Low'].values
print(f"\nRaw data: {len(all_highs)} high values, {len(all_lows)} low values")
print(f"Total raw points: {len(all_highs) + len(all_lows)}")

# Method 2: Find local extrema using scipy
order = 10  # Common window size for extrema detection
high_indices = argrelextrema(df['High'].values, np.greater, order=order)[0]
low_indices = argrelextrema(df['Low'].values, np.less, order=order)[0]

print(f"\nLocal extrema (order={order}):")
print(f"High points: {len(high_indices)}")
print(f"Low points: {len(low_indices)}")
print(f"Total extremum points: {len(high_indices) + len(low_indices)}")

# Method 3: Try different window sizes
for order in [5, 10, 15, 20]:
    high_indices = argrelextrema(df['High'].values, np.greater, order=order)[0]
    low_indices = argrelextrema(df['Low'].values, np.less, order=order)[0]
    total = len(high_indices) + len(low_indices)
    print(f"\nOrder {order}: {len(high_indices)} highs + {len(low_indices)} lows = {total} total")

# Check if 227+193=420 matches any pattern
print(f"\nYou mentioned: 227 highs + 193 lows = 420 total")
print("This could be from a different extremum detection algorithm or parameters")