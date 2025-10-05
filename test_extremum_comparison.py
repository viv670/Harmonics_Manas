"""
Test script to compare extremum detection with length=1 vs length=2
and identify why extremum=1 produces fewer ABCD patterns
"""

import pandas as pd
from extremum import detect_extremum_points
from formed_abcd import detect_strict_abcd_patterns

# Load the data
print("Loading BTC data...")
df = pd.read_csv('btcusdt_1d.csv')
if 'Date' in df.columns:
    df['Date'] = pd.to_datetime(df['Date'])
else:
    df.index = pd.to_datetime(df.index)
    df.reset_index(inplace=True)
    df.columns = ['Date'] + list(df.columns[1:])

print(f"Loaded {len(df)} candles\n")

# Test with extremum length = 1
print("="*70)
print("TEST 1: EXTREMUM LENGTH = 1")
print("="*70)
extremums_1 = detect_extremum_points(df, length=1)
print(f"\nTotal extremum points: {len(extremums_1)}")
print(f"  Highs: {sum(1 for ep in extremums_1 if ep[2])}")
print(f"  Lows: {sum(1 for ep in extremums_1 if not ep[2])}")

# Check if bars 233, 249, 252, 258 are detected
target_bars = [233, 249, 252, 258]
detected_bars_1 = []
for bar in target_bars:
    found = any(ep[3] == bar for ep in extremums_1)
    detected_bars_1.append(found)
    status = "✓" if found else "✗"
    if found:
        ep = [ep for ep in extremums_1 if ep[3] == bar][0]
        point_type = "HIGH" if ep[2] else "LOW"
        print(f"  {status} Bar {bar}: {point_type} at price {ep[1]:.2f}")
    else:
        print(f"  {status} Bar {bar}: NOT DETECTED")

print("\nDetecting ABCD patterns with extremum length=1...")
patterns_1 = detect_strict_abcd_patterns(extremums_1, df, log_details=False, max_patterns=50, max_search_window=20)
print(f"Found {len(patterns_1)} ABCD patterns")

# Show the patterns
if patterns_1:
    print("\nPatterns found:")
    for i, p in enumerate(patterns_1, 1):
        a_idx = p['points']['A']['index']
        b_idx = p['points']['B']['index']
        c_idx = p['points']['C']['index']
        d_idx = p['points']['D']['index']
        print(f"  {i}. {p['name']} | A:{a_idx} B:{b_idx} C:{c_idx} D:{d_idx}")

# Test with extremum length = 2
print("\n" + "="*70)
print("TEST 2: EXTREMUM LENGTH = 2")
print("="*70)
extremums_2 = detect_extremum_points(df, length=2)
print(f"\nTotal extremum points: {len(extremums_2)}")
print(f"  Highs: {sum(1 for ep in extremums_2 if ep[2])}")
print(f"  Lows: {sum(1 for ep in extremums_2 if not ep[2])}")

# Check if bars 233, 249, 252, 258 are detected
detected_bars_2 = []
for bar in target_bars:
    found = any(ep[3] == bar for ep in extremums_2)
    detected_bars_2.append(found)
    status = "✓" if found else "✗"
    if found:
        ep = [ep for ep in extremums_2 if ep[3] == bar][0]
        point_type = "HIGH" if ep[2] else "LOW"
        print(f"  {status} Bar {bar}: {point_type} at price {ep[1]:.2f}")
    else:
        print(f"  {status} Bar {bar}: NOT DETECTED")

print("\nDetecting ABCD patterns with extremum length=2...")
patterns_2 = detect_strict_abcd_patterns(extremums_2, df, log_details=False, max_patterns=50, max_search_window=20)
print(f"Found {len(patterns_2)} ABCD patterns")

# Show the patterns
if patterns_2:
    print("\nPatterns found:")
    for i, p in enumerate(patterns_2, 1):
        a_idx = p['points']['A']['index']
        b_idx = p['points']['B']['index']
        c_idx = p['points']['C']['index']
        d_idx = p['points']['D']['index']
        print(f"  {i}. {p['name']} | A:{a_idx} B:{b_idx} C:{c_idx} D:{d_idx}")

# Analysis
print("\n" + "="*70)
print("COMPARISON ANALYSIS")
print("="*70)
print(f"Extremum length=1: {len(extremums_1)} points → {len(patterns_1)} ABCD patterns")
print(f"Extremum length=2: {len(extremums_2)} points → {len(patterns_2)} ABCD patterns")
print(f"\nTarget bars (233, 249, 252, 258) detection:")
print(f"  Length=1: {detected_bars_1}")
print(f"  Length=2: {detected_bars_2}")

# Check if the issue is with extremum detection or pattern validation
if all(detected_bars_2) and not all(detected_bars_1):
    print("\n⚠️  ISSUE: Some target bars are detected with length=2 but NOT with length=1")
    print("   This suggests extremum detection is too strict with length=1")
elif all(detected_bars_1) and all(detected_bars_2):
    print("\n⚠️  ISSUE: All target bars detected in both cases")
    print("   The problem must be in pattern validation or matching")
else:
    print("\n⚠️  ISSUE: Some bars missing in both cases")
    print("   Need to investigate why these bars are not detected as extremums")

# Show extremum detection logic explanation
print("\n" + "="*70)
print("EXTREMUM DETECTION LOGIC")
print("="*70)
print("The 'length' parameter defines the lookback/forward window:")
print(f"  length=1: A point is high/low if it's >= or <= to 1 bar on each side")
print(f"  length=2: A point is high/low if it's >= or <= to 2 bars on each side")
print("\nWith length=1: MORE sensitive → MORE extremum points")
print("With length=2: LESS sensitive → FEWER extremum points")
print("\nExpected: extremum=1 should give MORE patterns, not fewer!")
