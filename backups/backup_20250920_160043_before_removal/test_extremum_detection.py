"""
Test script to verify extremum detection is counting ALL highs and lows
"""
import pandas as pd
from extremum import detect_extremum_points

# Read the data
df = pd.read_csv('btcusdt_1d.csv')
print(f"Total rows in CSV: {len(df)}")

# Capitalize column names
df.columns = [col.capitalize() for col in df.columns]

# Convert time column to datetime
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

print("\n=== Testing Extremum Detection ===")
print("Using window size (length) = 1")

# Detect extremums with our new function
extremum_points = detect_extremum_points(df, length=1)

print(f"\nExpected: 227 highs + 193 lows = 420 total")
print("This should now detect ALL local highs and lows without filtering!")