"""
Historical Pattern Database

Tracks all detected patterns for backtesting, analysis, and performance tracking.

Features:
- Pattern storage with full context
- Success/failure outcome tracking
- Performance analytics
- Pattern retrieval and filtering
- Statistical analysis
"""

import sqlite3
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

from exceptions import DatabaseError
from logging_config import get_logger


class PatternHistoryDB:
    """
    Historical pattern database for tracking and analysis.

    Stores all patterns with outcomes for performance tracking.
    """

    def __init__(self, db_path: str = 'data/pattern_history.db'):
        """
        Initialize pattern history database.

        Args:
            db_path: Path to database file
        """
        self.db_path = db_path
        self.logger = get_logger()

        # Ensure data directory exists
        Path(db_path).parent.mkdir(exist_ok=True)

        self._create_tables()

    def _create_tables(self):
        """Create database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Main patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pattern_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_name TEXT NOT NULL,
                direction TEXT NOT NULL,
                detected_at TIMESTAMP NOT NULL,

                -- Pattern data
                pattern_points TEXT NOT NULL,
                pattern_ratios TEXT,
                prz_zone TEXT,
                quality_score INTEGER,

                -- Entry and targets
                entry_price REAL,
                stop_loss REAL,
                take_profit_1 REAL,
                take_profit_2 REAL,

                -- Outcome tracking
                status TEXT DEFAULT 'pending',
                outcome TEXT,
                actual_high REAL,
                actual_low REAL,
                max_profit_pct REAL,
                max_loss_pct REAL,
                exit_price REAL,
                exit_time TIMESTAMP,
                pnl_pct REAL,

                -- Metadata
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Indices for fast queries
        indices = [
            'CREATE INDEX IF NOT EXISTS idx_symbol_tf ON pattern_history(symbol, timeframe)',
            'CREATE INDEX IF NOT EXISTS idx_pattern_name ON pattern_history(pattern_name)',
            'CREATE INDEX IF NOT EXISTS idx_detected_at ON pattern_history(detected_at DESC)',
            'CREATE INDEX IF NOT EXISTS idx_outcome ON pattern_history(outcome)',
            'CREATE INDEX IF NOT EXISTS idx_status ON pattern_history(status)',
            'CREATE INDEX IF NOT EXISTS idx_direction ON pattern_history(direction)',
        ]

        for idx in indices:
            cursor.execute(idx)

        # Pattern statistics view
        cursor.execute('''
            CREATE VIEW IF NOT EXISTS pattern_statistics AS
            SELECT
                pattern_name,
                direction,
                COUNT(*) as total_patterns,
                COUNT(CASE WHEN outcome = 'success' THEN 1 END) as successful,
                COUNT(CASE WHEN outcome = 'failed' THEN 1 END) as failed,
                ROUND(AVG(CASE WHEN outcome = 'success' THEN 1.0 ELSE 0.0 END) * 100, 2) as success_rate,
                ROUND(AVG(pnl_pct), 2) as avg_pnl_pct,
                ROUND(AVG(quality_score), 1) as avg_quality_score,
                ROUND(AVG(max_profit_pct), 2) as avg_max_profit,
                ROUND(AVG(ABS(max_loss_pct)), 2) as avg_max_loss
            FROM pattern_history
            WHERE outcome IS NOT NULL
            GROUP BY pattern_name, direction
        ''')

        conn.commit()
        conn.close()

        self.logger.info("Pattern history database initialized")

    def store_pattern(
        self,
        symbol: str,
        timeframe: str,
        pattern: Dict,
        entry_price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit_1: Optional[float] = None,
        take_profit_2: Optional[float] = None
    ) -> int:
        """
        Store pattern in history.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            pattern: Pattern dictionary
            entry_price: Entry price
            stop_loss: Stop loss
            take_profit_1: First take profit
            take_profit_2: Second take profit

        Returns:
            Pattern ID
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO pattern_history (
                    symbol, timeframe, pattern_type, pattern_name, direction,
                    detected_at, pattern_points, pattern_ratios, prz_zone,
                    quality_score, entry_price, stop_loss, take_profit_1, take_profit_2
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                symbol,
                timeframe,
                pattern.get('pattern_type', 'ABCD'),
                pattern.get('name', 'Unknown'),
                pattern.get('type', 'unknown'),
                pattern.get('detected_at', datetime.now()),
                json.dumps(pattern.get('points', {})),
                json.dumps(pattern.get('ratios', {})),
                json.dumps(pattern.get('prz_zone', {})),
                pattern.get('quality_score', 0),
                entry_price,
                stop_loss,
                take_profit_1,
                take_profit_2
            ))

            pattern_id = cursor.lastrowid
            conn.commit()
            conn.close()

            self.logger.info(f"Stored pattern {pattern_id}: {pattern.get('name')}")
            return pattern_id

        except Exception as e:
            raise DatabaseError(f"Failed to store pattern: {e}") from e

    def update_pattern_outcome(
        self,
        pattern_id: int,
        outcome: str,
        actual_high: Optional[float] = None,
        actual_low: Optional[float] = None,
        exit_price: Optional[float] = None,
        notes: Optional[str] = None
    ):
        """
        Update pattern outcome.

        Args:
            pattern_id: Pattern ID
            outcome: Outcome ('success', 'failed', 'neutral')
            actual_high: Highest price reached
            actual_low: Lowest price reached
            exit_price: Exit price
            notes: Optional notes
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get pattern data
            cursor.execute('''
                SELECT entry_price, stop_loss, take_profit_1
                FROM pattern_history WHERE id = ?
            ''', (pattern_id,))

            row = cursor.fetchone()
            if not row:
                raise DatabaseError(f"Pattern {pattern_id} not found")

            entry_price, stop_loss, take_profit_1 = row

            # Calculate metrics
            max_profit_pct = None
            max_loss_pct = None
            pnl_pct = None

            if entry_price and actual_high and actual_low:
                max_profit_pct = ((actual_high - entry_price) / entry_price) * 100
                max_loss_pct = ((actual_low - entry_price) / entry_price) * 100

            if entry_price and exit_price:
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100

            # Update
            cursor.execute('''
                UPDATE pattern_history SET
                    outcome = ?,
                    actual_high = ?,
                    actual_low = ?,
                    max_profit_pct = ?,
                    max_loss_pct = ?,
                    exit_price = ?,
                    exit_time = ?,
                    pnl_pct = ?,
                    notes = ?,
                    updated_at = ?,
                    status = 'closed'
                WHERE id = ?
            ''', (
                outcome,
                actual_high,
                actual_low,
                max_profit_pct,
                max_loss_pct,
                exit_price,
                datetime.now(),
                pnl_pct,
                notes,
                datetime.now(),
                pattern_id
            ))

            conn.commit()
            conn.close()

            self.logger.info(f"Updated pattern {pattern_id} outcome: {outcome}")

        except Exception as e:
            raise DatabaseError(f"Failed to update outcome: {e}") from e

    def get_pattern_statistics(
        self,
        pattern_name: Optional[str] = None,
        direction: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[Dict]:
        """
        Get pattern performance statistics.

        Args:
            pattern_name: Optional pattern name filter
            direction: Optional direction filter
            symbol: Optional symbol filter

        Returns:
            List of statistics dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            query = 'SELECT * FROM pattern_statistics WHERE 1=1'
            params = []

            if pattern_name:
                query += ' AND pattern_name = ?'
                params.append(pattern_name)

            if direction:
                query += ' AND direction = ?'
                params.append(direction)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            # Convert to dictionaries
            results = []
            for row in rows:
                results.append({
                    'pattern_name': row[0],
                    'direction': row[1],
                    'total_patterns': row[2],
                    'successful': row[3],
                    'failed': row[4],
                    'success_rate': row[5],
                    'avg_pnl_pct': row[6],
                    'avg_quality_score': row[7],
                    'avg_max_profit': row[8],
                    'avg_max_loss': row[9]
                })

            conn.close()
            return results

        except Exception as e:
            raise DatabaseError(f"Failed to get statistics: {e}") from e

    def get_best_patterns(self, min_samples: int = 10, limit: int = 10) -> List[Dict]:
        """
        Get best performing patterns.

        Args:
            min_samples: Minimum number of samples required
            limit: Maximum results

        Returns:
            List of best patterns
        """
        stats = self.get_pattern_statistics()

        # Filter by minimum samples
        stats = [s for s in stats if s['total_patterns'] >= min_samples]

        # Sort by success rate then average PnL
        stats.sort(
            key=lambda s: (s['success_rate'], s['avg_pnl_pct']),
            reverse=True
        )

        return stats[:limit]

    def get_recent_patterns(
        self,
        days: int = 30,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get recent patterns.

        Args:
            days: Number of days to look back
            symbol: Optional symbol filter
            limit: Maximum results

        Returns:
            List of recent patterns
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_date = datetime.now() - timedelta(days=days)

            query = '''
                SELECT * FROM pattern_history
                WHERE detected_at >= ?
            '''
            params = [cutoff_date]

            if symbol:
                query += ' AND symbol = ?'
                params.append(symbol)

            query += ' ORDER BY detected_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            # Convert to dictionaries
            return [self._row_to_dict(row, cursor.description) for row in rows]

        except Exception as e:
            raise DatabaseError(f"Failed to get recent patterns: {e}") from e

    def analyze_pattern_quality(self) -> Dict:
        """
        Analyze relationship between quality score and success.

        Returns:
            Analysis dictionary
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Group by quality score ranges
            cursor.execute('''
                SELECT
                    CASE
                        WHEN quality_score >= 80 THEN '80-100'
                        WHEN quality_score >= 60 THEN '60-79'
                        WHEN quality_score >= 40 THEN '40-59'
                        ELSE '0-39'
                    END as score_range,
                    COUNT(*) as total,
                    ROUND(AVG(CASE WHEN outcome = 'success' THEN 1.0 ELSE 0.0 END) * 100, 2) as success_rate,
                    ROUND(AVG(pnl_pct), 2) as avg_pnl
                FROM pattern_history
                WHERE outcome IS NOT NULL
                GROUP BY score_range
                ORDER BY score_range DESC
            ''')

            rows = cursor.fetchall()
            conn.close()

            return {
                'score_ranges': [
                    {
                        'range': row[0],
                        'total': row[1],
                        'success_rate': row[2],
                        'avg_pnl': row[3]
                    }
                    for row in rows
                ]
            }

        except Exception as e:
            raise DatabaseError(f"Analysis failed: {e}") from e

    def _row_to_dict(self, row, description) -> Dict:
        """Convert database row to dictionary"""
        if not row:
            return {}

        result = {}
        for idx, col in enumerate(description):
            value = row[idx]

            # Parse JSON fields
            if col[0] in ('pattern_points', 'pattern_ratios', 'prz_zone') and value:
                try:
                    value = json.loads(value)
                except:
                    pass

            result[col[0]] = value

        return result


if __name__ == "__main__":
    print("Testing Pattern History Database...")
    print()

    db = PatternHistoryDB('test_pattern_history.db')

    # Store test pattern
    test_pattern = {
        'name': 'Gartley_bull',
        'type': 'bullish',
        'pattern_type': 'XABCD',
        'quality_score': 75,
        'points': {'A': {'price': 100}, 'B': {'price': 95}},
        'ratios': {'bc_retracement': 61.8},
        'prz_zone': {'low': 96, 'high': 97}
    }

    pattern_id = db.store_pattern(
        'BTCUSDT',
        '1h',
        test_pattern,
        entry_price=96.5,
        stop_loss=94.0,
        take_profit_1=100.0
    )
    print(f"Stored pattern: {pattern_id}")

    # Update outcome
    db.update_pattern_outcome(
        pattern_id,
        outcome='success',
        actual_high=101.0,
        actual_low=96.0,
        exit_price=100.0
    )
    print("Updated outcome")

    # Get statistics
    stats = db.get_pattern_statistics()
    print(f"Statistics: {stats}")

    # Analyze quality
    quality_analysis = db.analyze_pattern_quality()
    print(f"Quality analysis: {quality_analysis}")

    print()
    print("✅ Pattern History Database ready!")
