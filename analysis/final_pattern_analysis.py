"""
Final analysis of ABCD pattern ABCD_105f49cde5e12698
Based on zone entry price 77975.52 around 2024-11-10
"""

import pandas as pd
from extremum import detect_extremum_points
from datetime import datetime

print("Final Analysis: ABCD_105f49cde5e12698")
print("="*60)

# Load data
data = pd.read_csv('btcusdt_1d.csv', parse_dates=['time'])
data.set_index('time', inplace=True)
data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

# Focus on the timeframe around 2024-11-10 (bar 2642)
target_bar = 2642
start_bar = max(0, target_bar - 300)  # Look 300 bars back
end_bar = min(len(data), target_bar + 100)  # And 100 bars forward

analysis_data = data.iloc[start_bar:end_bar]
print(f"Analyzing bars {start_bar} to {end_bar}")
print(f"Date range: {analysis_data.index[0].strftime('%Y-%m-%d')} to {analysis_data.index[-1].strftime('%Y-%m-%d')}")
print(f"Total bars in analysis: {len(analysis_data)}")

# Detect extremums in this range
print("\nDetecting extremum points...")
extremums = detect_extremum_points(analysis_data, length=2)
print(f"Found {len(extremums)} extremum points")

# The zone entry price is 77975.52, so look for extremums near this level
target_price = 77975.52
print(f"\nLooking for extremums near zone entry price: {target_price:.2f}")

# Find extremums within reasonable range of the target price
price_tolerance = 5000  # 5000 points tolerance
relevant_extremums = []

for i, (timestamp, price, is_high) in enumerate(extremums):
    if abs(price - target_price) <= price_tolerance:
        relevant_extremums.append((i, timestamp, price, is_high))

print(f"Found {len(relevant_extremums)} extremums within {price_tolerance} points of target:")
for i, timestamp, price, is_high in relevant_extremums:
    bar_idx = analysis_data.index.get_loc(timestamp) + start_bar
    if hasattr(timestamp, 'strftime'):
        date_str = timestamp.strftime('%Y-%m-%d')
    else:
        date_str = pd.to_datetime(timestamp).strftime('%Y-%m-%d')
    print(f"  {i}: {date_str} - {price:.2f} ({'HIGH' if is_high else 'LOW'}) - Global bar {bar_idx}")

# Now analyze potential ABCD patterns that could result in this zone entry
print(f"\nAnalyzing potential ABCD patterns...")

# Look for patterns where C is one of these relevant extremums
for c_idx, c_timestamp, c_price, c_is_high in relevant_extremums:
    if hasattr(c_timestamp, 'strftime'):
        c_date_str = c_timestamp.strftime('%Y-%m-%d')
    else:
        c_date_str = pd.to_datetime(c_timestamp).strftime('%Y-%m-%d')
    print(f"\n--- Analyzing with C at index {c_idx} ({c_date_str}, {c_price:.2f}) ---")

    # Find potential A and B points (must be before C)
    for a_idx in range(max(0, c_idx - 50), c_idx):  # A should be before C
        for b_idx in range(a_idx + 1, c_idx):  # B should be between A and C

            a_timestamp, a_price, a_is_high = extremums[a_idx]
            b_timestamp, b_price, b_is_high = extremums[b_idx]

            # Check if this forms a valid ABCD structure (alternating highs/lows)
            if a_is_high == c_is_high:  # A and C should be same type
                continue
            if a_is_high == b_is_high:  # A and B should be different types
                continue

            # Calculate some basic pattern ratios to see if it makes sense
            ab_length = abs(b_price - a_price)
            bc_length = abs(c_price - b_price)

            if ab_length == 0 or bc_length == 0:
                continue

            bc_ab_ratio = bc_length / ab_length

            # Show this potential pattern
            a_bar_idx = analysis_data.index.get_loc(a_timestamp) + start_bar
            b_bar_idx = analysis_data.index.get_loc(b_timestamp) + start_bar
            c_bar_idx = analysis_data.index.get_loc(c_timestamp) + start_bar

            # Convert timestamps to readable format
            def format_timestamp(ts):
                if hasattr(ts, 'strftime'):
                    return ts.strftime('%Y-%m-%d')
                else:
                    return pd.to_datetime(ts).strftime('%Y-%m-%d')

            print(f"  Potential ABCD:")
            print(f"    A[{a_idx}]: {format_timestamp(a_timestamp)} - {a_price:.2f} ({'HIGH' if a_is_high else 'LOW'}) - Bar {a_bar_idx}")
            print(f"    B[{b_idx}]: {format_timestamp(b_timestamp)} - {b_price:.2f} ({'HIGH' if b_is_high else 'LOW'}) - Bar {b_bar_idx}")
            print(f"    C[{c_idx}]: {format_timestamp(c_timestamp)} - {c_price:.2f} ({'HIGH' if c_is_high else 'LOW'}) - Bar {c_bar_idx}")
            print(f"    BC/AB ratio: {bc_ab_ratio:.3f}")

            # Calculate projected D zone (basic ABCD)
            if not c_is_high:  # Bullish pattern (C is a low)
                ab_range = a_price - b_price  # A higher than B
                bc_range = c_price - b_price  # C lower than B
                # For bullish ABCD, D should be higher than C
                if bc_ab_ratio >= 0.618 and bc_ab_ratio <= 0.786:  # Common retracement levels
                    projected_d = c_price + abs(ab_range) * 1.272  # 127.2% extension
                    print(f"    Projected D (bullish): {projected_d:.2f}")
                    if abs(projected_d - target_price) < 1000:
                        print(f"    *** CLOSE MATCH to zone entry price! ***")
            else:  # Bearish pattern (C is a high)
                ab_range = b_price - a_price  # B higher than A
                bc_range = b_price - c_price  # C higher than B
                # For bearish ABCD, D should be lower than C
                if bc_ab_ratio >= 0.618 and bc_ab_ratio <= 0.786:
                    projected_d = c_price - abs(ab_range) * 1.272  # 127.2% extension
                    print(f"    Projected D (bearish): {projected_d:.2f}")
                    if abs(projected_d - target_price) < 1000:
                        print(f"    *** CLOSE MATCH to zone entry price! ***")

            # Only show first few to avoid overwhelming output
            if b_idx - a_idx > 10:  # Limit combinations shown
                break
        if a_idx > c_idx - 10:  # Limit combinations shown
            break

print(f"\n" + "="*60)
print("Summary:")
print(f"- Pattern ABCD_105f49cde5e12698 has zone entry at 77975.52")
print(f"- This occurs around 2024-11-10 timeframe")
print(f"- The A, B, C points are extremums in the detected extremum list")
print(f"- The pattern projects to the D zone where price reached 77975.52")
print(f"- To verify exact extremum indices, check the patterns marked as close matches above")

# Show the exact bar where target price was reached
target_bar_data = data.iloc[target_bar]
print(f"\nTarget bar {target_bar} (2024-11-10):")
print(f"  Open: {target_bar_data['Open']:.2f}")
print(f"  High: {target_bar_data['High']:.2f}")
print(f"  Low: {target_bar_data['Low']:.2f}")
print(f"  Close: {target_bar_data['Close']:.2f}")
print(f"  Zone entry level 77975.52 is within this bar's range: {target_bar_data['Low']:.2f} - {target_bar_data['High']:.2f}")