"""
Update History Logger
=====================
Tracks all auto-update attempts with success/failure status and error messages.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class UpdateRecord:
    """Represents a single update attempt"""
    timestamp: str
    symbol: str
    timeframe: str
    status: str  # 'success', 'failed', 'retrying'
    candles_updated: int
    error_message: Optional[str] = None
    retry_attempt: int = 0

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'UpdateRecord':
        """Create UpdateRecord from dictionary"""
        return cls(**data)


class UpdateHistoryLogger:
    """Manages update history with persistence"""

    def __init__(self, history_path: str = "data/update_history.json", max_records: int = 1000):
        """
        Initialize the update history logger

        Args:
            history_path: Path to history JSON file
            max_records: Maximum number of records to keep (oldest deleted first)
        """
        self.history_path = history_path
        self.max_records = max_records
        self.records: List[UpdateRecord] = []

        # Ensure data directory exists
        os.makedirs(os.path.dirname(history_path), exist_ok=True)

        # Load existing history
        self.load()

    def load(self):
        """Load history from JSON file"""
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, 'r') as f:
                    data = json.load(f)
                    self.records = [UpdateRecord.from_dict(record) for record in data.get('records', [])]
                print(f"Loaded {len(self.records)} update records from history")
            except Exception as e:
                print(f"Error loading update history: {e}")
                self.records = []
        else:
            self.records = []

    def save(self):
        """Save history to JSON file"""
        try:
            # Limit records to max_records
            if len(self.records) > self.max_records:
                self.records = self.records[-self.max_records:]

            data = {
                'records': [record.to_dict() for record in self.records],
                'total_records': len(self.records),
                'last_updated': datetime.now().isoformat()
            }

            with open(self.history_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving update history: {e}")

    def log_success(self, symbol: str, timeframe: str, candles_updated: int):
        """Log a successful update"""
        record = UpdateRecord(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            timeframe=timeframe,
            status='success',
            candles_updated=candles_updated,
            error_message=None,
            retry_attempt=0
        )
        self.records.append(record)
        self.save()
        print(f"Logged success: {symbol} {timeframe} ({candles_updated} candles)")

    def log_failure(self, symbol: str, timeframe: str, error_message: str, retry_attempt: int = 0):
        """Log a failed update"""
        record = UpdateRecord(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            timeframe=timeframe,
            status='failed',
            candles_updated=0,
            error_message=error_message,
            retry_attempt=retry_attempt
        )
        self.records.append(record)
        self.save()
        print(f"Logged failure: {symbol} {timeframe} - {error_message}")

    def log_retry(self, symbol: str, timeframe: str, retry_attempt: int, error_message: str):
        """Log a retry attempt"""
        record = UpdateRecord(
            timestamp=datetime.now().isoformat(),
            symbol=symbol,
            timeframe=timeframe,
            status='retrying',
            candles_updated=0,
            error_message=error_message,
            retry_attempt=retry_attempt
        )
        self.records.append(record)
        self.save()
        print(f"Logged retry: {symbol} {timeframe} (attempt {retry_attempt})")

    def get_recent_records(self, limit: int = 50) -> List[UpdateRecord]:
        """Get most recent update records"""
        return self.records[-limit:]

    def get_records_by_symbol(self, symbol: str, timeframe: str, limit: int = 20) -> List[UpdateRecord]:
        """Get update records for a specific chart"""
        matching = [r for r in self.records
                   if r.symbol == symbol.upper() and r.timeframe == timeframe]
        return matching[-limit:]

    def get_failed_records(self, limit: int = 50) -> List[UpdateRecord]:
        """Get recent failed update attempts"""
        failed = [r for r in self.records if r.status == 'failed']
        return failed[-limit:]

    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        total = len(self.records)
        if total == 0:
            return {
                'total_updates': 0,
                'successful': 0,
                'failed': 0,
                'success_rate': 0.0,
                'total_candles_updated': 0
            }

        successful = sum(1 for r in self.records if r.status == 'success')
        failed = sum(1 for r in self.records if r.status == 'failed')
        total_candles = sum(r.candles_updated for r in self.records if r.status == 'success')

        return {
            'total_updates': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0.0,
            'total_candles_updated': total_candles
        }

    def get_chart_statistics(self, symbol: str, timeframe: str) -> Dict:
        """Get statistics for a specific chart"""
        records = self.get_records_by_symbol(symbol, timeframe, limit=None)

        if not records:
            return {
                'total_updates': 0,
                'successful': 0,
                'failed': 0,
                'last_update': None,
                'last_success': None,
                'last_failure': None
            }

        successful = [r for r in records if r.status == 'success']
        failed = [r for r in records if r.status == 'failed']

        return {
            'total_updates': len(records),
            'successful': len(successful),
            'failed': len(failed),
            'last_update': records[-1].timestamp if records else None,
            'last_success': successful[-1].timestamp if successful else None,
            'last_failure': failed[-1].timestamp if failed else None,
            'total_candles': sum(r.candles_updated for r in successful)
        }

    def clear_old_records(self, days_to_keep: int = 30):
        """Clear records older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)

        self.records = [r for r in self.records
                       if datetime.fromisoformat(r.timestamp) > cutoff_date]
        self.save()
        print(f"Cleared records older than {days_to_keep} days")

    def clear_all(self):
        """Clear all history records"""
        self.records = []
        self.save()
        print("Cleared all update history")


# Import for date operations
from datetime import timedelta
