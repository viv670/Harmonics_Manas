"""
Test extremum=1 vs extremum=2 for ENAUSDT 1d data
Verify why extremum=1 gives 3 patterns but extremum=2 gives 4 patterns
"""

import pandas as pd
from extremum import detect_extremum_points
from formed_abcd import detect_strict_abcd_patterns

# Load ENAUSDT data
print("Loading ENAUSDT 1d data...")
df = pd.read_csv('enausdt_1d.csv')

# Normalize column names
df.columns = [col.capitalize() if col.lower() in ['time', 'open', 'high', 'low', 'close', 'volume'] else col for col in df.columns]
if 'Time' in df.columns:
    df['Date'] = pd.to_datetime(df['Time'])
elif 'Date' not in df.columns:
    df['Date'] = pd.to_datetime(df.index)

print(f"Loaded {len(df)} candles")
print(f"Date range: {df['Date'].min()} to {df['Date'].max()}\n")

# Test with extremum length = 1
print("="*70)
print("TEST 1: EXTREMUM LENGTH = 1")
print("="*70)
extremums_1 = detect_extremum_points(df, length=1)
print(f"Total extremum points: {len(extremums_1)}")
print(f"  Highs: {sum(1 for ep in extremums_1 if ep[2])}")
print(f"  Lows: {sum(1 for ep in extremums_1 if not ep[2])}")

print("\nDetecting FORMED ABCD patterns with extremum length=1...")
patterns_1 = detect_strict_abcd_patterns(extremums_1, df, log_details=False, max_patterns=200, max_search_window=30)
print(f"\n✓ FOUND {len(patterns_1)} FORMED ABCD patterns with extremum=1")

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
print(f"Total extremum points: {len(extremums_2)}")
print(f"  Highs: {sum(1 for ep in extremums_2 if ep[2])}")
print(f"  Lows: {sum(1 for ep in extremums_2 if not ep[2])}")

print("\nDetecting FORMED ABCD patterns with extremum length=2...")
patterns_2 = detect_strict_abcd_patterns(extremums_2, df, log_details=False, max_patterns=200, max_search_window=30)
print(f"\n✓ FOUND {len(patterns_2)} FORMED ABCD patterns with extremum=2")

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
print("ANALYSIS: WHY DOES EXTREMUM=1 PRODUCE FEWER PATTERNS?")
print("="*70)
print(f"Extremum length=1: {len(extremums_1)} points → {len(patterns_1)} ABCD patterns")
print(f"Extremum length=2: {len(extremums_2)} points → {len(patterns_2)} ABCD patterns")
print(f"\nDifference: extremum=1 has {len(patterns_1) - len(patterns_2)} {'fewer' if len(patterns_1) < len(patterns_2) else 'more'} patterns")

if len(patterns_1) < len(patterns_2):
    print("\n⚠️  UNEXPECTED BEHAVIOR CONFIRMED!")
    print("   Extremum=1 should give MORE patterns, not fewer.")
    print("   Let's investigate which pattern exists in extremum=2 but not in extremum=1...")

    # Find patterns in 2 that aren't in 1
    patterns_2_indices = set()
    for p in patterns_2:
        a = p['points']['A']['index']
        b = p['points']['B']['index']
        c = p['points']['C']['index']
        d = p['points']['D']['index']
        patterns_2_indices.add((a, b, c, d))

    patterns_1_indices = set()
    for p in patterns_1:
        a = p['points']['A']['index']
        b = p['points']['B']['index']
        c = p['points']['C']['index']
        d = p['points']['D']['index']
        patterns_1_indices.add((a, b, c, d))

    missing_in_1 = patterns_2_indices - patterns_1_indices
    print(f"\n   Patterns in extremum=2 but NOT in extremum=1:")
    for indices in missing_in_1:
        print(f"     A:{indices[0]} B:{indices[1]} C:{indices[2]} D:{indices[3]}")
        # Check if these bars are detected as extremums in both cases
        for bar in indices:
            in_ext1 = any(ep[3] == bar for ep in extremums_1)
            in_ext2 = any(ep[3] == bar for ep in extremums_2)
            print(f"       Bar {bar}: in extremum=1? {in_ext1}, in extremum=2? {in_ext2}")
else:
    print("\n✓ EXPECTED BEHAVIOR")
    print("   Extremum=1 gives more patterns as expected.")
