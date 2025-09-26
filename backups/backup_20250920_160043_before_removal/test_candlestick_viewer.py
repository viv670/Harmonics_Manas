"""
Test script to debug Y-axis discrepancy in pattern viewer
"""
import pandas as pd
import numpy as np

# Read sample data
df = pd.read_csv('btcusdt_1d.csv')
df.columns = [col.capitalize() for col in df.columns]
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

# Simulate what happens in the pattern viewer
# Let's say we're looking at a pattern in a specific range
display_min = 100
display_max = 120

# Get the slice
display_data = df.iloc[display_min:display_max].copy()

print("=== Original Data Slice ===")
print(f"Shape: {display_data.shape}")
print(f"Index type: {type(display_data.index)}")
print(f"First index: {display_data.index[0]}")
print(f"Last index: {display_data.index[-1]}")

print("\n=== Price ranges in original slice ===")
print(f"Low range: {display_data['Low'].min():.2f} to {display_data['Low'].max():.2f}")
print(f"High range: {display_data['High'].min():.2f} to {display_data['High'].max():.2f}")
print(f"Overall price range: {display_data['Low'].min():.2f} to {display_data['High'].max():.2f}")

# Reset index like the pattern viewer does
reset_data = display_data.reset_index(drop=True)

print("\n=== After reset_index(drop=True) ===")
print(f"Shape: {reset_data.shape}")
print(f"Index type: {type(reset_data.index)}")
print(f"First index: {reset_data.index[0]}")
print(f"Last index: {reset_data.index[-1]}")

print("\n=== Price ranges after reset ===")
print(f"Low range: {reset_data['Low'].min():.2f} to {reset_data['Low'].max():.2f}")
print(f"High range: {reset_data['High'].min():.2f} to {reset_data['High'].max():.2f}")
print(f"Overall price range: {reset_data['Low'].min():.2f} to {reset_data['High'].max():.2f}")

print("\n=== Checking individual candlesticks ===")
for i in range(min(3, len(reset_data))):
    print(f"Candle {i}:")
    print(f"  Open: {reset_data.iloc[i]['Open']:.2f}")
    print(f"  High: {reset_data.iloc[i]['High']:.2f}")
    print(f"  Low: {reset_data.iloc[i]['Low']:.2f}")
    print(f"  Close: {reset_data.iloc[i]['Close']:.2f}")

print("\n=== What the Y-axis should show ===")
y_min = reset_data['Low'].min() * 0.999
y_max = reset_data['High'].max() * 1.001
print(f"Y-axis min (with padding): {y_min:.2f}")
print(f"Y-axis max (with padding): {y_max:.2f}")

print("\n=== Debugging the CandlestickItem ===")
print("The CandlestickItem uses reset_data where:")
print("- X coordinates are 0, 1, 2, 3... (index positions)")
print("- Y coordinates are the actual price values")
print("- The issue might be in how pyqtgraph is interpreting the data")

print("\n=== Checking for NaN or invalid values ===")
print(f"NaN in Open: {reset_data['Open'].isna().sum()}")
print(f"NaN in High: {reset_data['High'].isna().sum()}")
print(f"NaN in Low: {reset_data['Low'].isna().sum()}")
print(f"NaN in Close: {reset_data['Close'].isna().sum()}")

# Check if any prices are zero or negative
print(f"\nZero or negative Open: {(reset_data['Open'] <= 0).sum()}")
print(f"Zero or negative High: {(reset_data['High'] <= 0).sum()}")
print(f"Zero or negative Low: {(reset_data['Low'] <= 0).sum()}")
print(f"Zero or negative Close: {(reset_data['Close'] <= 0).sum()}")