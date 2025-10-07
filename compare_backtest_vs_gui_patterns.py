"""
Compare Backtesting Pattern Detection vs GUI Formed Pattern Detection

This script runs both detection methods on the same data and compares:
1. Total formed patterns found
2. Pattern IDs and details
3. Patterns found by backtest but not GUI
4. Patterns found by GUI but not backtest
"""

import pandas as pd
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Import required modules
from optimized_walk_forward_backtester import OptimizedWalkForwardBacktester
from formed_xabcd import detect_xabcd_patterns
from extremum import detect_extremum_points


def load_test_data(symbol: str = 'HYPEUSDT', timeframe: str = '4h') -> pd.DataFrame:
    """Load test data from CSV file"""
    csv_path = Path('data') / f'{symbol.lower()}_{timeframe}.csv'

    if not csv_path.exists():
        print(f"❌ File not found: {csv_path}")
        sys.exit(1)

    # Load data
    df = pd.read_csv(csv_path)

    # Normalize column names to Title Case
    df.columns = df.columns.str.capitalize()

    # Convert Date/Time column to datetime
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
    elif 'Time' in df.columns:
        df['Time'] = pd.to_datetime(df['Time'])
        df.set_index('Time', inplace=True)

    return df


def run_backtesting(data: pd.DataFrame, start_date: str, end_date: str) -> Dict:
    """Run backtesting and return all tracked patterns"""
    print("\n" + "="*80)
    print("🔄 RUNNING BACKTESTING...")
    print("="*80)

    # Filter data by date range
    start_pd = pd.Timestamp(start_date)
    end_pd = pd.Timestamp(end_date)
    mask = (data.index >= start_pd) & (data.index <= end_pd)
    test_data = data[mask].copy()

    print(f"Date range: {start_date} to {end_date}")
    print(f"Total bars: {len(test_data)}")

    # Initialize backtester
    backtester = OptimizedWalkForwardBacktester(
        data=test_data,
        initial_capital=10000,
        position_size=1000,
        lookback_window=300,
        future_buffer=50,
        min_pattern_score=0.0,
        max_open_trades=5,
        detection_interval=1,  # Detect every bar for 100% coverage
        extremum_length=1
    )

    # Run backtest
    print("\nRunning backtest (this may take a few minutes)...")
    stats = backtester.run_backtest()

    # Get all tracked patterns
    tracker = backtester.pattern_tracker
    all_patterns = tracker.tracked_patterns

    print(f"\n✅ Backtesting completed!")
    print(f"Total patterns tracked: {len(all_patterns)}")

    # Count by status
    status_counts = {}
    for pattern_id, tracked in all_patterns.items():
        status = tracked.status
        status_counts[status] = status_counts.get(status, 0) + 1

    print("\nPatterns by status:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")

    return {
        'tracker': tracker,
        'patterns': all_patterns,
        'backtester': backtester
    }


def run_gui_detection(data: pd.DataFrame, extremum_length: int = 1) -> Dict:
    """Run GUI formed pattern detection on complete data"""
    print("\n" + "="*80)
    print("🎨 RUNNING GUI FORMED PATTERN DETECTION...")
    print("="*80)

    # Find extremum points
    print(f"Finding extremum points (length={extremum_length})...")
    extremum_points = detect_extremum_points(data, length=extremum_length)
    print(f"Found {len(extremum_points)} extremum points")

    # Prepare data for GUI detection
    data_with_date = data.reset_index()
    if 'time' in data_with_date.columns:
        data_with_date.rename(columns={'time': 'Date'}, inplace=True)
    elif data_with_date.index.name == 'time':
        data_with_date['Date'] = data_with_date.index

    # Convert extremums to indexed format
    extremums_with_idx = []
    for ext in extremum_points:
        timestamp, price, is_high, bar_index = ext
        extremums_with_idx.append((bar_index, price, is_high, bar_index))

    # Detect formed patterns
    print(f"\nDetecting formed XABCD patterns...")
    formed_xabcd = detect_xabcd_patterns(
        extremums_with_idx,
        df=data_with_date,
        max_patterns=None,  # No limit
        validate_d_crossing=False
    )

    # Filter to only truly formed patterns (with D point)
    formed_patterns = []
    for pattern in formed_xabcd:
        if 'D' in pattern.get('points', {}):
            formed_patterns.append(pattern)

    print(f"\n✅ GUI detection completed!")
    print(f"Total formed XABCD patterns: {len(formed_patterns)}")

    return {
        'patterns': formed_patterns,
        'extremums': extremum_points
    }


def generate_pattern_id_from_gui(pattern: Dict) -> str:
    """Generate pattern ID compatible with backtester format"""
    pattern_type = pattern.get('pattern_type', 'XABCD')
    pattern_name = pattern.get('name', 'unknown').replace('_formed', '')

    points = pattern.get('points', {})
    point_indices = []

    for point_name in ['X', 'A', 'B', 'C']:
        if point_name in points:
            point_data = points[point_name]
            if isinstance(point_data, (list, tuple)):
                idx = point_data[0]
            elif isinstance(point_data, dict):
                idx = point_data.get('index', point_data.get('bar', 0))
            else:
                idx = point_data
            point_indices.append(f"{point_name}:{idx}")

    point_str = "_".join(point_indices)
    return f"{pattern_type}_{point_str}_{pattern_name}"


def compare_results(backtest_result: Dict, gui_result: Dict) -> Dict:
    """Compare backtesting vs GUI detection results"""
    print("\n" + "="*80)
    print("📊 COMPARISON ANALYSIS")
    print("="*80)

    # Get pattern IDs from backtesting (only 'success' status = formed patterns)
    backtest_formed = {}
    for pattern_id, tracked in backtest_result['patterns'].items():
        if tracked.status == 'success':  # Successfully formed patterns
            backtest_formed[pattern_id] = tracked

    # Get pattern IDs from GUI
    gui_formed = {}
    for pattern in gui_result['patterns']:
        pattern_id = generate_pattern_id_from_gui(pattern)
        gui_formed[pattern_id] = pattern

    # Find patterns in both, only backtest, only GUI
    backtest_ids = set(backtest_formed.keys())
    gui_ids = set(gui_formed.keys())

    in_both = backtest_ids & gui_ids
    only_backtest = backtest_ids - gui_ids
    only_gui = gui_ids - backtest_ids

    # Print summary
    print(f"\n{'='*80}")
    print(f"SUMMARY:")
    print(f"{'='*80}")
    print(f"Backtesting formed patterns (status='success'): {len(backtest_formed)}")
    print(f"GUI formed patterns: {len(gui_formed)}")
    print(f"\nFound in BOTH: {len(in_both)} ({len(in_both)/max(len(gui_formed), 1)*100:.1f}% of GUI patterns)")
    print(f"Only in BACKTESTING: {len(only_backtest)}")
    print(f"Only in GUI: {len(only_gui)}")

    # Detailed analysis
    if only_backtest:
        print(f"\n{'='*80}")
        print(f"⚠️  PATTERNS ONLY IN BACKTESTING (NOT IN GUI): {len(only_backtest)}")
        print(f"{'='*80}")
        for i, pattern_id in enumerate(list(only_backtest)[:10], 1):  # Show first 10
            tracked = backtest_formed[pattern_id]
            print(f"{i}. {tracked.subtype} ({tracked.pattern_type})")
            print(f"   ID: {pattern_id[:80]}...")
            print(f"   Points: A={tracked.a_point}, B={tracked.b_point}, C={tracked.c_point}")
        if len(only_backtest) > 10:
            print(f"   ... and {len(only_backtest) - 10} more")

    if only_gui:
        print(f"\n{'='*80}")
        print(f"⚠️  PATTERNS ONLY IN GUI (NOT IN BACKTESTING): {len(only_gui)}")
        print(f"{'='*80}")
        for i, pattern_id in enumerate(list(only_gui)[:10], 1):  # Show first 10
            pattern = gui_formed[pattern_id]
            points = pattern.get('points', {})
            print(f"{i}. {pattern.get('name', 'Unknown')} ({pattern.get('pattern_type', 'XABCD')})")
            print(f"   ID: {pattern_id[:80]}...")
            if 'A' in points and 'B' in points and 'C' in points:
                print(f"   Points: A={points['A']}, B={points['B']}, C={points['C']}")
        if len(only_gui) > 10:
            print(f"   ... and {len(only_gui) - 10} more")

    # Check for status mismatches
    print(f"\n{'='*80}")
    print(f"BACKTESTING PATTERN STATUS BREAKDOWN:")
    print(f"{'='*80}")
    status_counts = {}
    for pattern_id, tracked in backtest_result['patterns'].items():
        status = tracked.status
        pattern_type = tracked.pattern_type
        key = f"{pattern_type} - {status}"
        status_counts[key] = status_counts.get(key, 0) + 1

    for key, count in sorted(status_counts.items()):
        print(f"  {key}: {count}")

    return {
        'backtest_count': len(backtest_formed),
        'gui_count': len(gui_formed),
        'in_both': len(in_both),
        'only_backtest': len(only_backtest),
        'only_gui': len(only_gui),
        'match_rate': len(in_both) / max(len(gui_formed), 1) * 100
    }


def main():
    """Main execution"""
    print("="*80)
    print("BACKTESTING vs GUI PATTERN DETECTION COMPARISON")
    print("="*80)

    # Configuration
    SYMBOL = 'HYPEUSDT'
    TIMEFRAME = '4h'
    START_DATE = '2025-08-01'  # Test on recent 2 months data
    END_DATE = '2025-10-05'
    EXTREMUM_LENGTH = 1

    print(f"\nConfiguration:")
    print(f"  Symbol: {SYMBOL}")
    print(f"  Timeframe: {TIMEFRAME}")
    print(f"  Date range: {START_DATE} to {END_DATE}")
    print(f"  Extremum length: {EXTREMUM_LENGTH}")

    # Load data
    print(f"\nLoading data...")
    full_data = load_test_data(SYMBOL, TIMEFRAME)
    print(f"Loaded {len(full_data)} total bars")

    # Filter to test date range
    start_pd = pd.Timestamp(START_DATE)
    end_pd = pd.Timestamp(END_DATE)
    mask = (full_data.index >= start_pd) & (full_data.index <= end_pd)
    test_data = full_data[mask].copy()

    # Run backtesting
    backtest_result = run_backtesting(full_data, START_DATE, END_DATE)

    # Run GUI detection on same data
    gui_result = run_gui_detection(test_data, EXTREMUM_LENGTH)

    # Compare results
    comparison = compare_results(backtest_result, gui_result)

    # Final verdict
    print("\n" + "="*80)
    print("🎯 FINAL VERDICT")
    print("="*80)

    match_rate = comparison['match_rate']

    if match_rate >= 95:
        print(f"✅ EXCELLENT: {match_rate:.1f}% match rate")
        print("   Backtesting is finding almost all GUI patterns!")
    elif match_rate >= 80:
        print(f"✅ GOOD: {match_rate:.1f}% match rate")
        print("   Backtesting is finding most GUI patterns")
    elif match_rate >= 50:
        print(f"⚠️  MODERATE: {match_rate:.1f}% match rate")
        print("   Backtesting is missing some GUI patterns")
    else:
        print(f"❌ POOR: {match_rate:.1f}% match rate")
        print("   Backtesting is missing many GUI patterns - investigation needed!")

    if comparison['only_backtest'] > 0:
        print(f"\nℹ️  Backtesting found {comparison['only_backtest']} extra patterns")
        print("   These patterns formed DURING the backtest but may have been dismissed/failed later")

    if comparison['only_gui'] > 0:
        print(f"\n⚠️  GUI found {comparison['only_gui']} patterns NOT in backtesting 'success'")
        print("   These patterns might be in backtesting but with different status:")
        print("   - Check 'pending', 'invalid_prz', or 'dismissed' categories")
        print("   - Pattern might have been detected but not marked as 'success'")


if __name__ == '__main__':
    main()
