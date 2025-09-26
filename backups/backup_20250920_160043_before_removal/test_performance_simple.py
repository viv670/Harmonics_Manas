"""
Simple performance test for strict XABCD pattern detection
"""

import pandas as pd
import time
from extremum import detect_extremum_points
from strict_xabcd_patterns_optimized import detect_strict_xabcd_patterns

# Read the data
df = pd.read_csv('btcusdt_1d.csv')

# Capitalize column names
df.columns = [col.capitalize() for col in df.columns]

# Convert time column to datetime
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

print(f"Data shape: {df.shape[0]} rows")

# Detect extremum points
start = time.time()
extremum_points = detect_extremum_points(df)
extremum_time = time.time() - start

print(f"\nExtremum detection: {extremum_time:.3f} seconds")
print(f"Found {len(extremum_points)} extremum points")

# Time strict pattern detection
start = time.time()
strict_patterns = detect_strict_xabcd_patterns(
    extremum_points,
    df,
    log_details=True,
    max_patterns=10
)
pattern_time = time.time() - start

print(f"\nStrict pattern detection: {pattern_time:.3f} seconds")
print(f"Found {len(strict_patterns)} strict patterns")

print(f"\n=== Total Time: {extremum_time + pattern_time:.3f} seconds ===")
print("\nFor 934 rows, this should take < 1 second total")