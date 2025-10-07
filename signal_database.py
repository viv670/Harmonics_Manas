"""
Signal Database - Store and manage pattern signals for alerts

This module handles persistent storage of trading signals detected by the
pattern monitoring system.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class TradingSignal:
    """Represents a trading signal from a detected pattern"""
    signal_id: str
    symbol: str
    timeframe: str
    pattern_type: str          # ABCD or XABCD
    pattern_name: str          # Gartley_bull, etc.
    direction: str             # bullish or bearish

    # Pattern points
    points_json: str           # JSON string of all points

    # PRZ/Entry info
    prz_min: float
    prz_max: float
    d_lines_json: str          # JSON string of d_lines (for XABCD)
    prz_zones_json: str        # JSON string of all PRZ zones

    # Pattern formation status
    is_formed: bool            # True if D point completed, False if D projected

    # Status tracking
    status: str                # detected, approaching, entered, completed, invalidated
    alerts_sent_json: str      # JSON list of alerts already sent

    # Timestamps
    detected_at: str           # ISO format datetime
    last_updated: str          # ISO format datetime

    # Current price tracking
    current_price: float
    distance_to_prz_pct: float # Percentage distance to PRZ

    # Trading parameters
    entry_price: float
    stop_loss: float
    targets_json: str          # JSON list of target prices

    # Quality score (placeholder for now)
    score: int = 50


class SignalDatabase:
    """Manages SQLite database for trading signals"""

    def __init__(self, db_path: str = "data/signals.db"):
        """Initialize database connection"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_database()

    def _get_connection(self):
        """Get thread-safe database connection"""
        # Each thread gets its own connection using check_same_thread=False
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Create database tables if they don't exist"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                signal_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                direction TEXT NOT NULL,

                points_json TEXT NOT NULL,

                prz_min REAL NOT NULL,
                prz_max REAL NOT NULL,
                d_lines_json TEXT,
                prz_zones_json TEXT,

                is_formed INTEGER NOT NULL DEFAULT 0,

                status TEXT NOT NULL,
                alerts_sent_json TEXT NOT NULL,

                detected_at TEXT NOT NULL,
                last_updated TEXT NOT NULL,

                current_price REAL NOT NULL,
                distance_to_prz_pct REAL NOT NULL,

                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                targets_json TEXT NOT NULL,

                score INTEGER DEFAULT 50
            )
        ''')

        # Create comprehensive indices for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_status
            ON signals(symbol, status)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status
            ON signals(status)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_symbol_timeframe
            ON signals(symbol, timeframe)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_status_created
            ON signals(status, detected_at DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_pattern_type
            ON signals(pattern_type, pattern_name)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timeframe
            ON signals(timeframe)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_direction_status
            ON signals(direction, status)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_last_updated
            ON signals(last_updated DESC)
        ''')

        # Create price_alerts table for individual price level alerts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                price_level REAL NOT NULL,
                level_name TEXT NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 0,
                was_triggered INTEGER NOT NULL DEFAULT 0,
                triggered_at TEXT,
                FOREIGN KEY (signal_id) REFERENCES signals(signal_id) ON DELETE CASCADE
            )
        ''')

        # Create index for price_alerts
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_price_alerts_signal
            ON price_alerts(signal_id, is_enabled, was_triggered)
        ''')

        # Create pattern_statistics table for Fibonacci and Harmonic Points historical data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_statistics (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                direction TEXT NOT NULL,
                stat_type TEXT NOT NULL,
                level_name TEXT NOT NULL,
                patterns_hit INTEGER NOT NULL DEFAULT 0,
                hit_percentage REAL NOT NULL DEFAULT 0.0,
                avg_touches REAL NOT NULL DEFAULT 0.0,
                sample_count INTEGER NOT NULL DEFAULT 0,
                last_updated TEXT NOT NULL,
                UNIQUE(symbol, timeframe, pattern_type, pattern_name, direction, stat_type, level_name)
            )
        ''')

        # Create index for pattern_statistics
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_pattern_stats_lookup
            ON pattern_statistics(symbol, timeframe, pattern_type, pattern_name, direction)
        ''')

        # Migration: Add is_formed column if it doesn't exist
        try:
            cursor.execute("SELECT is_formed FROM signals LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            print("Adding is_formed column to signals table...")
            cursor.execute('''
                ALTER TABLE signals ADD COLUMN is_formed INTEGER NOT NULL DEFAULT 0
            ''')
            conn.commit()
            print("✓ is_formed column added successfully")

        # Migration: Add prz_zones_json column if it doesn't exist
        try:
            cursor.execute("SELECT prz_zones_json FROM signals LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            print("Adding prz_zones_json column to signals table...")
            cursor.execute('''
                ALTER TABLE signals ADD COLUMN prz_zones_json TEXT
            ''')
            conn.commit()
            print("✓ prz_zones_json column added successfully")

        conn.commit()
        conn.close()

    def add_signal(self, signal: TradingSignal) -> bool:
        """Add new signal to database"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO signals VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            ''', (
                signal.signal_id,
                signal.symbol,
                signal.timeframe,
                signal.pattern_type,
                signal.pattern_name,
                signal.direction,
                signal.points_json,
                signal.prz_min,
                signal.prz_max,
                signal.d_lines_json,
                signal.prz_zones_json,
                int(signal.is_formed),  # Convert bool to int for SQLite
                signal.status,
                signal.alerts_sent_json,
                signal.detected_at,
                signal.last_updated,
                signal.current_price,
                signal.distance_to_prz_pct,
                signal.entry_price,
                signal.stop_loss,
                signal.targets_json,
                signal.score
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Signal already exists
            return False
        except Exception as e:
            print(f"Error adding signal: {e}")
            return False
        finally:
            conn.close()

    def update_signal(self, signal_id: str, updates: Dict) -> bool:
        """Update existing signal"""
        conn = self._get_connection()
        try:
            # Build UPDATE query dynamically
            set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
            values = list(updates.values())

            cursor = conn.cursor()
            cursor.execute(f'''
                UPDATE signals
                SET {set_clause}, last_updated = ?
                WHERE signal_id = ?
            ''', values + [datetime.now().isoformat(), signal_id])

            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating signal: {e}")
            return False
        finally:
            conn.close()

    def get_signal(self, signal_id: str) -> Optional[Dict]:
        """Get single signal by ID"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM signals WHERE signal_id = ?', (signal_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_active_signals(self) -> List[Dict]:
        """Get all active signals (not completed or invalidated)"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM signals
                WHERE status IN ('detected', 'approaching', 'entered')
                ORDER BY detected_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_signals_with_outcomes(self) -> List[Dict]:
        """Get ALL signals including completed and invalidated"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM signals
                ORDER BY detected_at DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_signals_by_symbol(self, symbol: str, active_only: bool = True) -> List[Dict]:
        """Get signals for specific symbol"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if active_only:
                cursor.execute('''
                    SELECT * FROM signals
                    WHERE symbol = ? AND status IN ('detected', 'approaching', 'entered')
                    ORDER BY detected_at DESC
                ''', (symbol,))
            else:
                cursor.execute('''
                    SELECT * FROM signals
                    WHERE symbol = ?
                    ORDER BY detected_at DESC
                ''', (symbol,))

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_signals_by_status(self, status: str) -> List[Dict]:
        """Get signals by status"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM signals
                WHERE status = ?
                ORDER BY detected_at DESC
            ''', (status,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def mark_signal_invalidated(self, signal_id: str, reason: str = ""):
        """Mark signal as invalidated"""
        return self.update_signal(signal_id, {
            'status': 'invalidated'
        })

    def mark_signal_completed(self, signal_id: str):
        """Mark signal as completed"""
        return self.update_signal(signal_id, {
            'status': 'completed'
        })

    def cleanup_old_signals(self, days: int = 30):
        """Remove completed/invalidated signals older than X days"""
        conn = self._get_connection()
        try:
            cutoff_date = datetime.now()
            # Simple cleanup - remove old completed/invalidated signals
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM signals
                WHERE status IN ('completed', 'invalidated')
                AND datetime(last_updated) < datetime('now', '-' || ? || ' days')
            ''', (days,))
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            print(f"Error cleaning up signals: {e}")
            return 0
        finally:
            conn.close()

    def add_price_alert(self, signal_id: str, alert_type: str, price_level: float,
                        level_name: str, is_enabled: bool = False) -> bool:
        """
        Add a price alert for a signal

        Args:
            signal_id: Signal ID to attach alert to
            alert_type: 'fibonacci' or 'harmonic_point'
            price_level: Price to trigger alert
            level_name: Name of level (e.g., '23.6%', 'Point A')
            is_enabled: Whether alert is enabled (default: False)
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO price_alerts (signal_id, alert_type, price_level, level_name, is_enabled)
                VALUES (?, ?, ?, ?, ?)
            ''', (signal_id, alert_type, price_level, level_name, int(is_enabled)))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding price alert: {e}")
            return False
        finally:
            conn.close()

    def get_price_alerts(self, signal_id: str) -> List[Dict]:
        """Get all price alerts for a signal"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM price_alerts
                WHERE signal_id = ?
                ORDER BY price_level
            ''', (signal_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_active_price_alerts(self, signal_id: str) -> List[Dict]:
        """Get enabled, non-triggered price alerts for a signal"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM price_alerts
                WHERE signal_id = ? AND is_enabled = 1 AND was_triggered = 0
                ORDER BY price_level
            ''', (signal_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def toggle_price_alert(self, alert_id: int, enabled: bool) -> bool:
        """Enable or disable a price alert"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE price_alerts
                SET is_enabled = ?
                WHERE alert_id = ?
            ''', (int(enabled), alert_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error toggling price alert: {e}")
            return False
        finally:
            conn.close()

    def mark_price_alert_triggered(self, alert_id: int) -> bool:
        """Mark a price alert as triggered"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE price_alerts
                SET was_triggered = 1, triggered_at = ?
                WHERE alert_id = ?
            ''', (datetime.now().isoformat(), alert_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error marking alert triggered: {e}")
            return False
        finally:
            conn.close()

    def delete_signal_alerts(self, signal_id: str) -> bool:
        """Delete all price alerts for a signal (called when pattern completes/hits 161.8%)"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM price_alerts
                WHERE signal_id = ?
            ''', (signal_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting signal alerts: {e}")
            return False
        finally:
            conn.close()

    def upsert_pattern_statistic(self, symbol: str, timeframe: str, pattern_type: str,
                                  pattern_name: str, direction: str, stat_type: str,
                                  level_name: str, patterns_hit: int, hit_percentage: float,
                                  avg_touches: float, sample_count: int) -> bool:
        """
        Insert or update pattern statistic

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            pattern_type: ABCD or XABCD
            pattern_name: Specific pattern (e.g., Gartley, Bat)
            direction: bullish or bearish
            stat_type: 'fibonacci' or 'harmonic_point'
            level_name: Level name (e.g., '50%', 'Point A')
            patterns_hit: Number of patterns that hit this level
            hit_percentage: Percentage of patterns that hit this level
            avg_touches: Average number of touches when hit
            sample_count: Total number of patterns analyzed
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            now = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO pattern_statistics
                (symbol, timeframe, pattern_type, pattern_name, direction, stat_type, level_name,
                 patterns_hit, hit_percentage, avg_touches, sample_count, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol, timeframe, pattern_type, pattern_name, direction, stat_type, level_name)
                DO UPDATE SET
                    patterns_hit = excluded.patterns_hit,
                    hit_percentage = excluded.hit_percentage,
                    avg_touches = excluded.avg_touches,
                    sample_count = excluded.sample_count,
                    last_updated = excluded.last_updated
            ''', (symbol, timeframe, pattern_type, pattern_name, direction, stat_type, level_name,
                  patterns_hit, hit_percentage, avg_touches, sample_count, now))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error upserting pattern statistic: {e}")
            return False
        finally:
            conn.close()

    def get_pattern_statistics(self, symbol: str, timeframe: str, pattern_type: str = None,
                               pattern_name: str = None, direction: str = None) -> List[Dict]:
        """
        Get pattern statistics filtered by various criteria

        Args:
            symbol: Trading symbol (required)
            timeframe: Timeframe (required)
            pattern_type: Optional filter for ABCD or XABCD
            pattern_name: Optional filter for specific pattern
            direction: Optional filter for bullish or bearish
        """
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            query = '''
                SELECT * FROM pattern_statistics
                WHERE symbol = ? AND timeframe = ?
            '''
            params = [symbol, timeframe]

            if pattern_type:
                query += ' AND pattern_type = ?'
                params.append(pattern_type)

            if pattern_name:
                query += ' AND pattern_name = ?'
                params.append(pattern_name)

            if direction:
                query += ' AND direction = ?'
                params.append(direction)

            query += ' ORDER BY stat_type, hit_percentage DESC'

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_all_pattern_statistics(self) -> List[Dict]:
        """Get all pattern statistics across all symbols/timeframes"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM pattern_statistics ORDER BY symbol, timeframe, pattern_name')
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    def close(self):
        """Close database connection - no-op since we use per-call connections"""
        pass


def generate_signal_id(symbol: str, timeframe: str, pattern: Dict) -> str:
    """Generate unique ID for a signal"""
    # Use pattern points to create unique ID
    points = pattern.get('points', {})

    point_ids = []
    for point_name in ['X', 'A', 'B', 'C']:
        if point_name in points:
            point_data = points[point_name]
            if isinstance(point_data, (list, tuple)):
                idx = point_data[0]
            elif isinstance(point_data, dict):
                idx = point_data.get('index', point_data.get('bar', 0))
            else:
                idx = 0
            point_ids.append(f"{point_name}{idx}")

    pattern_name = pattern.get('name', 'unknown')
    signal_id = f"{symbol}_{timeframe}_{pattern_name}_{'_'.join(point_ids)}"

    return signal_id


def create_signal_from_pattern(symbol: str, timeframe: str, pattern: Dict,
                               current_price: float) -> TradingSignal:
    """Convert detected pattern to TradingSignal object"""

    signal_id = generate_signal_id(symbol, timeframe, pattern)

    # Extract PRZ info
    points = pattern.get('points', {})
    prz_min = 0
    prz_max = 0
    d_lines = []
    prz_zones = []

    # Determine if pattern is formed or unformed
    is_formed = pattern.get('is_formed', False)

    # Check if this is an XABCD pattern (unformed with D_projected)
    d_proj = pattern.get('D_projected', points.get('D_projected', {}))

    if isinstance(d_proj, dict):
        prz_zones = d_proj.get('prz_zones', [])
        d_lines = d_proj.get('d_lines', [])

        if prz_zones:
            prz_min = min(zone['min'] for zone in prz_zones)
            prz_max = max(zone['max'] for zone in prz_zones)
        elif d_lines:
            prz_min = min(d_lines)
            prz_max = max(d_lines)

    # If no projected D, check if pattern has actual D point (formed pattern)
    if prz_min == 0 and 'D' in points:
        is_formed = True  # Has actual D point
        d_point = points['D']
        if isinstance(d_point, (list, tuple)):
            d_price = d_point[1]  # (index, price, ...)
        elif isinstance(d_point, dict):
            d_price = d_point.get('price', 0)
        else:
            d_price = 0

        if d_price > 0:
            # For formed patterns, PRZ is a small zone around D point (±0.1%)
            prz_min = d_price * 0.999
            prz_max = d_price * 1.001
            d_lines = [d_price]

    # Calculate distance to PRZ
    if prz_min > 0:
        if current_price < prz_min:
            distance_pct = ((prz_min - current_price) / current_price) * 100
        elif current_price > prz_max:
            distance_pct = ((current_price - prz_max) / current_price) * 100
        else:
            distance_pct = 0  # Inside PRZ
    else:
        distance_pct = 999  # Unknown

    # Determine direction
    direction = 'bullish' if pattern.get('bullish', True) else 'bearish'

    # Helper to extract price from point
    def get_point_price(point_data):
        if isinstance(point_data, (list, tuple)) and len(point_data) > 1:
            return point_data[1]
        elif isinstance(point_data, dict):
            return point_data.get('price', 0)
        return 0

    # Calculate entry, stop, targets
    if direction == 'bullish':
        entry_price = prz_min if prz_min > 0 else current_price

        # Stop loss at X point or below D
        x_price = get_point_price(points.get('X')) if 'X' in points else 0
        stop_loss = x_price if x_price > 0 else (prz_min * 0.95 if prz_min > 0 else current_price * 0.95)

        # Targets at C and A
        c_price = get_point_price(points.get('C'))
        a_price = get_point_price(points.get('A'))
        targets = [
            c_price if c_price > 0 else (prz_max * 1.05 if prz_max > 0 else current_price * 1.05),
            a_price if a_price > 0 else (prz_max * 1.10 if prz_max > 0 else current_price * 1.10),
        ]
    else:
        entry_price = prz_max if prz_max > 0 else current_price

        # Stop loss at X point or above D
        x_price = get_point_price(points.get('X')) if 'X' in points else 0
        stop_loss = x_price if x_price > 0 else (prz_max * 1.05 if prz_max > 0 else current_price * 1.05)

        # Targets at C and A
        c_price = get_point_price(points.get('C'))
        a_price = get_point_price(points.get('A'))
        targets = [
            c_price if c_price > 0 else (prz_min * 0.95 if prz_min > 0 else current_price * 0.95),
            a_price if a_price > 0 else (prz_min * 0.90 if prz_min > 0 else current_price * 0.90),
        ]

    now = datetime.now().isoformat()

    signal = TradingSignal(
        signal_id=signal_id,
        symbol=symbol,
        timeframe=timeframe,
        pattern_type=pattern.get('pattern_type', 'XABCD'),
        pattern_name=pattern.get('name', 'Unknown'),
        direction=direction,
        points_json=json.dumps(points),
        prz_min=prz_min,
        prz_max=prz_max,
        d_lines_json=json.dumps(d_lines),
        prz_zones_json=json.dumps(prz_zones if prz_zones else []),
        is_formed=is_formed,
        status='detected',
        alerts_sent_json=json.dumps([]),
        detected_at=now,
        last_updated=now,
        current_price=current_price,
        distance_to_prz_pct=distance_pct,
        entry_price=entry_price,
        stop_loss=stop_loss,
        targets_json=json.dumps(targets),
        score=50  # Placeholder
    )

    return signal


def create_price_alerts_for_signal(db: SignalDatabase, signal: TradingSignal, pattern: Dict) -> None:
    """
    Create price alerts for Fibonacci levels and harmonic points

    All alerts are created as DISABLED by default.
    Alerts remain active until pattern hits 161.8% Fibonacci (completion).

    Args:
        db: SignalDatabase instance
        signal: TradingSignal object
        pattern: Pattern dictionary containing points
    """
    points = pattern.get('points', {})

    # Helper to extract price from point
    def get_point_price(point_data):
        if isinstance(point_data, (list, tuple)) and len(point_data) > 1:
            return point_data[1]
        elif isinstance(point_data, dict):
            return point_data.get('price', 0)
        return 0

    # Get A, C, D prices
    a_price = get_point_price(points.get('A'))
    c_price = get_point_price(points.get('C'))
    d_price = signal.entry_price  # Use entry_price as D reference

    if a_price == 0 or c_price == 0 or d_price == 0:
        print(f"⚠️ Cannot create price alerts - missing price data")
        return

    # Determine direction for Fibonacci calculation
    is_bullish = a_price > c_price

    # Calculate Fibonacci levels (same logic as backtesting)
    if is_bullish:
        start_price = max(a_price, c_price)  # 0% at swing high (C or A)
        end_price = d_price  # 100% at D (higher)
        price_range = end_price - start_price
    else:
        # BEARISH: Retracement FROM D back down
        start_price = d_price  # 0% at D (the high where pattern completed)
        end_price = min(a_price, c_price)  # 100% back to swing low (C or A)
        price_range = end_price - start_price  # Negative range for bearish

    # Fibonacci percentages (0% to 161.8%)
    fib_percentages = [0, 23.6, 38.2, 50, 61.8, 78.6, 88.6, 100, 112.8, 127.2, 141.4, 161.8]

    # Create Fibonacci alerts
    for pct in fib_percentages:
        level_price = start_price + (price_range * pct / 100.0)
        level_name = f"Fib {pct}%"
        db.add_price_alert(signal.signal_id, 'fibonacci', level_price, level_name, is_enabled=False)

    # Create Harmonic Point alerts (A, B, C)
    for point_name in ['A', 'B', 'C']:
        if point_name in points:
            point_price = get_point_price(points[point_name])
            if point_price > 0:
                level_name = f"Point {point_name}"
                db.add_price_alert(signal.signal_id, 'harmonic_point', point_price, level_name, is_enabled=False)

    print(f"✅ Created {len(fib_percentages) + 3} price alerts for {signal.signal_id} (all disabled by default)")
