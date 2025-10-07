"""
Database Optimization Script
Adds indices and optimizes existing signal database

Run this script to add missing indices to existing databases
and perform database optimization.
"""

import sqlite3
from pathlib import Path


def optimize_database(db_path='data/signals.db'):
    """
    Optimize database by adding indices and running VACUUM.

    Args:
        db_path: Path to signals database
    """
    db_file = Path(db_path)
    if not db_file.exists():
        print(f"❌ Database not found at {db_path}")
        return

    print(f"🔧 Optimizing database: {db_path}")
    print()

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    # Add missing indices
    indices = [
        ('idx_symbol_status', 'signals(symbol, status)'),
        ('idx_status', 'signals(status)'),
        ('idx_symbol_timeframe', 'signals(symbol, timeframe)'),
        ('idx_status_created', 'signals(status, detected_at DESC)'),
        ('idx_pattern_type', 'signals(pattern_type, pattern_name)'),
        ('idx_timeframe', 'signals(timeframe)'),
        ('idx_direction_status', 'signals(direction, status)'),
        ('idx_last_updated', 'signals(last_updated DESC)'),
    ]

    print("📊 Creating indices...")
    for idx_name, idx_def in indices:
        try:
            cursor.execute(f'CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}')
            print(f"  ✓ {idx_name}")
        except Exception as e:
            print(f"  ✗ {idx_name}: {e}")

    conn.commit()

    # Get database statistics
    print()
    print("📈 Database Statistics:")

    cursor.execute("SELECT COUNT(*) FROM signals")
    total_signals = cursor.fetchone()[0]
    print(f"  Total signals: {total_signals}")

    cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'active'")
    active_signals = cursor.fetchone()[0]
    print(f"  Active signals: {active_signals}")

    cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'in_zone'")
    in_zone_signals = cursor.fetchone()[0]
    print(f"  In-zone signals: {in_zone_signals}")

    cursor.execute("SELECT COUNT(*) FROM signals WHERE status = 'success'")
    successful_signals = cursor.fetchone()[0]
    print(f"  Successful signals: {successful_signals}")

    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM signals")
    unique_symbols = cursor.fetchone()[0]
    print(f"  Unique symbols: {unique_symbols}")

    cursor.execute("SELECT COUNT(DISTINCT timeframe) FROM signals")
    unique_timeframes = cursor.fetchone()[0]
    print(f"  Unique timeframes: {unique_timeframes}")

    # Get database size
    cursor.execute("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size()")
    db_size = cursor.fetchone()[0]
    db_size_mb = db_size / (1024 * 1024)
    print(f"  Database size: {db_size_mb:.2f} MB")

    # Run VACUUM to optimize database file
    print()
    print("🗜️  Running VACUUM to optimize database...")
    try:
        cursor.execute("VACUUM")
        print("  ✓ Database optimized")
    except Exception as e:
        print(f"  ✗ VACUUM failed: {e}")

    # Run ANALYZE to update statistics
    print()
    print("📊 Updating query optimizer statistics...")
    try:
        cursor.execute("ANALYZE")
        print("  ✓ Statistics updated")
    except Exception as e:
        print(f"  ✗ ANALYZE failed: {e}")

    # Check integrity
    print()
    print("🔍 Checking database integrity...")
    cursor.execute("PRAGMA integrity_check")
    integrity_result = cursor.fetchone()[0]
    if integrity_result == 'ok':
        print("  ✓ Database integrity OK")
    else:
        print(f"  ⚠️  Integrity check result: {integrity_result}")

    conn.close()

    print()
    print("✅ Database optimization complete!")


def analyze_query_performance(db_path='data/signals.db'):
    """
    Analyze query performance with and without indices.

    Args:
        db_path: Path to signals database
    """
    import time

    db_file = Path(db_path)
    if not db_file.exists():
        print(f"❌ Database not found at {db_path}")
        return

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    print("⚡ Query Performance Analysis:")
    print()

    # Test query 1: Get active signals for symbol
    test_queries = [
        ("Active signals by symbol", "SELECT * FROM signals WHERE symbol = 'BTCUSDT' AND status = 'active'"),
        ("Recent signals", "SELECT * FROM signals ORDER BY detected_at DESC LIMIT 100"),
        ("Bullish patterns", "SELECT * FROM signals WHERE direction = 'bullish' AND status IN ('active', 'in_zone')"),
        ("By pattern type", "SELECT * FROM signals WHERE pattern_type = 'ABCD' AND pattern_name LIKE '%Gartley%'"),
        ("By timeframe", "SELECT * FROM signals WHERE timeframe = '1d'"),
    ]

    for query_name, query in test_queries:
        # Enable query plan
        cursor.execute(f"EXPLAIN QUERY PLAN {query}")
        plan = cursor.fetchall()

        # Execute and time
        start = time.time()
        cursor.execute(query)
        results = cursor.fetchall()
        elapsed = (time.time() - start) * 1000  # Convert to ms

        print(f"{query_name}:")
        print(f"  Results: {len(results)}")
        print(f"  Time: {elapsed:.2f}ms")
        print(f"  Plan: {plan[0][3] if plan else 'N/A'}")
        print()

    conn.close()


if __name__ == "__main__":
    print("="*60)
    print("DATABASE OPTIMIZATION TOOL")
    print("="*60)
    print()

    # Optimize database
    optimize_database()

    print()
    print("="*60)
    print()

    # Analyze performance
    analyze_query_performance()

    print()
    print("="*60)
    print("OPTIMIZATION COMPLETE")
    print("="*60)
