"""
Compare ABCD points between GUI formed patterns and backtested successful patterns
"""

import pandas as pd
import sys

# Run a simple backtest to get the tracked patterns
from optimized_walk_forward_backtester import OptimizedWalkForwardBacktester

# Load data
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

print("Running backtest to get tracked patterns...")
print("="*80)

# Run backtest with same settings as GUI
backtester = OptimizedWalkForwardBacktester(
    data=data,
    initial_capital=10000,
    position_size=0.02,
    lookback_window=10000,
    future_buffer=5,
    min_pattern_score=0.5,
    max_open_trades=5,
    detection_interval=1,
    extremum_length=1
)

# Define simple progress callback
def progress_callback(value):
    if value % 10 == 0:
        print(f"Progress: {value}%")

# Run backtest
stats = backtester.run_backtest(progress_callback=progress_callback)

print("\n" + "="*80)
print("BACKTEST COMPLETED")
print("="*80)

# Get the tracked patterns from the pattern tracker
tracker = backtester.pattern_tracker
tracked_patterns = tracker.tracked_patterns

# Filter successful patterns only
successful_patterns = {
    pid: p for pid, p in tracked_patterns.items()
    if p.status == 'success'
}

print(f"\nTotal tracked patterns: {len(tracked_patterns)}")
print(f"Successful patterns: {len(successful_patterns)}")

# Extract ABCD points from successful patterns
print("\n" + "="*80)
print("SUCCESSFUL PATTERNS (from backtest tracking):")
print("="*80)

successful_abcd_points = []
for i, (pid, pattern) in enumerate(successful_patterns.items(), 1):
    # Get points
    a_idx, a_price = pattern.a_point
    b_idx, b_price = pattern.b_point
    c_idx, c_price = pattern.c_point

    # D point from actual completion
    if pattern.d_point:
        d_idx, d_price = pattern.d_point
    else:
        d_idx = pattern.actual_d_bar if pattern.actual_d_bar else None
        d_price = pattern.actual_d_price if pattern.actual_d_price else None

    # Handle XABCD patterns
    x_idx, x_price = pattern.x_point if pattern.x_point else (None, None)

    abcd_key = (a_idx, b_idx, c_idx, d_idx)
    successful_abcd_points.append({
        'id': pid[:30],
        'type': pattern.pattern_type,
        'name': pattern.subtype,
        'x_idx': x_idx,
        'x_price': x_price,
        'a_idx': a_idx,
        'a_price': a_price,
        'b_idx': b_idx,
        'b_price': b_price,
        'c_idx': c_idx,
        'c_price': c_price,
        'd_idx': d_idx,
        'd_price': d_price,
        'abcd_key': abcd_key
    })

    if i <= 10:  # Show first 10
        print(f"{i}. {pattern.pattern_type} - {pattern.subtype[:30]}")
        if x_idx is not None:
            print(f"   X: idx={x_idx}, price={x_price:.2f}")
        print(f"   A: idx={a_idx}, price={a_price:.2f}")
        print(f"   B: idx={b_idx}, price={b_price:.2f}")
        print(f"   C: idx={c_idx}, price={c_price:.2f}")
        print(f"   D: idx={d_idx}, price={d_price:.2f if d_price else 'N/A'}")

if len(successful_patterns) > 10:
    print(f"   ... and {len(successful_patterns) - 10} more")

# Get GUI formed patterns from backtester (it already detected them)
print("\n" + "="*80)
print("FORMED PATTERNS (from GUI full-dataset detection):")
print("="*80)

# The backtester stores these counts
print(f"Total formed patterns: {backtester.total_formed_found}")
print(f"  ABCD: {backtester.formed_abcd_count}")
print(f"  XABCD: {backtester.formed_xabcd_count}")

# We need to re-detect to get the actual pattern objects
from gui_compatible_detection import detect_all_gui_patterns
from extremum import detect_extremum_points as find_extremum_points

extremums = find_extremum_points(data, length=1)
data_with_date = data.reset_index()

all_abcd_full, all_xabcd_full = detect_all_gui_patterns(
    extremums,
    data_with_date,
    max_patterns=200,
    validate_d_crossing=False
)

# Get formed patterns (with D point)
gui_formed_patterns = []
for p in all_abcd_full + all_xabcd_full:
    if 'points' in p and 'D' in p['points']:
        gui_formed_patterns.append(p)

print(f"\nRe-detected {len(gui_formed_patterns)} formed patterns")

# Extract ABCD points from GUI patterns
gui_abcd_points = []
for i, pattern in enumerate(gui_formed_patterns, 1):
    points = pattern.get('points', {})
    indices = pattern.get('indices', {})

    # Extract points
    x_point = points.get('X')
    a_point = points.get('A')
    b_point = points.get('B')
    c_point = points.get('C')
    d_point = points.get('D')

    if not a_point or not b_point or not c_point or not d_point:
        continue

    # Extract indices and prices
    x_idx = indices.get('X') if x_point else None
    x_price = x_point[1] if isinstance(x_point, (list, tuple)) and len(x_point) > 1 else None

    a_idx = indices.get('A')
    a_price = a_point[1] if isinstance(a_point, (list, tuple)) else a_point

    b_idx = indices.get('B')
    b_price = b_point[1] if isinstance(b_point, (list, tuple)) else b_point

    c_idx = indices.get('C')
    c_price = c_point[1] if isinstance(c_point, (list, tuple)) else c_point

    d_idx = indices.get('D')
    d_price = d_point[1] if isinstance(d_point, (list, tuple)) else d_point

    abcd_key = (a_idx, b_idx, c_idx, d_idx)
    gui_abcd_points.append({
        'type': pattern.get('pattern_type', 'ABCD'),
        'name': pattern.get('name', 'Unknown'),
        'x_idx': x_idx,
        'x_price': x_price,
        'a_idx': a_idx,
        'a_price': a_price,
        'b_idx': b_idx,
        'b_price': b_price,
        'c_idx': c_idx,
        'c_price': c_price,
        'd_idx': d_idx,
        'd_price': d_price,
        'abcd_key': abcd_key
    })

    print(f"{i}. {pattern.get('pattern_type', 'ABCD')} - {pattern.get('name', 'Unknown')[:30]}")
    if x_idx is not None:
        print(f"   X: idx={x_idx}, price={x_price:.2f}")
    print(f"   A: idx={a_idx}, price={a_price:.2f}")
    print(f"   B: idx={b_idx}, price={b_price:.2f}")
    print(f"   C: idx={c_idx}, price={c_price:.2f}")
    print(f"   D: idx={d_idx}, price={d_price:.2f}")

# Now compare ABCD keys
print("\n" + "="*80)
print("COMPARISON: Finding overlaps by ABCD point indices")
print("="*80)

# Create sets of ABCD keys
successful_keys = set(p['abcd_key'] for p in successful_abcd_points)
gui_keys = set(p['abcd_key'] for p in gui_abcd_points)

# Find overlaps
overlapping_keys = successful_keys.intersection(gui_keys)

print(f"\nSuccessful patterns (from tracking): {len(successful_keys)}")
print(f"GUI formed patterns: {len(gui_keys)}")
print(f"Overlapping patterns (same ABCD points): {len(overlapping_keys)}")

if overlapping_keys:
    print(f"\n✅ YES! {len(overlapping_keys)} of the {len(gui_keys)} GUI patterns are among the {len(successful_keys)} successful patterns!")
    print("\nOverlapping patterns:")
    for key in overlapping_keys:
        # Find the patterns
        gui_pattern = next(p for p in gui_abcd_points if p['abcd_key'] == key)
        successful_pattern = next(p for p in successful_abcd_points if p['abcd_key'] == key)

        print(f"\n  Pattern: {gui_pattern['name'][:40]}")
        print(f"    A={key[0]}, B={key[1]}, C={key[2]}, D={key[3]}")
        print(f"    GUI: {gui_pattern['type']}")
        print(f"    Backtest: {successful_pattern['type']} (tracked as {successful_pattern['name'][:30]})")
else:
    print(f"\n❌ NO OVERLAP! The 7 GUI patterns are NOT among the 87 successful patterns.")
    print("This means they are completely different patterns.")

# Show patterns unique to each set
gui_only = gui_keys - successful_keys
successful_only = successful_keys - gui_keys

if gui_only:
    print(f"\n{len(gui_only)} GUI patterns NOT in successful tracked patterns:")
    for key in list(gui_only)[:5]:
        gui_pattern = next(p for p in gui_abcd_points if p['abcd_key'] == key)
        print(f"  - {gui_pattern['name'][:40]}: A={key[0]}, B={key[1]}, C={key[2]}, D={key[3]}")
    if len(gui_only) > 5:
        print(f"  ... and {len(gui_only) - 5} more")

if successful_only:
    print(f"\n{len(successful_only)} Successful patterns NOT in GUI formed patterns:")
    for key in list(successful_only)[:5]:
        if key[3] is not None:  # Only show if D exists
            successful_pattern = next(p for p in successful_abcd_points if p['abcd_key'] == key)
            print(f"  - {successful_pattern['name'][:40]}: A={key[0]}, B={key[1]}, C={key[2]}, D={key[3]}")
    if len(successful_only) > 5:
        print(f"  ... and {len(successful_only) - 5} more")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
