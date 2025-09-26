"""
Performance test for pattern detection
"""

import pandas as pd
import time
from pattern_ratios_2_Final import HarmonicPatternAnalyzer

# Read the data
df = pd.read_csv('btcusdt_1d.csv')

# Capitalize column names
df.columns = [col.capitalize() for col in df.columns]

# Convert time column to datetime
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

print(f"Data shape: {df.shape[0]} rows, {df.shape[1]} columns")

# Initialize analyzer
analyzer = HarmonicPatternAnalyzer()

# Time the full pattern detection
start = time.time()
analyzer.detect_patterns(df)
elapsed = time.time() - start

print(f"\nPattern Detection Results:")
print(f"Time taken: {elapsed:.2f} seconds")
print(f"Extremum points found: {len(analyzer.extremum_points)}")
print(f"ABCD patterns: {len(analyzer.abcd_patterns)}")
print(f"XABCD patterns: {len(analyzer.xabcd_patterns)}")
print(f"Strict XABCD patterns: {len(analyzer.strict_xabcd_patterns)}")

# Test just strict pattern detection with timing
from strict_xabcd_patterns_optimized import detect_strict_xabcd_patterns

start = time.time()
strict_patterns = detect_strict_xabcd_patterns(
    analyzer.extremum_points,
    df,
    log_details=True,
    max_patterns=10
)
elapsed = time.time() - start

print(f"\nStrict pattern detection alone: {elapsed:.2f} seconds")
print(f"Found {len(strict_patterns)} strict patterns")

print("\n=== Expected Performance ===")
print("For 934 rows of data:")
print("- Total analysis should take < 1 second")
print("- Extremum detection: < 0.1 seconds")
print("- Pattern detection: < 0.5 seconds")
print("- GUI rendering: < 0.5 seconds")