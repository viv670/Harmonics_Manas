"""
Simple Pattern Count Verification

This script:
1. Loads a recent backtest Excel file
2. Counts all patterns by status
3. Runs GUI formed pattern detection on the same date range
4. Compares the counts
"""

import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Import detection modules
from formed_xabcd import detect_xabcd_patterns
from formed_abcd import detect_strict_abcd_patterns
from extremum import detect_extremum_points


def find_latest_backtest_file():
    """Find the most recent backtest Excel file"""
    backtest_dir = Path('backtest_results')

    if not backtest_dir.exists():
        print("❌ backtest_results directory not found!")
        return None

    # Find all backtest Excel files
    excel_files = list(backtest_dir.glob('backtest_results_*.xlsx'))

    if not excel_files:
        print("❌ No backtest Excel files found!")
        return None

    # Sort by modification time, get latest
    latest_file = max(excel_files, key=lambda p: p.stat().st_mtime)

    return latest_file


def load_backtest_patterns(excel_file):
    """Load and count patterns from backtest Excel file"""
    print(f"\n📊 Loading backtest results from:")
    print(f"   {excel_file.name}")

    try:
        # Read the Summary sheet
        summary_df = pd.read_excel(excel_file, sheet_name='Summary')

        # Extract key metrics
        metrics = {}
        for _, row in summary_df.iterrows():
            metric = row.iloc[0]
            value = row.iloc[1]
            metrics[metric] = value

        print(f"\n📈 Backtest Summary:")
        print(f"   Date range: {metrics.get('Backtest Date Range', 'N/A')}")
        print(f"   Total bars: {metrics.get('Total Bars Analyzed', 'N/A')}")

        # Read the Pattern Details sheet
        lifecycle_df = pd.read_excel(excel_file, sheet_name='Pattern Details')

        # Count patterns by status
        status_counts = {}
        if 'Status' in lifecycle_df.columns:
            status_counts = lifecycle_df['Status'].value_counts().to_dict()

        # Count by pattern type
        type_counts = {}
        if 'Pattern Type' in lifecycle_df.columns:
            type_counts = lifecycle_df['Pattern Type'].value_counts().to_dict()

        print(f"\n📊 Patterns by Status:")
        for status, count in sorted(status_counts.items()):
            print(f"   {status}: {count}")

        print(f"\n📊 Patterns by Type:")
        for ptype, count in sorted(type_counts.items()):
            print(f"   {ptype}: {count}")

        # Calculate total formed patterns
        # Formed = patterns that have D point (success + invalid_prz + in_zone)
        total_formed = (
            status_counts.get('success', 0) +
            status_counts.get('invalid_prz', 0) +
            status_counts.get('in_zone', 0)
        )

        return {
            'total_tracked': len(lifecycle_df),
            'status_counts': status_counts,
            'type_counts': type_counts,
            'total_formed': total_formed,
            'metrics': metrics,
            'lifecycle_df': lifecycle_df
        }

    except Exception as e:
        print(f"❌ Error loading backtest file: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_test_data_from_backtest(lifecycle_df):
    """Extract date range from backtest and load corresponding data"""

    # Try to get date range from the lifecycle data
    if 'First Seen Bar' in lifecycle_df.columns:
        # The data should have timestamps
        # For now, let's use a default file
        pass

    # Load HYPEUSDT 4h data (adjust as needed)
    csv_path = Path('data/hypeusdt_4h.csv')

    if not csv_path.exists():
        print(f"❌ Data file not found: {csv_path}")
        return None, None, None

    # Load and normalize columns
    df = pd.read_csv(csv_path)

    # Check original column names
    original_cols = df.columns.tolist()
    print(f"\n📁 Original CSV columns: {original_cols}")

    # Normalize to Title Case
    df.columns = [col.capitalize() for col in df.columns]

    # Set time index
    if 'Time' in df.columns:
        df['Time'] = pd.to_datetime(df['Time'])
        df.set_index('Time', inplace=True)
    elif 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)

    print(f"   Loaded {len(df)} bars")
    print(f"   Date range: {df.index[0]} to {df.index[-1]}")

    # For simplicity, use last 200 bars (covers ~1 month of 4h data)
    test_df = df.tail(200).copy()

    start_date = test_df.index[0]
    end_date = test_df.index[-1]

    print(f"\n🎯 Using date range for comparison:")
    print(f"   {start_date} to {end_date}")
    print(f"   Total bars: {len(test_df)}")

    return test_df, start_date, end_date


def run_gui_formed_detection(data, extremum_length=1):
    """Run GUI formed pattern detection"""
    print(f"\n🎨 Running GUI Formed Pattern Detection...")
    print(f"   Extremum length: {extremum_length}")

    # Detect extremum points
    extremum_points = detect_extremum_points(data, length=extremum_length)
    print(f"   Found {len(extremum_points)} extremum points")

    if len(extremum_points) < 4:
        print("   ⚠️ Not enough extremum points for pattern detection")
        return {'abcd': [], 'xabcd': []}

    # Convert extremums to indexed format
    extremums_indexed = []
    for ext in extremum_points:
        timestamp, price, is_high, bar_index = ext
        extremums_indexed.append((bar_index, price, is_high, bar_index))

    # Detect ABCD patterns
    abcd_patterns = []
    if len(extremums_indexed) >= 4:
        try:
            # Prepare data with Date column
            data_with_date = data.reset_index()
            if data.index.name == 'Time':
                data_with_date.rename(columns={'Time': 'Date'}, inplace=True)
            elif 'Date' not in data_with_date.columns and data.index.name:
                data_with_date['Date'] = data_with_date.index

            abcd_patterns = detect_strict_abcd_patterns(extremums_indexed, df=data_with_date)
            # Filter to only formed (with D point)
            abcd_patterns = [p for p in abcd_patterns if 'D' in p.get('points', {})]
        except Exception as e:
            print(f"   ⚠️ ABCD detection error: {e}")

    # Detect XABCD patterns
    xabcd_patterns = []
    if len(extremums_indexed) >= 5:
        try:
            # Prepare data with Date column for detection
            data_with_date = data.reset_index()
            if data.index.name == 'Time':
                data_with_date.rename(columns={'Time': 'Date'}, inplace=True)
            elif 'Date' not in data_with_date.columns and data.index.name:
                data_with_date['Date'] = data_with_date.index

            xabcd_patterns = detect_xabcd_patterns(
                extremums_indexed,
                df=data_with_date,
                max_patterns=None,
                validate_d_crossing=False
            )
            # Filter to only formed (with D point)
            xabcd_patterns = [p for p in xabcd_patterns if 'D' in p.get('points', {})]
        except Exception as e:
            print(f"   ⚠️ XABCD detection error: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n✅ GUI Detection Results:")
    print(f"   ABCD patterns (formed): {len(abcd_patterns)}")
    print(f"   XABCD patterns (formed): {len(xabcd_patterns)}")
    print(f"   TOTAL: {len(abcd_patterns) + len(xabcd_patterns)}")

    return {
        'abcd': abcd_patterns,
        'xabcd': xabcd_patterns,
        'total': len(abcd_patterns) + len(xabcd_patterns)
    }


def compare_counts(backtest_data, gui_data):
    """Compare backtest vs GUI pattern counts"""
    print(f"\n" + "="*80)
    print(f"📊 COMPARISON RESULTS")
    print(f"="*80)

    backtest_formed = backtest_data['total_formed']
    gui_formed = gui_data['total']

    print(f"\n🔢 Pattern Counts:")
    print(f"   Backtest (success + invalid_prz + in_zone): {backtest_formed}")
    print(f"   GUI (formed ABCD + XABCD): {gui_formed}")

    if backtest_formed == 0 and gui_formed == 0:
        print(f"\n⚠️  Both systems found 0 patterns")
        print(f"   This might indicate:")
        print(f"   - Date ranges don't overlap")
        print(f"   - Not enough data/extremums")
        print(f"   - Different detection parameters")
        return

    # Calculate difference
    diff = backtest_formed - gui_formed

    print(f"\n📈 Analysis:")

    if backtest_formed >= gui_formed * 0.95:
        print(f"   ✅ EXCELLENT: Backtest found {backtest_formed} vs GUI {gui_formed}")
        if diff > 0:
            print(f"   📌 Backtest found {diff} MORE patterns")
            print(f"      These patterns likely formed during backtest but later failed/dismissed")
        else:
            print(f"   📌 Counts match well!")
    elif backtest_formed >= gui_formed * 0.80:
        print(f"   ✅ GOOD: Backtest found {backtest_formed} vs GUI {gui_formed}")
        print(f"   📌 Missing ~{gui_formed - backtest_formed} patterns ({abs(diff/gui_formed*100):.1f}%)")
    elif backtest_formed >= gui_formed * 0.50:
        print(f"   ⚠️  MODERATE: Backtest found {backtest_formed} vs GUI {gui_formed}")
        print(f"   📌 Missing ~{gui_formed - backtest_formed} patterns ({abs(diff/gui_formed*100):.1f}%)")
        print(f"   ⚠️  Significant gap - investigation recommended")
    else:
        print(f"   ❌ POOR: Backtest found {backtest_formed} vs GUI {gui_formed}")
        print(f"   📌 Missing ~{gui_formed - backtest_formed} patterns ({abs(diff/gui_formed*100):.1f}%)")
        print(f"   ❌ Large gap - issue with backtest detection")

    # Additional insights
    print(f"\n💡 Additional Context:")
    print(f"   Backtest total tracked: {backtest_data['total_tracked']}")
    print(f"   Backtest status breakdown:")
    for status, count in sorted(backtest_data['status_counts'].items()):
        print(f"     - {status}: {count}")

    print(f"\n📝 Notes:")
    print(f"   • Backtest sees patterns as they form in real-time")
    print(f"   • GUI sees final state only")
    print(f"   • Backtest might have patterns that formed then failed")
    print(f"   • Different date ranges may cause count differences")


def main():
    print("="*80)
    print("BACKTEST vs GUI PATTERN COUNT VERIFICATION")
    print("="*80)

    # Find latest backtest file
    backtest_file = find_latest_backtest_file()

    if not backtest_file:
        print("\n❌ No backtest file found. Please run a backtest first.")
        return

    # Load backtest patterns
    backtest_data = load_backtest_patterns(backtest_file)

    if not backtest_data:
        return

    # Load data and run GUI detection
    data, start_date, end_date = load_test_data_from_backtest(backtest_data['lifecycle_df'])

    if data is None:
        return

    gui_data = run_gui_formed_detection(data, extremum_length=1)

    # Compare
    compare_counts(backtest_data, gui_data)

    print("\n" + "="*80)
    print("✅ Verification Complete!")
    print("="*80)


if __name__ == '__main__':
    main()
