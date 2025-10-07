"""
Migration script to populate prz_zones_json for existing signals in the database.

This script:
1. Reads all signals from the database
2. For ABCD patterns, re-detects them to get prz_zones
3. Updates the prz_zones_json field in the database
"""

import sqlite3
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Import pattern detection functions
from unformed_abcd import detect_unformed_abcd_patterns

def load_chart_data(symbol, timeframe):
    """Load chart data from file"""
    # Try common locations
    possible_paths = [
        f"data/{symbol.lower()}_{timeframe}.csv",
        f"{symbol.lower()}_{timeframe}.csv",
    ]

    for path_str in possible_paths:
        path = Path(path_str)
        if path.exists():
            print(f"  Loading data from: {path}")
            df = pd.read_csv(path)

            # Ensure Timestamp column exists and is datetime
            if 'Timestamp' in df.columns:
                df['Timestamp'] = pd.to_datetime(df['Timestamp'])
                df.set_index('Timestamp', inplace=True)
            elif 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)

            # Standardize column names
            df.columns = [col.capitalize() for col in df.columns]

            return df

    return None

def detect_pattern_and_get_prz_zones(symbol, timeframe, pattern_type, pattern_name, points_json):
    """Re-detect pattern to get prz_zones"""

    # Load chart data
    df = load_chart_data(symbol, timeframe)
    if df is None:
        print(f"  ⚠️  Could not find data file for {symbol} {timeframe}")
        return None

    # Parse points
    points = json.loads(points_json)

    # Only ABCD patterns have multiple PRZ zones
    if 'X' in points:
        print(f"  ℹ️  XABCD pattern - skipping (no multiple PRZ zones)")
        return None

    # For ABCD patterns, we need to re-detect to get prz_zones
    try:
        # Detect patterns
        patterns = detect_unformed_abcd_patterns(df)

        if not patterns:
            print(f"  ⚠️  No patterns detected")
            return None

        # Find matching pattern by comparing points
        a_time = pd.to_datetime(points['A']['time'])
        b_time = pd.to_datetime(points['B']['time'])
        c_time = pd.to_datetime(points['C']['time'])

        for pattern in patterns:
            p_points = pattern.get('points', {})
            if 'A' not in p_points or 'B' not in p_points or 'C' not in p_points:
                continue

            p_a_time = pd.to_datetime(p_points['A']['time'])
            p_b_time = pd.to_datetime(p_points['B']['time'])
            p_c_time = pd.to_datetime(p_points['C']['time'])

            # Check if times match (within 1 bar tolerance)
            if (abs((a_time - p_a_time).total_seconds()) < 86400 and
                abs((b_time - p_b_time).total_seconds()) < 86400 and
                abs((c_time - p_c_time).total_seconds()) < 86400):

                # Found matching pattern - extract prz_zones
                d_proj = pattern.get('D_projected', p_points.get('D_projected', {}))
                if isinstance(d_proj, dict):
                    prz_zones = d_proj.get('prz_zones', [])
                    if prz_zones:
                        print(f"  ✓ Found {len(prz_zones)} PRZ zones")
                        return prz_zones

        print(f"  ⚠️  Could not find matching pattern")
        return None

    except Exception as e:
        print(f"  ❌ Error detecting pattern: {e}")
        import traceback
        traceback.print_exc()
        return None

def migrate_prz_zones():
    """Main migration function"""

    db_path = Path("data/signals.db")
    if not db_path.exists():
        print("❌ Database not found at data/signals.db")
        return

    print(f"📊 Migrating PRZ zones for existing signals...")
    print(f"Database: {db_path}")
    print()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get all signals
    cursor.execute("""
        SELECT signal_id, symbol, timeframe, pattern_type, pattern_name,
               points_json, prz_zones_json
        FROM signals
    """)

    signals = cursor.fetchall()
    print(f"Found {len(signals)} signals in database")
    print()

    updated_count = 0
    skipped_count = 0
    error_count = 0

    for signal_id, symbol, timeframe, pattern_type, pattern_name, points_json, prz_zones_json in signals:
        print(f"Processing: {signal_id}")

        # Skip if already has prz_zones_json
        if prz_zones_json:
            try:
                existing_zones = json.loads(prz_zones_json)
                if existing_zones:
                    print(f"  ℹ️  Already has {len(existing_zones)} PRZ zones - skipping")
                    skipped_count += 1
                    continue
            except:
                pass

        # Detect pattern and get prz_zones
        prz_zones = detect_pattern_and_get_prz_zones(
            symbol, timeframe, pattern_type, pattern_name, points_json
        )

        if prz_zones:
            # Update database
            prz_zones_json_str = json.dumps(prz_zones)
            cursor.execute("""
                UPDATE signals
                SET prz_zones_json = ?
                WHERE signal_id = ?
            """, (prz_zones_json_str, signal_id))

            print(f"  ✅ Updated with {len(prz_zones)} PRZ zones")
            updated_count += 1
        else:
            print(f"  ⚠️  No PRZ zones found - leaving empty")
            error_count += 1

        print()

    # Commit changes
    conn.commit()
    conn.close()

    print()
    print("="*60)
    print("Migration complete!")
    print(f"  ✅ Updated: {updated_count}")
    print(f"  ℹ️  Skipped: {skipped_count}")
    print(f"  ⚠️  No zones: {error_count}")
    print("="*60)

if __name__ == "__main__":
    migrate_prz_zones()
