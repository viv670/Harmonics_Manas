"""
Signal Service

Business logic for signal management and tracking.
"""

import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import json
import logging

from exceptions import DatabaseError, SignalNotFoundError
from logging_config import get_logger


class SignalService:
    """
    Service for signal operations.

    Handles signal storage, retrieval, updates, and lifecycle management.
    """

    def __init__(self, db_path: str = 'data/signals.db'):
        """
        Initialize signal service.

        Args:
            db_path: Path to signals database
        """
        self.db_path = db_path
        self.logger = get_logger()
        self._ensure_database()

    def _ensure_database(self):
        """Ensure database and tables exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    pattern_type TEXT NOT NULL,
                    pattern_name TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    status TEXT NOT NULL,
                    detected_at TIMESTAMP NOT NULL,
                    last_updated TIMESTAMP NOT NULL,
                    pattern_data TEXT NOT NULL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit REAL,
                    quality_score INTEGER
                )
            ''')

            # Create indices
            indices = [
                'CREATE INDEX IF NOT EXISTS idx_symbol_status ON signals(symbol, status)',
                'CREATE INDEX IF NOT EXISTS idx_status_detected ON signals(status, detected_at DESC)',
                'CREATE INDEX IF NOT EXISTS idx_symbol_timeframe ON signals(symbol, timeframe)',
            ]

            for idx in indices:
                cursor.execute(idx)

            conn.commit()
            conn.close()

        except Exception as e:
            raise DatabaseError(f"Database initialization failed: {e}") from e

    def create_signal(
        self,
        symbol: str,
        timeframe: str,
        pattern: Dict,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> int:
        """
        Create new signal.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            pattern: Pattern dictionary
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Signal ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            now = datetime.now()

            cursor.execute('''
                INSERT INTO signals (
                    symbol, timeframe, pattern_type, pattern_name, direction,
                    status, detected_at, last_updated, pattern_data,
                    entry_price, stop_loss, take_profit, quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                timeframe,
                pattern.get('pattern_type', 'ABCD'),
                pattern.get('name', 'Unknown'),
                pattern.get('type', 'unknown'),
                'active',
                now,
                now,
                json.dumps(pattern),
                entry_price,
                stop_loss,
                take_profit,
                pattern.get('quality_score', 0)
            ))

            signal_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.logger.info(f"Created signal {signal_id} for {symbol} {pattern.get('name')}")
            return signal_id

        except Exception as e:
            raise DatabaseError(f"Failed to create signal: {e}") from e

    def get_signal(self, signal_id: int) -> Dict:
        """
        Get signal by ID.

        Args:
            signal_id: Signal ID

        Returns:
            Signal dictionary

        Raises:
            SignalNotFoundError: If signal not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM signals WHERE id = ?', (signal_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                raise SignalNotFoundError(f"Signal {signal_id} not found")

            return self._row_to_dict(row, cursor.description)

        except SignalNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get signal: {e}") from e

    def get_active_signals(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None
    ) -> List[Dict]:
        """
        Get active signals.

        Args:
            symbol: Optional symbol filter
            timeframe: Optional timeframe filter

        Returns:
            List of active signals
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = 'SELECT * FROM signals WHERE status = ?'
            params = ['active']

            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)

            if timeframe:
                query += ' AND timeframe = ?'
                params.append(timeframe)

            query += ' ORDER BY detected_at DESC'

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            return [self._row_to_dict(row, cursor.description) for row in rows]

        except Exception as e:
            raise DatabaseError(f"Failed to get active signals: {e}") from e

    def update_signal_status(
        self,
        signal_id: int,
        status: str,
        notes: Optional[str] = None
    ):
        """
        Update signal status.

        Args:
            signal_id: Signal ID
            status: New status ('active', 'completed', 'failed', 'dismissed')
            notes: Optional notes
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE signals
                SET status = ?, last_updated = ?
                WHERE id = ?
            ''', (status, datetime.now(), signal_id))

            if cursor.rowcount == 0:
                raise SignalNotFoundError(f"Signal {signal_id} not found")

            conn.commit()
            conn.close()

            self.logger.info(f"Updated signal {signal_id} status to {status}")

        except SignalNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update signal: {e}") from e

    def get_signals_by_pattern(
        self,
        pattern_name: str,
        direction: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get signals by pattern name.

        Args:
            pattern_name: Pattern name
            direction: Optional direction filter
            limit: Maximum results

        Returns:
            List of signals
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = 'SELECT * FROM signals WHERE pattern_name = ?'
            params = [pattern_name]

            if direction:
                query += ' AND direction = ?'
                params.append(direction)

            query += ' ORDER BY detected_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            return [self._row_to_dict(row, cursor.description) for row in rows]

        except Exception as e:
            raise DatabaseError(f"Failed to get signals: {e}") from e

    def get_signal_statistics(self) -> Dict:
        """
        Get signal statistics.

        Returns:
            Statistics dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Total signals
            cursor.execute('SELECT COUNT(*) FROM signals')
            total = cursor.fetchone()[0]

            # By status
            cursor.execute('SELECT status, COUNT(*) FROM signals GROUP BY status')
            by_status = dict(cursor.fetchall())

            # By pattern
            cursor.execute('SELECT pattern_name, COUNT(*) FROM signals GROUP BY pattern_name')
            by_pattern = dict(cursor.fetchall())

            # By direction
            cursor.execute('SELECT direction, COUNT(*) FROM signals GROUP BY direction')
            by_direction = dict(cursor.fetchall())

            # Average quality score
            cursor.execute('SELECT AVG(quality_score) FROM signals WHERE quality_score IS NOT NULL')
            avg_score = cursor.fetchone()[0] or 0

            conn.close()

            return {
                'total': total,
                'by_status': by_status,
                'by_pattern': by_pattern,
                'by_direction': by_direction,
                'avg_quality_score': avg_score
            }

        except Exception as e:
            raise DatabaseError(f"Failed to get statistics: {e}") from e

    def cleanup_old_signals(self, days: int = 30):
        """
        Remove old signals.

        Args:
            days: Remove signals older than this many days
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days)

            cursor.execute('''
                DELETE FROM signals
                WHERE detected_at < ? AND status NOT IN ('active', 'completed')
            ''', (cutoff_date,))

            deleted = cursor.rowcount
            conn.commit()
            conn.close()

            self.logger.info(f"Cleaned up {deleted} old signals")

        except Exception as e:
            raise DatabaseError(f"Cleanup failed: {e}") from e

    def _row_to_dict(self, row, description) -> Dict:
        """Convert database row to dictionary"""
        if not row:
            return {}

        result = {}
        for idx, col in enumerate(description):
            value = row[idx]

            # Parse JSON pattern data
            if col[0] == 'pattern_data' and value:
                try:
                    value = json.loads(value)
                except:
                    pass

            result[col[0]] = value

        return result


if __name__ == "__main__":
    print("Testing Signal Service...")
    print()

    service = SignalService('test_signals.db')

    # Test create signal
    test_pattern = {
        'name': 'Gartley_bull',
        'type': 'bullish',
        'pattern_type': 'XABCD',
        'quality_score': 75
    }

    signal_id = service.create_signal(
        'BTCUSDT',
        '1h',
        test_pattern,
        entry_price=50000,
        stop_loss=49000,
        take_profit=52000
    )
    print(f"Created signal: {signal_id}")

    # Get active signals
    active = service.get_active_signals()
    print(f"Active signals: {len(active)}")

    # Get statistics
    stats = service.get_signal_statistics()
    print(f"Statistics: {stats}")

    print()
    print("✅ Signal Service ready!")
