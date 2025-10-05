"""
Watchlist Manager for Automatic Chart Updates
==============================================
Tracks all monitored charts and manages automatic updates based on timeframe.
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import threading


class ChartEntry:
    """Represents a single chart in the watchlist"""

    def __init__(self, symbol: str, timeframe: str, file_path: str,
                 last_update: Optional[str] = None, enabled: bool = True):
        self.symbol = symbol.upper()
        self.timeframe = timeframe
        self.file_path = file_path
        self.enabled = enabled

        # Parse last_update or use current time
        if last_update:
            self.last_update = datetime.fromisoformat(last_update)
        else:
            self.last_update = datetime.now()

        # Calculate next update time based on timeframe
        self.next_update = self._calculate_next_update()

    def _calculate_next_update(self) -> datetime:
        """Calculate when this chart should be updated next"""
        import re

        # Parse timeframe (e.g., "1d", "4h", "30m")
        match = re.match(r'^(\d+)([mhdwM])$', self.timeframe)
        if not match:
            # Default to 1 day if can't parse
            return self.last_update + timedelta(days=1)

        value = int(match.group(1))
        unit = match.group(2)

        # Calculate timedelta based on unit
        if unit == 'm':
            delta = timedelta(minutes=value)
        elif unit == 'h':
            delta = timedelta(hours=value)
        elif unit == 'd':
            delta = timedelta(days=value)
        elif unit == 'w':
            delta = timedelta(weeks=value)
        elif unit == 'M':
            # Approximate month as 30 days
            delta = timedelta(days=value * 30)
        else:
            delta = timedelta(days=1)

        return self.last_update + delta

    def needs_update(self) -> bool:
        """Check if this chart needs updating"""
        if not self.enabled:
            return False
        return datetime.now() >= self.next_update

    def mark_updated(self):
        """Mark this chart as just updated"""
        self.last_update = datetime.now()
        self.next_update = self._calculate_next_update()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'last_update': self.last_update.isoformat(),
            'next_update': self.next_update.isoformat(),
            'file_path': self.file_path,
            'enabled': self.enabled
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'ChartEntry':
        """Create ChartEntry from dictionary"""
        return cls(
            symbol=data['symbol'],
            timeframe=data['timeframe'],
            file_path=data['file_path'],
            last_update=data.get('last_update'),
            enabled=data.get('enabled', True)
        )


class WatchlistManager:
    """Manages the watchlist of charts to auto-update"""

    def __init__(self, watchlist_path: str = "data/watchlist.json"):
        self.watchlist_path = watchlist_path
        self.charts: List[ChartEntry] = []
        # REMOVED: self._lock - causing deadlock when called from Qt signals
        # Threading will be handled by calling code

        # Ensure data directory exists
        os.makedirs(os.path.dirname(watchlist_path), exist_ok=True)

        # Load existing watchlist
        self.load()

    def load(self):
        """Load watchlist from JSON file"""
        if os.path.exists(self.watchlist_path):
            try:
                with open(self.watchlist_path, 'r') as f:
                    data = json.load(f)
                    self.charts = [ChartEntry.from_dict(entry) for entry in data.get('charts', [])]
                print(f"Loaded {len(self.charts)} charts from watchlist")
            except Exception as e:
                print(f"Error loading watchlist: {e}")
                self.charts = []
        else:
            self.charts = []

    def save(self):
        """Save watchlist to JSON file (non-blocking)"""
        try:
            data = {
                'charts': [chart.to_dict() for chart in self.charts]
            }
            with open(self.watchlist_path, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"Saved {len(self.charts)} charts to watchlist")
        except Exception as e:
            print(f"Error saving watchlist: {e}")

    def add_chart(self, symbol: str, timeframe: str, file_path: str, enabled: bool = True) -> bool:
        """
        Add or update a chart in the watchlist

        Returns:
            True if added/updated, False if already exists with same settings
        """
        # Check if chart already exists
        existing = self.find_chart(symbol, timeframe)

        if existing:
            # Update existing entry
            existing.file_path = file_path
            existing.enabled = enabled
            existing.mark_updated()
            print(f"Updated watchlist entry: {symbol} {timeframe}")
        else:
            # Add new entry
            new_chart = ChartEntry(symbol, timeframe, file_path, enabled=enabled)
            self.charts.append(new_chart)
            print(f"Added to watchlist: {symbol} {timeframe}")

        self.save()
        return True

    def remove_chart(self, symbol: str, timeframe: str) -> bool:
        """Remove a chart from the watchlist"""
        initial_count = len(self.charts)
        self.charts = [c for c in self.charts
                      if not (c.symbol == symbol.upper() and c.timeframe == timeframe)]

        if len(self.charts) < initial_count:
            self.save()
            print(f"Removed from watchlist: {symbol} {timeframe}")
            return True
        return False

    def find_chart(self, symbol: str, timeframe: str) -> Optional[ChartEntry]:
        """Find a specific chart in the watchlist"""
        symbol = symbol.upper()
        for chart in self.charts:
            if chart.symbol == symbol and chart.timeframe == timeframe:
                return chart
        return None

    def get_charts_needing_update(self) -> List[ChartEntry]:
        """Get list of charts that need updating"""
        return [chart for chart in self.charts if chart.needs_update()]

    def get_all_charts(self) -> List[ChartEntry]:
        """Get all charts in watchlist"""
        return self.charts.copy()

    def enable_chart(self, symbol: str, timeframe: str, enabled: bool = True) -> bool:
        """Enable or disable a chart"""
        chart = self.find_chart(symbol, timeframe)
        if chart:
            chart.enabled = enabled
            self.save()
            return True
        return False

    def get_status_summary(self) -> Dict:
        """Get summary of watchlist status"""
        total = len(self.charts)
        enabled = sum(1 for c in self.charts if c.enabled)
        needs_update = sum(1 for c in self.charts if c.needs_update())

        return {
            'total_charts': total,
            'enabled_charts': enabled,
            'disabled_charts': total - enabled,
            'needs_update': needs_update
        }
