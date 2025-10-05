"""
Manual analysis of pattern ABCD_105f49cde5e12698 based on known information
"""

import pandas as pd
from datetime import datetime

print("Manual Pattern Analysis for ABCD_105f49cde5e12698")
print("="*60)

# Load data
data = pd.read_csv('btcusdt_1d.csv', parse_dates=['time'])
data.set_index('time', inplace=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

print(f"Total data points: {len(data)}")
print(f"Date range: {data.index[0]} to {data.index[-1]}")

# Find bars around the zone entry price of 77975.52
target_price = 77975.52
tolerance = 100  # Price tolerance

print(f"\nSearching for bars near the zone entry price: {target_price:.2f}")

# Find bars where price was near this level
near_target = data[
    (data['High'] >= target_price - tolerance) &
    (data['Low'] <= target_price + tolerance)
]

if len(near_target) > 0:
    print(f"\nFound {len(near_target)} bars near target price:")
    for idx, (timestamp, row) in enumerate(near_target.iterrows()):
        print(f"  {idx+1}: {timestamp.strftime('%Y-%m-%d')} - H:{row['High']:.2f} L:{row['Low']:.2f} C:{row['Close']:.2f}")

        # Show the exact bar index in the full dataset
        bar_idx = data.index.get_loc(timestamp)
        print(f"       Bar index: {bar_idx}")

    # Since we know this is an ABCD pattern entering a zone, let's look for potential A, B, C points
    # The C point would likely be near this price level
    print(f"\nAnalyzing potential pattern structure...")

    # Look for the most likely C point (should be near the zone entry)
    c_candidates = near_target.copy()

    for timestamp, row in c_candidates.iterrows():
        bar_idx = data.index.get_loc(timestamp)
        print(f"\nAnalyzing potential C point at {timestamp.strftime('%Y-%m-%d')} (bar {bar_idx}):")
        print(f"  Price range: {row['Low']:.2f} - {row['High']:.2f}")

        # Look backwards for potential A and B points
        lookback_data = data.iloc[max(0, bar_idx-200):bar_idx+1]

        # Find significant highs and lows in this range
        print(f"  Looking for A and B points in previous 200 bars...")

        # Find local highs and lows
        window = 5
        highs = []
        lows = []

        for i in range(window, len(lookback_data) - window):
            current_bar = lookback_data.iloc[i]
            left_bars = lookback_data.iloc[i-window:i]
            right_bars = lookback_data.iloc[i+1:i+window+1]

            # Check if this is a local high
            if (current_bar['High'] >= left_bars['High'].max() and
                current_bar['High'] >= right_bars['High'].max()):
                global_idx = max(0, bar_idx-200) + i
                highs.append((lookback_data.index[i], current_bar['High'], global_idx))

            # Check if this is a local low
            if (current_bar['Low'] <= left_bars['Low'].min() and
                current_bar['Low'] <= right_bars['Low'].min()):
                global_idx = max(0, bar_idx-200) + i
                lows.append((lookback_data.index[i], current_bar['Low'], global_idx))

        print(f"    Found {len(highs)} local highs and {len(lows)} local lows")

        # Show most significant extremes
        if highs:
            highs.sort(key=lambda x: x[1], reverse=True)  # Sort by price
            print(f"    Top 5 highs:")
            for i, (ts, price, g_idx) in enumerate(highs[:5]):
                print(f"      {i+1}: {ts.strftime('%Y-%m-%d')} - {price:.2f} (bar {g_idx})")

        if lows:
            lows.sort(key=lambda x: x[1])  # Sort by price
            print(f"    Top 5 lows:")
            for i, (ts, price, g_idx) in enumerate(lows[:5]):
                print(f"      {i+1}: {ts.strftime('%Y-%m-%d')} - {price:.2f} (bar {g_idx})")

        # Only analyze first candidate to avoid too much output
        break

else:
    print(f"No bars found near target price {target_price:.2f}")

    # Search in a wider range
    print(f"\nSearching in wider price range...")
    wider_range = data[
        (data['High'] >= 75000) & (data['Low'] <= 80000)
    ]

    if len(wider_range) > 0:
        print(f"Found {len(wider_range)} bars in range 75000-80000:")
        for idx, (timestamp, row) in enumerate(wider_range.head(10).iterrows()):
            bar_idx = data.index.get_loc(timestamp)
            print(f"  {timestamp.strftime('%Y-%m-%d')} (bar {bar_idx}) - H:{row['High']:.2f} L:{row['Low']:.2f}")

# Also show general information about the pattern hash
print(f"\n" + "="*60)
print("Pattern Hash Analysis:")
print(f"Target hash: 105f49cde5e12698")
print("This hash suggests the pattern was generated from specific extremum indices.")
print("The pattern appears to be related to high price levels around 77975.52.")

# Show approximate timeframe when this price level was reached
high_price_data = data[data['High'] > 77000]
if len(high_price_data) > 0:
    print(f"\nHigh price timeframe (>77000):")
    print(f"  First occurrence: {high_price_data.index[0].strftime('%Y-%m-%d')}")
    print(f"  Last occurrence: {high_price_data.index[-1].strftime('%Y-%m-%d')}")
    print(f"  Total bars: {len(high_price_data)}")