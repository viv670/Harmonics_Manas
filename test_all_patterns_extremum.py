"""
Test all pattern types (formed/unformed ABCD/XABCD) with extremum=1 vs extremum=2
Verify that extremum=1 consistently gives more or equal patterns across all types
"""

import pandas as pd
from extremum import detect_extremum_points
from formed_abcd import detect_strict_abcd_patterns
from formed_xabcd import detect_xabcd_patterns
from unformed_abcd import detect_unformed_abcd_patterns
from unformed_xabcd import detect_strict_unformed_xabcd_patterns

# Load ENAUSDT data
print("Loading ENAUSDT 1d data...")
df = pd.read_csv('enausdt_1d.csv')
df.columns = [col.capitalize() if col.lower() in ['time', 'open', 'high', 'low', 'close', 'volume'] else col for col in df.columns]
if 'Time' in df.columns:
    df['Date'] = pd.to_datetime(df['Time'])
elif 'Date' not in df.columns:
    df['Date'] = pd.to_datetime(df.index)

print(f"Loaded {len(df)} candles\n")

# Test parameters matching GUI
max_patterns = 200
max_search_window = 30

results = []

for extremum_length in [1, 2]:
    print("="*70)
    print(f"TESTING WITH EXTREMUM LENGTH = {extremum_length}")
    print("="*70)

    # Detect extremums
    extremums = detect_extremum_points(df, length=extremum_length)
    print(f"Extremum points: {len(extremums)}")
    print(f"  Highs: {sum(1 for ep in extremums if ep[2])}")
    print(f"  Lows: {sum(1 for ep in extremums if not ep[2])}")

    # Test all pattern types
    print("\nDetecting patterns...")

    # 1. Formed ABCD
    formed_abcd = detect_strict_abcd_patterns(
        extremums, df, log_details=False,
        max_patterns=max_patterns, max_search_window=max_search_window
    )
    print(f"  Formed ABCD: {len(formed_abcd)} patterns")

    # 2. Formed XABCD
    formed_xabcd = detect_xabcd_patterns(
        extremums, df, log_details=False
    )
    print(f"  Formed XABCD: {len(formed_xabcd)} patterns")

    # 3. Unformed ABCD
    unformed_abcd = detect_unformed_abcd_patterns(
        extremums, df, log_details=False, max_search_window=max_search_window
    )
    print(f"  Unformed ABCD: {len(unformed_abcd)} patterns")

    # 4. Unformed XABCD
    unformed_xabcd = detect_strict_unformed_xabcd_patterns(
        extremums, df, log_details=False,
        max_patterns=max_patterns, max_search_window=max_search_window
    )
    print(f"  Unformed XABCD: {len(unformed_xabcd)} patterns")

    results.append({
        'extremum': extremum_length,
        'extremum_points': len(extremums),
        'formed_abcd': len(formed_abcd),
        'formed_xabcd': len(formed_xabcd),
        'unformed_abcd': len(unformed_abcd),
        'unformed_xabcd': len(unformed_xabcd),
        'total': len(formed_abcd) + len(formed_xabcd) + len(unformed_abcd) + len(unformed_xabcd)
    })

    print()

# Summary comparison
print("="*70)
print("SUMMARY COMPARISON")
print("="*70)
print(f"{'Metric':<20} {'Extremum=1':<15} {'Extremum=2':<15} {'Status':<20}")
print("-"*70)

r1, r2 = results[0], results[1]

# Check extremum points
print(f"{'Extremum Points':<20} {r1['extremum_points']:<15} {r2['extremum_points']:<15} "
      f"{'✓ More' if r1['extremum_points'] > r2['extremum_points'] else '✗ Less or Equal'}")

# Check each pattern type
for ptype in ['formed_abcd', 'formed_xabcd', 'unformed_abcd', 'unformed_xabcd']:
    name = ptype.replace('_', ' ').title()
    status = "✓ More/Equal" if r1[ptype] >= r2[ptype] else "✗ LESS"
    print(f"{name:<20} {r1[ptype]:<15} {r2[ptype]:<15} {status}")

# Total patterns
status = "✓ More/Equal" if r1['total'] >= r2['total'] else "✗ LESS"
print(f"{'Total Patterns':<20} {r1['total']:<15} {r2['total']:<15} {status}")

print("\n" + "="*70)
if all([
    r1['extremum_points'] > r2['extremum_points'],
    r1['formed_abcd'] >= r2['formed_abcd'],
    r1['formed_xabcd'] >= r2['formed_xabcd'],
    r1['unformed_abcd'] >= r2['unformed_abcd'],
    r1['unformed_xabcd'] >= r2['unformed_xabcd']
]):
    print("✓✓✓ ALL TESTS PASSED ✓✓✓")
    print("Extremum=1 consistently produces more or equal patterns across all types!")
else:
    print("✗✗✗ SOME TESTS FAILED ✗✗✗")
    print("There are inconsistencies - some pattern types produce fewer patterns with extremum=1")
print("="*70)
