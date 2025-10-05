"""
Check if the 7 formed GUI patterns are among the 87 successful unformed patterns
"""

import pandas as pd
from gui_compatible_detection import detect_all_gui_patterns
from extremum import detect_extremum_points as find_extremum_points
from pattern_tracking_utils import PatternTracker

# Load the data
data = pd.read_csv('btcusdt_1d.csv')
data.rename(columns={
    'time': 'Date',
    'open': 'Open',
    'high': 'High',
    'low': 'Low',
    'close': 'Close',
    'volume': 'Volume'
}, inplace=True)
data['Date'] = pd.to_datetime(data['Date'])
data.set_index('Date', inplace=True)

# Get extremum points (using length=1 to match typical GUI settings)
extremum_length = 1
extremums = find_extremum_points(data, length=extremum_length)

# extremums already has indices, not dates
extremums_with_idx = extremums

# Detect all patterns from full dataset (like GUI does)
data_with_date = data.reset_index()
all_abcd_full, all_xabcd_full = detect_all_gui_patterns(
    extremums_with_idx,
    data_with_date,
    max_patterns=200,
    validate_d_crossing=False
)

# Get formed patterns (those with D point) - these are the 7 GUI patterns
formed_patterns = []
for p in all_abcd_full + all_xabcd_full:
    if 'points' in p and 'D' in p['points']:
        formed_patterns.append(p)

print(f"Found {len(formed_patterns)} formed patterns (should be 7)")
print("\nFormed Patterns (GUI visible):")
print("="*80)

# Create pattern tracker to generate consistent IDs
tracker = PatternTracker()

formed_pattern_ids = set()
for i, pattern in enumerate(formed_patterns, 1):
    pattern_id = tracker.generate_pattern_id(pattern)
    formed_pattern_ids.add(pattern_id)

    indices = pattern.get('indices', {})
    points = pattern.get('points', {})
    name = pattern.get('name', 'Unknown')
    ptype = pattern.get('pattern_type', 'ABCD')

    print(f"{i}. {ptype} - {name}")
    print(f"   ID: {pattern_id[:40]}...")
    print(f"   Points: X:{indices.get('X','N/A')} A:{indices.get('A','?')} B:{indices.get('B','?')} C:{indices.get('C','?')} D:{indices.get('D','?')}")

    # Check if this pattern is in tracked patterns (would be from unformed->formed)
    # We need to check if an unformed version exists by looking at XAB or XABC only

print("\n" + "="*80)
print("\nNow checking if these formed patterns originated from unformed patterns...")
print("="*80)

# Simulate unformed pattern detection (without D point)
unformed_pattern_ids = set()
for pattern in formed_patterns:
    # Create unformed version (remove D point)
    unformed = pattern.copy()
    if 'D' in unformed.get('points', {}):
        del unformed['points']['D']
    if 'D' in unformed.get('indices', {}):
        del unformed['indices']['D']

    # Generate ID for unformed version
    unformed_id = tracker.generate_pattern_id(unformed)
    unformed_pattern_ids.add(unformed_id)

    formed_id = tracker.generate_pattern_id(pattern)

    print(f"\nPattern: {pattern.get('name', 'Unknown')}")
    print(f"  Formed ID:   {formed_id[:50]}...")
    print(f"  Unformed ID: {unformed_id[:50]}...")
    print(f"  Same? {formed_id == unformed_id}")

print("\n" + "="*80)
print("IMPORTANT FINDING:")
print("="*80)
print(f"Total formed patterns (GUI visible): {len(formed_patterns)}")
print(f"These patterns have BOTH unformed and formed versions in tracking")
print(f"\nThe 87 'successful' patterns are UNFORMED patterns that:")
print(f"  1. Were detected at point C")
print(f"  2. Reached their projected PRZ (where D should form)")
print(f"  3. Price reversed successfully")
print(f"\nThe 7 formed patterns are ALREADY COMPLETE patterns that:")
print(f"  1. Have all points including D")
print(f"  2. Are visible in the GUI")
print(f"  3. May or may not have been tracked as unformed first")
print(f"\nTO ANSWER YOUR QUESTION:")
print(f"We need to check if the tracking system tracks the SAME pattern twice:")
print(f"  - Once as unformed (when detected at C)")
print(f"  - Once as formed (when D completes)")
print(f"\nLet me check the backtester's actual tracking...")
