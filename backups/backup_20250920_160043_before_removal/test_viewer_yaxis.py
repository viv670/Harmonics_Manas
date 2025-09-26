"""
Test script to verify Y-axis display issue in pattern viewer
"""
import pandas as pd
import numpy as np

# Read sample data
df = pd.read_csv('btcusdt_1d.csv')
df.columns = [col.capitalize() for col in df.columns]
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

# Select a subset of data to analyze
display_min = 100
display_max = 120

# Get the slice
display_data = df.iloc[display_min:display_max]

print("=== Original Data with Index ===")
print(f"Data shape: {display_data.shape}")
print("\nFirst 5 rows:")
for i, (timestamp, row) in enumerate(display_data.head().iterrows()):
    print(f"  Index {i}: Time={timestamp}, High={row['High']:.2f}, Low={row['Low']:.2f}")

# Now reset index like the CandlestickItem does
reset_data = display_data.reset_index(drop=True)

print("\n=== After reset_index(drop=True) ===")
print(f"Data shape: {reset_data.shape}")
print("\nFirst 5 rows:")
for i, (index, row) in enumerate(reset_data.head().iterrows()):
    print(f"  Index {i} (actual={index}): High={row['High']:.2f}, Low={row['Low']:.2f}")

print("\n=== Analysis ===")
print("The reset_index(drop=True) operation:")
print("1. Removes the timestamp index and replaces it with integers 0, 1, 2...")
print("2. The candlesticks are drawn at X positions 0, 1, 2...")
print("3. The Y values (prices) remain the same")
print("4. This is correct behavior for candlestick display")

print("\n=== Checking Y-axis range ===")
min_low = display_data['Low'].min()
max_high = display_data['High'].max()
print(f"Min Low in subset: {min_low:.2f}")
print(f"Max High in subset: {max_high:.2f}")
print(f"Y-axis should range from ~{min_low:.2f} to ~{max_high:.2f}")

# Check if there are extremum points being drawn at wrong Y values
print("\n=== Potential Issue ===")
print("If extremum points are being drawn using display_ep_idx as X and ep_price as Y,")
print("but the ep_price is from a different data range, then the Y values won't match")
print("the candlestick prices visually.")