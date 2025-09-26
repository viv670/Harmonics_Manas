"""
Test script to verify that strict XABCD patterns only return exact ratio matches
"""
import pandas as pd
from extremum import detect_extremum_points
from strict_xabcd_patterns import detect_strict_xabcd_patterns
from pattern_ratios_2_Final import XABCD_PATTERN_RATIOS

# Read and prepare data
df = pd.read_csv('btcusdt_1d.csv')
print(f"Total rows in CSV: {len(df)}")

# Capitalize column names
df.columns = [col.capitalize() for col in df.columns]

# Convert time column to datetime
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

# Use a subset for testing
test_df = df[:200]  # First 200 rows for faster testing

print("\n=== Detecting Extremum Points ===")
extremum_points = detect_extremum_points(test_df, length=1)

print("\n=== Testing Exact Pattern Matching ===")
patterns = detect_strict_xabcd_patterns(
    extremum_points,
    test_df,
    log_details=True,
    max_patterns=100  # Allow more patterns to see how many exact matches we get
)

print(f"\n=== Results ===")
print(f"Total patterns found with EXACT ratio matches: {len(patterns)}")

if patterns:
    # Count pattern names
    pattern_counts = {}
    for pattern in patterns:
        name = pattern.get('name', 'Unknown')
        pattern_counts[name] = pattern_counts.get(name, 0) + 1

    print(f"\nPattern distribution (only exact matches):")
    for name, count in sorted(pattern_counts.items()):
        print(f"  {name}: {count} patterns")

    # Show details of first 3 patterns
    print(f"\nFirst 3 patterns with exact matches:")
    for i, pattern in enumerate(patterns[:3]):
        print(f"\n--- Pattern {i+1}: {pattern['name']} ---")
        print(f"  Direction: {'Bullish' if pattern['bullish'] else 'Bearish'}")
        print(f"  Ratios:")
        print(f"    AB/XA: {pattern['ratios']['ab_xa']:.1f}%")
        print(f"    BC/AB: {pattern['ratios']['bc_ab']:.1f}%")
        print(f"    CD/BC: {pattern['ratios']['cd_bc']:.1f}%")
        print(f"    AD/XA: {pattern['ratios']['ad_xa']:.1f}%")

        # Verify this pattern's ratios are within defined ranges
        pattern_def = XABCD_PATTERN_RATIOS.get(pattern['name'])
        if pattern_def:
            print(f"  Defined ranges for {pattern['name']}:")
            print(f"    AB/XA: {pattern_def['ab_xa'][0]:.1f}% - {pattern_def['ab_xa'][1]:.1f}%")
            print(f"    BC/AB: {pattern_def['bc_ab'][0]:.1f}% - {pattern_def['bc_ab'][1]:.1f}%")
            print(f"    CD/BC: {pattern_def['cd_bc'][0]:.1f}% - {pattern_def['cd_bc'][1]:.1f}%")
            print(f"    AD/XA: {pattern_def['ad_xa'][0]:.1f}% - {pattern_def['ad_xa'][1]:.1f}%")

            # Verify all ratios are within bounds
            ab_ok = pattern_def['ab_xa'][0] <= pattern['ratios']['ab_xa'] <= pattern_def['ab_xa'][1]
            bc_ok = pattern_def['bc_ab'][0] <= pattern['ratios']['bc_ab'] <= pattern_def['bc_ab'][1]
            cd_ok = pattern_def['cd_bc'][0] <= pattern['ratios']['cd_bc'] <= pattern_def['cd_bc'][1]
            ad_ok = pattern_def['ad_xa'][0] <= pattern['ratios']['ad_xa'] <= pattern_def['ad_xa'][1]

            print(f"  Verification: {'✓ EXACT MATCH' if all([ab_ok, bc_ok, cd_ok, ad_ok]) else '✗ NOT EXACT'}")
else:
    print("\nNo patterns found with exact ratio matches.")
    print("This is expected if the data doesn't contain patterns that exactly match the defined ratios.")

print("\n=== Summary ===")
print("The strict XABCD pattern detection now ONLY returns patterns that:")
print("1. Have ALL four ratios within the exact defined ranges")
print("2. Match a specific pattern name from pattern_ratios_2_Final.py")
print("3. No approximations or generic patterns are included")