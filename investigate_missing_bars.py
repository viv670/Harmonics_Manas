"""
Investigate why bars 233, 249, and 258 are NOT detected as extremum points
"""

import pandas as pd
import numpy as np

# Load the data
print("Loading BTC data...")
df = pd.read_csv('btcusdt_1d.csv')
# Rename columns to capitalized format
df.columns = [col.capitalize() if col in ['time', 'open', 'high', 'low', 'close', 'volume'] else col for col in df.columns]
if 'Time' in df.columns:
    df['Date'] = pd.to_datetime(df['Time'])
elif 'Date' not in df.columns:
    df['Date'] = pd.to_datetime(df.index)

print(f"Loaded {len(df)} candles")
print(f"Columns: {df.columns.tolist()}\n")

# Inspect the target bars
target_bars = [233, 249, 252, 258]

print("="*70)
print("INSPECTING TARGET BARS")
print("="*70)

for bar_idx in target_bars:
    print(f"\n--- Bar {bar_idx} ---")
    bar = df.iloc[bar_idx]
    print(f"Date: {bar['Date']}")
    print(f"High: {bar['High']:.2f}")
    print(f"Low: {bar['Low']:.2f}")
    print(f"Open: {bar['Open']:.2f}")
    print(f"Close: {bar['Close']:.2f}")

    # Check if it's a high pivot with length=1
    if bar_idx > 0 and bar_idx < len(df) - 1:
        left_high = df['High'].iloc[bar_idx - 1]
        right_high = df['High'].iloc[bar_idx + 1]
        is_high_pivot_1 = bar['High'] >= left_high and bar['High'] >= right_high
        print(f"\nWith length=1 (comparing to 1 bar on each side):")
        print(f"  Left high ({bar_idx-1}): {left_high:.2f}")
        print(f"  Current high ({bar_idx}): {bar['High']:.2f}")
        print(f"  Right high ({bar_idx+1}): {right_high:.2f}")
        print(f"  Is HIGH pivot? {is_high_pivot_1}")

        left_low = df['Low'].iloc[bar_idx - 1]
        right_low = df['Low'].iloc[bar_idx + 1]
        is_low_pivot_1 = bar['Low'] <= left_low and bar['Low'] <= right_low
        print(f"\n  Left low ({bar_idx-1}): {left_low:.2f}")
        print(f"  Current low ({bar_idx}): {bar['Low']:.2f}")
        print(f"  Right low ({bar_idx+1}): {right_low:.2f}")
        print(f"  Is LOW pivot? {is_low_pivot_1}")

    # Check if it's a high/low pivot with length=2
    if bar_idx > 1 and bar_idx < len(df) - 2:
        left_highs = df['High'].iloc[bar_idx - 2:bar_idx]
        right_highs = df['High'].iloc[bar_idx + 1:bar_idx + 3]
        is_high_pivot_2 = bar['High'] >= left_highs.max() and bar['High'] >= right_highs.max()
        print(f"\nWith length=2 (comparing to 2 bars on each side):")
        print(f"  Left highs ({bar_idx-2},{bar_idx-1}): {left_highs.values}")
        print(f"  Current high ({bar_idx}): {bar['High']:.2f}")
        print(f"  Right highs ({bar_idx+1},{bar_idx+2}): {right_highs.values}")
        print(f"  Is HIGH pivot? {is_high_pivot_2}")

        left_lows = df['Low'].iloc[bar_idx - 2:bar_idx]
        right_lows = df['Low'].iloc[bar_idx + 1:bar_idx + 3]
        is_low_pivot_2 = bar['Low'] <= left_lows.min() and bar['Low'] <= right_lows.min()
        print(f"\n  Left lows ({bar_idx-2},{bar_idx-1}): {left_lows.values}")
        print(f"  Current low ({bar_idx}): {bar['Low']:.2f}")
        print(f"  Right lows ({bar_idx+1},{bar_idx+2}): {right_lows.values}")
        print(f"  Is LOW pivot? {is_low_pivot_2}")

# Now look at surrounding context
print("\n\n" + "="*70)
print("SURROUNDING CONTEXT (Bars 230-265)")
print("="*70)
print(f"{'Bar':<5} {'Date':<12} {'High':<10} {'Low':<10} {'Is_High_Pvt':<12} {'Is_Low_Pvt':<12}")
print("-"*70)

for i in range(230, 265):
    bar = df.iloc[i]

    # Check pivots with length=1
    is_high_pvt = False
    is_low_pvt = False

    if i > 0 and i < len(df) - 1:
        left_high = df['High'].iloc[i - 1]
        right_high = df['High'].iloc[i + 1]
        is_high_pvt = bar['High'] >= left_high and bar['High'] >= right_high

        left_low = df['Low'].iloc[i - 1]
        right_low = df['Low'].iloc[i + 1]
        is_low_pvt = bar['Low'] <= left_low and bar['Low'] <= right_low

    marker = ""
    if i in target_bars:
        marker = " <-- TARGET"

    high_mark = "✓" if is_high_pvt else ""
    low_mark = "✓" if is_low_pvt else ""

    print(f"{i:<5} {str(bar['Date'])[:10]:<12} {bar['High']:<10.2f} {bar['Low']:<10.2f} {high_mark:<12} {low_mark:<12}{marker}")

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("If bars 233, 249, 258 show no ✓ marks, they are NOT detected as pivots")
print("because they don't meet the strict >= or <= criteria compared to neighbors.")
print("\nThis explains why the pattern at (233, 249, 252, 258) is never detected!")
