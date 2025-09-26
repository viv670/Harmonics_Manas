"""
Test strict XABCD pattern detection with fixed validation logic
"""
import pandas as pd
import time
from extremum import detect_extremum_points
from strict_xabcd_patterns import detect_strict_xabcd_patterns

# Read and prepare data
df = pd.read_csv('btcusdt_1d.csv')
print(f"Total rows in CSV: {len(df)}")

# Capitalize column names
df.columns = [col.capitalize() for col in df.columns]

# Convert time column to datetime
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

# Detect ALL extremum points
print("\n=== Detecting ALL Extremum Points ===")
extremum_points = detect_extremum_points(df, length=1)

# Test strict XABCD detection with fixed validation
print("\n=== Testing Strict XABCD Detection (Fixed Validation) ===")
print(f"Processing {len(extremum_points)} extremum points...")

start_time = time.time()
patterns = detect_strict_xabcd_patterns(
    extremum_points,
    df,
    log_details=True,
    max_window=100  # Using correct parameter name
)
elapsed = time.time() - start_time

print(f"\n=== Results ===")
print(f"Found {len(patterns)} strict XABCD patterns")
print(f"Time taken: {elapsed:.3f} seconds")

if patterns:
    print("\nFirst 3 patterns found:")
    for i, pattern in enumerate(patterns[:3]):
        print(f"\nPattern {i+1}:")
        print(f"  Type: {'Bullish' if pattern['bullish'] else 'Bearish'}")
        print(f"  X: {pattern['points']['X']['price']:.2f}")
        print(f"  A: {pattern['points']['A']['price']:.2f}")
        print(f"  B: {pattern['points']['B']['price']:.2f}")
        print(f"  C: {pattern['points']['C']['price']:.2f}")
        print(f"  D: {pattern['points']['D']['price']:.2f}")
        print(f"  Start: {pattern['start_time']}")
        print(f"  End: {pattern['end_time']}")
else:
    print("\nNo patterns found - checking if validation is too strict...")

    # Try with a smaller window to see if that helps
    print("\nTrying with smaller window (50 points)...")
    patterns_small = detect_strict_xabcd_patterns(
        extremum_points,
        df,
        log_details=False,
        max_window=50
    )
    print(f"Found {len(patterns_small)} patterns with smaller window")

    # Try to detect just the first 100 extremum points
    print("\nTrying with first 100 extremum points...")
    patterns_subset = detect_strict_xabcd_patterns(
        extremum_points[:100],
        df,
        log_details=False,
        max_window=100
    )
    print(f"Found {len(patterns_subset)} patterns in first 100 points")

print("\n=== Performance Metrics ===")
if elapsed > 0:
    patterns_per_sec = len(patterns) / elapsed if patterns else 0
    points_per_sec = len(extremum_points) / elapsed
    print(f"Patterns found per second: {patterns_per_sec:.1f}")
    print(f"Points processed per second: {points_per_sec:.1f}")
    print(f"Average time per pattern: {(elapsed / len(patterns)):.3f} seconds" if patterns else "N/A")