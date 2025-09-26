"""
Test script to verify that strict XABCD patterns are getting specific names
"""
import pandas as pd
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

# Detect extremum points with small window for testing
print("\n=== Detecting Extremum Points ===")
extremum_points = detect_extremum_points(df[:100], length=1)  # Use first 100 rows for faster testing

# Test strict XABCD detection
print("\n=== Testing Strict XABCD Pattern Names ===")
patterns = detect_strict_xabcd_patterns(
    extremum_points,
    df[:100],
    log_details=True,
    max_patterns=10  # Limit to 10 patterns for testing
)

print(f"\n=== Pattern Names Found ===")
if patterns:
    # Count pattern names
    pattern_names = {}
    for pattern in patterns:
        name = pattern.get('name', 'Unknown')
        pattern_names[name] = pattern_names.get(name, 0) + 1

    # Print unique pattern names
    print(f"Found {len(patterns)} patterns with {len(pattern_names)} unique names:")
    for name, count in sorted(pattern_names.items()):
        print(f"  - {name}: {count} patterns")

    # Show first 3 patterns with their names and ratios
    print("\nFirst 3 patterns details:")
    for i, pattern in enumerate(patterns[:3]):
        print(f"\nPattern {i+1}:")
        print(f"  Name: {pattern.get('name', 'Unknown')}")
        if 'ratios' in pattern:
            print(f"  Ratios:")
            print(f"    AB/XA: {pattern['ratios']['ab_xa']:.1f}%")
            print(f"    BC/AB: {pattern['ratios']['bc_ab']:.1f}%")
            print(f"    CD/BC: {pattern['ratios']['cd_bc']:.1f}%")
            print(f"    AD/XA: {pattern['ratios']['ad_xa']:.1f}%")
else:
    print("No patterns found")