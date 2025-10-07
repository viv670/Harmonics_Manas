"""
Scan Watchlist and Populate Active Signals Database

This script scans all charts in the watchlist, detects patterns,
and populates the signals database for the Active Signals window.

Usage:
    python scan_and_populate_signals.py
"""

import pandas as pd
import json
import os
from datetime import datetime

# Import detection modules
from extremum import detect_extremum_points
from formed_xabcd import detect_xabcd_patterns
from formed_abcd import detect_strict_abcd_patterns
from unformed_abcd import detect_unformed_abcd_patterns_optimized
from unformed_xabcd import detect_strict_unformed_xabcd_patterns

# Import signal database
from signal_database import (
    SignalDatabase,
    create_signal_from_pattern,
    create_price_alerts_for_signal
)


def load_watchlist(watchlist_path="data/watchlist.json"):
    """Load watchlist from JSON file"""
    if not os.path.exists(watchlist_path):
        print(f"❌ Watchlist not found at {watchlist_path}")
        return []

    with open(watchlist_path, 'r') as f:
        data = json.load(f)
        return data.get('charts', [])


def load_chart_data(file_path):
    """Load chart data from CSV"""
    if not os.path.exists(file_path):
        print(f"  ❌ File not found: {file_path}")
        return None

    try:
        df = pd.read_csv(file_path)

        # Ensure datetime index
        if 'Timestamp' in df.columns:
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])
            df.set_index('Timestamp', inplace=True)
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)

        # Standardize column names to uppercase
        column_mapping = {}
        for col in df.columns:
            if col.lower() in ['open', 'high', 'low', 'close', 'volume']:
                column_mapping[col] = col.capitalize()

        if column_mapping:
            df.rename(columns=column_mapping, inplace=True)

        return df
    except Exception as e:
        print(f"  ❌ Error loading data: {e}")
        return None


def detect_patterns_for_chart(df, extremum_length=5):
    """Detect all patterns for a chart - using extremum_length=5 for faster detection"""
    patterns = []

    # Detect extremum points
    print(f"  ⏳ Detecting extremum points...", flush=True)
    extremum_points = detect_extremum_points(df, length=extremum_length)
    print(f"  ✓ Found {len(extremum_points)} extremum points", flush=True)

    if len(extremum_points) < 4:
        return patterns

    # Only detect the most recent patterns (last 50 extremum points)
    # This speeds up detection significantly
    recent_extremum = extremum_points[-50:] if len(extremum_points) > 50 else extremum_points

    # Detect formed XABCD patterns
    try:
        print(f"  ⏳ Detecting XABCD formed...", flush=True)
        xabcd_formed = detect_xabcd_patterns(recent_extremum, df=df, log_details=False)
        for pattern in xabcd_formed:
            pattern['is_formed'] = True
            pattern['pattern_type'] = 'XABCD'
            patterns.append(pattern)
        print(f"  ✓ Found {len(xabcd_formed)} XABCD formed", flush=True)
    except Exception as e:
        print(f"  ⚠️ XABCD formed detection error: {e}", flush=True)

    # Detect unformed XABCD patterns
    try:
        print(f"  ⏳ Detecting XABCD unformed...", flush=True)
        xabcd_unformed = detect_strict_unformed_xabcd_patterns(recent_extremum, df=df, log_details=False)
        for pattern in xabcd_unformed:
            pattern['is_formed'] = False
            pattern['pattern_type'] = 'XABCD'
            patterns.append(pattern)
        print(f"  ✓ Found {len(xabcd_unformed)} XABCD unformed", flush=True)
    except Exception as e:
        print(f"  ⚠️ XABCD unformed detection error: {e}", flush=True)

    # Detect formed ABCD patterns
    try:
        print(f"  ⏳ Detecting ABCD formed...", flush=True)
        abcd_formed = detect_strict_abcd_patterns(recent_extremum, df=df, log_details=False)
        for pattern in abcd_formed:
            pattern['is_formed'] = True
            pattern['pattern_type'] = 'ABCD'
            patterns.append(pattern)
        print(f"  ✓ Found {len(abcd_formed)} ABCD formed", flush=True)
    except Exception as e:
        print(f"  ⚠️ ABCD formed detection error: {e}", flush=True)

    # Detect unformed ABCD patterns
    try:
        print(f"  ⏳ Detecting ABCD unformed...", flush=True)
        abcd_unformed = detect_unformed_abcd_patterns_optimized(recent_extremum, df=df, log_details=False)
        for pattern in abcd_unformed:
            pattern['is_formed'] = False
            pattern['pattern_type'] = 'ABCD'
            patterns.append(pattern)
        print(f"  ✓ Found {len(abcd_unformed)} ABCD unformed", flush=True)
    except Exception as e:
        print(f"  ⚠️ ABCD unformed detection error: {e}", flush=True)

    return patterns


def main():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║          Pattern Detection & Database Population          ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()

    # Load watchlist
    watchlist = load_watchlist()

    if not watchlist:
        print("❌ No charts in watchlist")
        return

    # Filter only enabled charts with monitor_alerts
    enabled_charts = [c for c in watchlist if c.get('enabled', True) and c.get('monitor_alerts', False)]

    # LIMIT TO FIRST 3 CHARTS to prevent hanging
    enabled_charts = enabled_charts[:3]

    print(f"Scanning {len(enabled_charts)} charts from watchlist (limited to 3 to prevent hanging)...")
    print()

    # Initialize database
    db = SignalDatabase()

    # Statistics
    total_patterns = 0
    abcd_count = 0
    xabcd_count = 0
    formed_count = 0
    unformed_count = 0
    signals_added = 0
    alerts_created = 0

    # Process each chart
    for idx, chart in enumerate(enabled_charts, 1):
        symbol = chart['symbol']
        timeframe = chart['timeframe']
        file_path = chart['file_path']

        print(f"[{idx}/{len(enabled_charts)}] {symbol} {timeframe}")

        # Load data
        df = load_chart_data(file_path)
        if df is None:
            continue

        print(f"  ✓ Loaded {len(df)} bars")

        # Detect patterns
        patterns = detect_patterns_for_chart(df)

        if not patterns:
            print(f"  ⚠️ No patterns detected")
            print()
            continue

        # Get current price
        current_price = float(df['Close'].iloc[-1])

        print(f"  ✓ Found {len(patterns)} patterns")

        # Add patterns to database
        for pattern in patterns:
            try:
                # Create signal
                signal = create_signal_from_pattern(symbol, timeframe, pattern, current_price)

                # Add to database
                if db.add_signal(signal):
                    signals_added += 1
                    total_patterns += 1

                    # Count by type
                    if pattern['pattern_type'] == 'ABCD':
                        abcd_count += 1
                    else:
                        xabcd_count += 1

                    # Count by formed/unformed
                    if pattern.get('is_formed', False):
                        formed_count += 1
                    else:
                        unformed_count += 1

                    # Create price alerts
                    create_price_alerts_for_signal(db, signal, pattern)
                    alerts_created += 15  # 12 Fib + 3 Points

            except Exception as e:
                print(f"  ⚠️ Error adding pattern: {e}")

        print(f"  ✓ Added {len(patterns)} signals to database")
        print(f"  ✓ Created {len(patterns) * 15} price alerts")
        print()

    # Summary
    print()
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                    Scan Complete!                         ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print()
    print(f"Total patterns detected: {total_patterns}")
    print(f"  • ABCD patterns: {abcd_count}")
    print(f"  • XABCD patterns: {xabcd_count}")
    print(f"  • Formed patterns: {formed_count}")
    print(f"  • Unformed patterns: {unformed_count}")
    print()
    print(f"Signals added to database: {signals_added}")
    print(f"Price alerts created: {alerts_created}")
    print()
    print("✅ Active Signals database populated!")
    print("   Open Active Signals Window to view and manage patterns.")
    print()


if __name__ == "__main__":
    main()
