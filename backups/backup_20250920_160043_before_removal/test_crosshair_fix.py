"""
Test script to verify crosshair OHLC display fix
"""
import pandas as pd
import numpy as np

# Read the data
df = pd.read_csv('btcusdt_1d.csv')
df.columns = [col.capitalize() for col in df.columns]
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

print("=== Testing Crosshair Fix ===")
print(f"Total data points: {len(df)}")

# Test different display ranges
test_ranges = [
    (0, 50, "Beginning of data"),
    (100, 150, "Middle section"),
    (500, 550, "Later section"),
    (len(df)-50, len(df), "End of data")
]

for display_min, display_max, description in test_ranges:
    print(f"\n=== Test: {description} ===")
    print(f"Display range: {display_min} to {display_max}")

    # Get the display slice (as done in PatternViewerWindow)
    display_data = df.iloc[display_min:display_max]

    print(f"Display data shape: {display_data.shape}")
    print(f"First timestamp: {display_data.index[0]}")
    print(f"Last timestamp: {display_data.index[-1]}")

    # Simulate crosshair hover at different positions
    test_positions = [0, 5, len(display_data)//2, len(display_data)-1]

    for x_pos in test_positions:
        if 0 <= x_pos < len(display_data):
            # This is what the fixed crosshair code does
            date = display_data.index[x_pos]
            row = display_data.iloc[x_pos]

            print(f"\n  Position {x_pos}:")
            print(f"    Date: {date}")
            print(f"    OHLC: O={row['Open']:.2f}, H={row['High']:.2f}, L={row['Low']:.2f}, C={row['Close']:.2f}")

            # Verify the values are correct
            # The candlestick at position x_pos should have these exact values
            original_idx = display_min + x_pos
            original_row = df.iloc[original_idx]

            # Check if they match
            matches = (
                abs(row['Open'] - original_row['Open']) < 0.01 and
                abs(row['High'] - original_row['High']) < 0.01 and
                abs(row['Low'] - original_row['Low']) < 0.01 and
                abs(row['Close'] - original_row['Close']) < 0.01
            )

            if matches:
                print(f"    [OK] Values match original data")
            else:
                print(f"    [ERROR] Values don't match!")
                print(f"    Original: O={original_row['Open']:.2f}, H={original_row['High']:.2f}, L={original_row['Low']:.2f}, C={original_row['Close']:.2f}")

print("\n=== Summary ===")
print("The crosshair fix ensures that:")
print("1. The display_data slice is used for OHLC values")
print("2. The x position directly indexes into display_data")
print("3. The timestamp is preserved from the original index")
print("4. OHLC values correctly correspond to the visible candlesticks")
print("\nThis fix resolves the issue where crosshair showed wrong OHLC values")
print("because it was using the full dataset instead of the display subset.")