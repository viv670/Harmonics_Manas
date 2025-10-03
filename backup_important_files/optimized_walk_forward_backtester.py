"""
Optimized Walk-Forward Harmonic Pattern Backtesting System
===========================================================
Improved performance with caching and efficient pattern detection.
Uses unformed patterns for entry signals and tracks their completion.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any, Set
from datetime import datetime
import json
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# Import pattern detection modules
from unformed_abcd import detect_strict_unformed_abcd_patterns as detect_unformed_abcd_patterns
from unformed_xabcd import detect_strict_unformed_xabcd_patterns
from gui_compatible_detection import detect_all_gui_patterns
from extremum import detect_extremum_points as find_extremum_points
from pattern_tracking_utils import PatternTracker, TrackedPattern


class TradeDirection(Enum):
    """Trade direction based on pattern type"""
    LONG = "long"
    SHORT = "short"


@dataclass
class PatternSignal:
    """Represents a potential trading signal from an unformed pattern"""
    timestamp: pd.Timestamp
    pattern_type: str  # ABCD or XABCD
    pattern_name: str  # Gartley, Bat, Butterfly, etc.
    direction: TradeDirection
    prz_levels: List[float]  # Potential reversal zone levels
    entry_price: float  # Suggested entry price
    stop_loss: float  # Stop loss level
    take_profit_1: float  # First target
    take_profit_2: float  # Second target
    confidence_score: float  # Pattern quality score
    pattern_data: Dict  # Complete pattern information
    pattern_hash: str = ""  # Unique identifier for pattern


@dataclass
class TradeResult:
    """Stores the result of a completed trade"""
    signal: PatternSignal
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_percent: float = 0.0
    max_favorable_excursion: float = 0.0
    max_adverse_excursion: float = 0.0
    trade_duration_bars: int = 0
    pattern_completed: bool = False  # Did unformed pattern complete to formed?
    exit_reason: str = ""  # stop_loss, take_profit, time_exit, etc.


@dataclass
class FibonacciLevelTouch:
    """Records a single touch of a Fibonacci or harmonic level"""
    level_name: str  # e.g., "Fib_50%", "A_Level"
    level_price: float
    absolute_bar: int  # Bars since D formation
    incremental_bar: int  # Bars since previous touch
    touch_type: str  # "high", "low", or "whipsaw"


@dataclass
class FormedPatternFibAnalysis:
    """Tracks Fibonacci and harmonic level touches for a single formed pattern"""
    pattern_id: str
    pattern_type: str  # ABCD or XABCD
    pattern_name: str  # Gartley, Bat, etc.
    direction: str  # bullish or bearish
    detection_bar: int  # Bar index when D was formed
    d_price: float

    # Fibonacci levels (price values)
    fib_levels: Dict[str, float] = field(default_factory=dict)  # {"Fib_0%": price, ...}

    # Harmonic structure levels (price values)
    harmonic_levels: Dict[str, float] = field(default_factory=dict)  # {"X_Level": price, ...}

    # PRZ information
    prz_min: float = 0.0
    prz_max: float = 0.0
    prz_broken_bar: Optional[int] = None  # Bar when PRZ was broken

    # Touch tracking
    touches: List[FibonacciLevelTouch] = field(default_factory=list)
    last_touch_bar: int = 0  # Track last touch for incremental calculation

    # Summary statistics
    total_bars_tracked: int = 0
    is_tracking_complete: bool = False


@dataclass
class BacktestStatistics:
    """Comprehensive backtest performance metrics"""
    total_signals: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0
    pattern_completion_rate: float = 0.0
    patterns_detected: int = 0  # Total unique patterns found
    patterns_traded: int = 0    # Patterns that resulted in trades
    total_unformed_patterns: int = 0  # Total unformed patterns encountered
    total_formed_patterns: int = 0    # Total formed patterns encountered

    # Extremum statistics
    total_extremum_points: int = 0  # Total extremum points detected
    high_extremum_points: int = 0   # Number of high extremums
    low_extremum_points: int = 0    # Number of low extremums

    # Pattern tracking statistics
    patterns_tracked: int = 0  # Patterns tracked from unformed to completion
    patterns_completed: int = 0  # Unformed patterns that completed (legacy)
    patterns_failed: int = 0  # Unformed patterns that failed (zone violated)
    patterns_expired: int = 0  # Unformed patterns that expired (legacy)
    patterns_success: int = 0  # Patterns that entered zone and reversed
    patterns_dismissed: int = 0  # Patterns dismissed due to structure break
    patterns_pending: int = 0  # Patterns still pending at end
    patterns_in_zone: int = 0  # Patterns currently in PRZ zone
    patterns_success_rate: float = 0.0  # Success rate among concluded patterns
    avg_projection_accuracy: float = 0.0  # How accurate were D projections
    pattern_type_completion_rates: Dict[str, float] = field(default_factory=dict)

    # Pattern-specific stats
    pattern_performance: Dict[str, Dict] = field(default_factory=dict)
    # Time-based analysis
    monthly_returns: List[float] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    time_taken: float = 0.0  # Total time taken for backtest in seconds

    # Tracking warnings
    tracking_warnings: List[str] = field(default_factory=list)

    # Fibonacci analysis for formed patterns
    fibonacci_analysis: List[FormedPatternFibAnalysis] = field(default_factory=list)


class OptimizedWalkForwardBacktester:
    """
    Optimized walk-forward backtesting engine for harmonic patterns.
    Features caching and efficient pattern detection to improve performance.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        initial_capital: float = 10000,
        position_size: float = 0.02,  # 2% risk per trade
        lookback_window: int = 100,  # Not used anymore, kept for compatibility
        future_buffer: int = 5,  # Bars to leave as buffer (avoid look-ahead)
        min_pattern_score: float = 0.7,  # Minimum confidence score to trade
        max_open_trades: int = 5,  # Maximum concurrent trades
        detection_interval: int = 10,  # Detect patterns every N bars for efficiency
        extremum_length: int = 1  # Length for extremum detection (1 matches GUI default)
    ):
        """
        Initialize the optimized backtester.

        Args:
            data: DataFrame with OHLCV data
            initial_capital: Starting capital
            position_size: Risk per trade as fraction of capital
            lookback_window: Kept for compatibility (not used)
            future_buffer: Bars to exclude from current time (prevent bias)
            min_pattern_score: Minimum pattern quality score to generate signal
            max_open_trades: Maximum number of concurrent open trades
            detection_interval: Run pattern detection every N bars (optimization)
        """
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.future_buffer = future_buffer
        self.min_pattern_score = min_pattern_score
        self.max_open_trades = max_open_trades
        self.detection_interval = detection_interval
        self.extremum_length = extremum_length  # Store extremum detection length

        # Trading state
        self.current_capital = initial_capital
        self.open_trades: List[TradeResult] = []
        self.closed_trades: List[TradeResult] = []
        self.all_signals: List[PatternSignal] = []

        # Performance tracking
        self.equity_curve = [initial_capital]
        self.drawdown_curve = []

        # Extremum tracking - will be counted from full dataset at the end
        self.total_extremum_points = 0
        self.high_extremum_points = 0
        self.low_extremum_points = 0
        self.current_extremum_points = []  # Current extremum points for C updates

        # OPTIMIZATION: Pattern caching
        self.cached_patterns = {
            'unformed': {},  # idx -> patterns
            'formed': {},    # idx -> patterns
            'extremums': {}  # idx -> extremums
        }
        self.last_detection_idx = -1
        self.traded_patterns: Set[str] = set()  # Track patterns we've already traded
        self.pattern_cache: Set[str] = set()  # Track all unique patterns seen

        # Initialize pattern tracker for completion analysis
        self.pattern_tracker = PatternTracker()

        # Fibonacci analysis tracking for formed patterns
        self.fibonacci_trackers: Dict[str, FormedPatternFibAnalysis] = {}  # pattern_id -> tracker
        self.active_fibonacci_tracking: Set[str] = set()  # Pattern IDs currently being tracked

    def calculate_fibonacci_levels_for_formed_pattern(self, pattern: Dict) -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels for a formed pattern.

        Returns dict with level names as keys and prices as values.
        """
        points = pattern.get('points', {})
        if 'A' not in points or 'C' not in points or 'D' not in points:
            return {}

        # Get prices
        a_price = points['A'].get('price', 0)
        c_price = points['C'].get('price', 0)
        d_price = points['D'].get('price', 0)

        # Determine if bullish or bearish
        is_bullish = 'bull' in pattern.get('name', '').lower()

        # For bullish: From highest formation point (A or C) down to D
        # For bearish: From lowest formation point (A or C) up to D
        if is_bullish:
            start_price = max(a_price, c_price)
        else:
            start_price = min(a_price, c_price)

        end_price = d_price
        price_range = end_price - start_price

        # Calculate Fibonacci levels (including extensions)
        fib_percentages = [0, 23.6, 38.2, 50, 61.8, 78.6, 88.6, 100, 112.8, 127.2, 141.4, 161.8]
        fib_levels = {}

        for pct in fib_percentages:
            level_price = start_price + (price_range * pct / 100.0)
            fib_levels[f"Fib_{pct}%"] = level_price

        return fib_levels

    def get_harmonic_structure_levels(self, pattern: Dict) -> Dict[str, float]:
        """
        Extract harmonic structure levels (X, A, B, C points) for tracking.

        Returns dict with level names as keys and prices as values.
        """
        points = pattern.get('points', {})
        harmonic_levels = {}

        # For XABCD patterns, track X, A, B, C
        # For ABCD patterns, track A, B, C
        pattern_type = pattern.get('pattern_type', 'ABCD')

        if pattern_type == 'XABCD' and 'X' in points:
            harmonic_levels['X_Level'] = points['X'].get('price', 0)

        if 'A' in points:
            harmonic_levels['A_Level'] = points['A'].get('price', 0)

        if 'B' in points:
            harmonic_levels['B_Level'] = points['B'].get('price', 0)

        if 'C' in points:
            harmonic_levels['C_Level'] = points['C'].get('price', 0)

        return harmonic_levels

    def get_prz_zone(self, pattern: Dict) -> Tuple[float, float]:
        """
        Extract PRZ zone min/max from pattern.

        Returns (prz_min, prz_max) tuple.
        """
        # Try to get PRZ from pattern ratios or prz_zones
        if 'ratios' in pattern and 'prz_zones' in pattern['ratios']:
            prz_zones = pattern['ratios']['prz_zones']
            if isinstance(prz_zones, list) and len(prz_zones) > 0:
                first_zone = prz_zones[0]
                if isinstance(first_zone, dict):
                    return (first_zone.get('min', 0), first_zone.get('max', 0))

        # Fallback: calculate from D point with small tolerance
        points = pattern.get('points', {})
        if 'D' in points:
            d_price = points['D'].get('price', 0)
            tolerance = d_price * 0.01  # 1% tolerance
            return (d_price - tolerance, d_price + tolerance)

        return (0, 0)

    def initialize_fibonacci_tracking(self, pattern: Dict, detection_bar: int):
        """
        Initialize Fibonacci tracking for a newly detected formed pattern.
        """
        # Use pattern_tracker's ID generation for consistency
        pattern_id = self.pattern_tracker.generate_pattern_id(pattern)

        # Skip if already tracking
        if pattern_id in self.fibonacci_trackers:
            # Silently skip - this is normal behavior
            return

        # Calculate Fibonacci levels
        fib_levels = self.calculate_fibonacci_levels_for_formed_pattern(pattern)
        if not fib_levels:
            return  # Can't track without valid levels

        # Get harmonic structure levels
        harmonic_levels = self.get_harmonic_structure_levels(pattern)

        # Get PRZ zone
        prz_min, prz_max = self.get_prz_zone(pattern)

        # Get D price
        points = pattern.get('points', {})
        d_price = points.get('D', {}).get('price', 0) if 'D' in points else 0

        # Determine direction
        is_bullish = 'bull' in pattern.get('name', '').lower()
        direction = 'bullish' if is_bullish else 'bearish'

        # Create tracker
        tracker = FormedPatternFibAnalysis(
            pattern_id=pattern_id,
            pattern_type=pattern.get('pattern_type', 'ABCD'),
            pattern_name=pattern.get('name', 'unknown'),
            direction=direction,
            detection_bar=detection_bar,
            d_price=d_price,
            fib_levels=fib_levels,
            harmonic_levels=harmonic_levels,
            prz_min=prz_min,
            prz_max=prz_max
        )

        self.fibonacci_trackers[pattern_id] = tracker
        self.active_fibonacci_tracking.add(pattern_id)

        # Get indices for debugging
        points = pattern.get('points', {})
        indices_dict = pattern.get('indices', {})
        a_idx = indices_dict.get('A', points.get('A', {}).get('index', '?'))
        b_idx = indices_dict.get('B', points.get('B', {}).get('index', '?'))
        c_idx = indices_dict.get('C', points.get('C', {}).get('index', '?'))

        print(f"FIB TRACKING #{len(self.fibonacci_trackers)}: {pattern.get('name', 'unknown')} @ bar {detection_bar}")
        print(f"  Indices: A:{a_idx} B:{b_idx} C:{c_idx}")
        print(f"  ID: {pattern_id}")
        print(f"  Already tracking: {list(self.fibonacci_trackers.keys())}")

    def update_fibonacci_tracking(self, current_bar: pd.Series, current_idx: int):
        """
        Update Fibonacci tracking for all active patterns.
        Check for level touches, PRZ breaks, and D point crossing.
        """
        if not self.active_fibonacci_tracking:
            return

        patterns_to_remove = set()

        for pattern_id in list(self.active_fibonacci_tracking):
            tracker = self.fibonacci_trackers[pattern_id]

            # Calculate bars since D formation
            bars_since_d = current_idx - tracker.detection_bar

            # Check if D point is crossed (price crosses D point after formation)
            is_bullish = tracker.direction == 'bullish'
            d_point_crossed = False

            if is_bullish:
                # For bullish, D point crossed if price goes below D point
                if current_bar['Low'] < tracker.d_price:
                    d_point_crossed = True
            else:
                # For bearish, D point crossed if price goes above D point
                if current_bar['High'] > tracker.d_price:
                    d_point_crossed = True

            if d_point_crossed:
                # Mark pattern as invalid due to D point crossing
                # Update the pattern in tracker to mark as dismissed
                if pattern_id in self.pattern_tracker.tracked_patterns:
                    tracked_pattern = self.pattern_tracker.tracked_patterns[pattern_id]
                    if tracked_pattern.status not in ['dismissed', 'failed']:
                        tracked_pattern.status = 'dismissed'
                        tracked_pattern.dismissal_reason = 'D_point_crossed'
                        tracked_pattern.dismissal_bar = current_idx
                        print(f"DEBUG: D point crossed for {pattern_id[:20]}... at bar {current_idx}, pattern invalidated")

                tracker.total_bars_tracked = bars_since_d
                tracker.is_tracking_complete = True
                patterns_to_remove.add(pattern_id)
                continue

            # Check if PRZ is broken (price beyond PRZ zone)
            prz_broken = False

            if is_bullish:
                # For bullish, PRZ broken if price goes below PRZ min
                if current_bar['Low'] < tracker.prz_min:
                    prz_broken = True
            else:
                # For bearish, PRZ broken if price goes above PRZ max
                if current_bar['High'] > tracker.prz_max:
                    prz_broken = True

            if prz_broken:
                tracker.prz_broken_bar = current_idx
                tracker.total_bars_tracked = bars_since_d
                tracker.is_tracking_complete = True
                patterns_to_remove.add(pattern_id)
                print(f"DEBUG: PRZ broken for {pattern_id[:20]}... at bar {current_idx}, tracked {bars_since_d} bars")
                continue

            # Check all Fibonacci levels for touches
            all_levels = {**tracker.fib_levels, **tracker.harmonic_levels}

            for level_name, level_price in all_levels.items():
                # Check if current bar touches this level
                high = current_bar['High']
                low = current_bar['Low']

                # A touch means the bar's high/low range CROSSES the level
                # i.e., low <= level <= high
                touched = low <= level_price <= high

                if not touched:
                    continue

                # Determine touch type
                close_price = current_bar['Close']
                open_price = current_bar['Open']

                # Check if close/open crossed the level (whipsaw)
                if (open_price <= level_price <= close_price) or (close_price <= level_price <= open_price):
                    touch_type = "body"  # Body crossed the level
                elif abs(high - level_price) < abs(low - level_price):
                    touch_type = "high"  # Touched at high
                else:
                    touch_type = "low"   # Touched at low

                # Calculate incremental bar count from detection (not last touch)
                incremental_bar = bars_since_d

                # Add touch
                touch = FibonacciLevelTouch(
                    level_name=level_name,
                    level_price=level_price,
                    absolute_bar=current_idx,
                    incremental_bar=incremental_bar,
                    touch_type=touch_type
                )
                tracker.touches.append(touch)

                # Update last touch bar for this specific level
                tracker.last_touch_bar = current_idx

        # Remove completed patterns from active tracking
        for pattern_id in patterns_to_remove:
            self.active_fibonacci_tracking.discard(pattern_id)

    def get_fibonacci_summary_statistics(self) -> Dict:
        """
        Aggregate Fibonacci analysis statistics across all tracked patterns.
        Returns summary statistics for display.
        """
        if not self.fibonacci_trackers:
            return {}

        # Collect all trackers (both active and completed)
        # EXCLUDE patterns where PRZ was broken (D point ended outside PRZ)
        # Only include patterns where price stayed in PRZ or is still being tracked
        all_trackers = [
            tracker for tracker in self.fibonacci_trackers.values()
            if tracker.prz_broken_bar is None  # PRZ not broken
        ]

        if not all_trackers:
            return {}

        # Initialize aggregation structures
        level_stats = {}  # level_name -> {touches: [], first_touch_bars: [], intervals: []}
        pattern_type_stats = {}  # pattern_type -> level_stats

        # Process each pattern
        for tracker in all_trackers:
            pattern_type = tracker.pattern_type

            # Initialize pattern type stats if needed
            if pattern_type not in pattern_type_stats:
                pattern_type_stats[pattern_type] = {}

            # Group touches by level
            touches_by_level = {}
            for touch in tracker.touches:
                level_name = touch.level_name
                if level_name not in touches_by_level:
                    touches_by_level[level_name] = []
                touches_by_level[level_name].append(touch)

            # Aggregate stats for each level
            all_levels = list(tracker.fib_levels.keys()) + list(tracker.harmonic_levels.keys())
            for level_name in all_levels:
                # Overall stats
                if level_name not in level_stats:
                    level_stats[level_name] = {
                        'touch_counts': [],
                        'first_touch_bars': [],
                        'avg_intervals': []
                    }

                # Pattern type specific stats
                if level_name not in pattern_type_stats[pattern_type]:
                    pattern_type_stats[pattern_type][level_name] = {
                        'touch_counts': [],
                        'first_touch_bars': [],
                        'avg_intervals': []
                    }

                # Calculate stats for this pattern's level
                level_touches = touches_by_level.get(level_name, [])
                touch_count = len(level_touches)

                # Add to overall stats
                level_stats[level_name]['touch_counts'].append(touch_count)

                # Add to pattern type stats
                pattern_type_stats[pattern_type][level_name]['touch_counts'].append(touch_count)

                if level_touches:
                    # First touch bar
                    first_touch_bar = level_touches[0].absolute_bar
                    level_stats[level_name]['first_touch_bars'].append(first_touch_bar)
                    pattern_type_stats[pattern_type][level_name]['first_touch_bars'].append(first_touch_bar)

                    # Average interval between touches
                    if len(level_touches) > 1:
                        intervals = [t.incremental_bar for t in level_touches[1:]]
                        avg_interval = sum(intervals) / len(intervals)
                        level_stats[level_name]['avg_intervals'].append(avg_interval)
                        pattern_type_stats[pattern_type][level_name]['avg_intervals'].append(avg_interval)

        # Calculate final averages
        summary = {
            'total_patterns_analyzed': len(all_trackers),
            'abcd_count': len([t for t in all_trackers if t.pattern_type == 'ABCD']),
            'xabcd_count': len([t for t in all_trackers if t.pattern_type == 'XABCD']),
            'patterns_completed': len([t for t in all_trackers if t.is_tracking_complete]),
            'patterns_active': len([t for t in all_trackers if not t.is_tracking_complete]),
            'overall_stats': {},
            'pattern_type_breakdown': {},
            'individual_patterns': []  # For Option C - individual pattern details
        }

        # Overall level statistics
        for level_name, stats in level_stats.items():
            total_touches = sum(stats['touch_counts'])
            avg_touches = total_touches / len(stats['touch_counts']) if stats['touch_counts'] else 0

            summary['overall_stats'][level_name] = {
                'avg_touches': avg_touches,
                'total_touches': total_touches,
                'avg_first_touch_bar': sum(stats['first_touch_bars']) / len(stats['first_touch_bars']) if stats['first_touch_bars'] else 0,
                'avg_interval': sum(stats['avg_intervals']) / len(stats['avg_intervals']) if stats['avg_intervals'] else 0,
                'patterns_touched': len([c for c in stats['touch_counts'] if c > 0])
            }

        # Pattern type breakdown
        for pattern_type, type_level_stats in pattern_type_stats.items():
            summary['pattern_type_breakdown'][pattern_type] = {}
            for level_name, stats in type_level_stats.items():
                summary['pattern_type_breakdown'][pattern_type][level_name] = {
                    'avg_touches': sum(stats['touch_counts']) / len(stats['touch_counts']) if stats['touch_counts'] else 0,
                    'avg_first_touch_bar': sum(stats['first_touch_bars']) / len(stats['first_touch_bars']) if stats['first_touch_bars'] else 0,
                    'avg_interval': sum(stats['avg_intervals']) / len(stats['avg_intervals']) if stats['avg_intervals'] else 0
                }

        # Individual pattern details (Option C)
        for tracker in all_trackers:
            # Group touches by level for this pattern
            touches_by_level = {}
            for touch in tracker.touches:
                level_name = touch.level_name
                if level_name not in touches_by_level:
                    touches_by_level[level_name] = []
                touches_by_level[level_name].append(touch)

            pattern_detail = {
                'pattern_id': tracker.pattern_id,
                'pattern_name': tracker.pattern_name,
                'pattern_type': tracker.pattern_type,
                'direction': tracker.direction,
                'detection_bar': tracker.detection_bar,
                'total_bars_tracked': tracker.total_bars_tracked,
                'is_complete': tracker.is_tracking_complete,
                'level_touches': {}  # level_name -> touch count and details
            }

            # Add touch counts for each level
            all_levels = list(tracker.fib_levels.keys()) + list(tracker.harmonic_levels.keys())
            for level_name in all_levels:
                level_touches = touches_by_level.get(level_name, [])
                pattern_detail['level_touches'][level_name] = {
                    'touch_count': len(level_touches),
                    'first_touch_bar': level_touches[0].absolute_bar if level_touches else None
                }

            summary['individual_patterns'].append(pattern_detail)

        return summary

    def detect_patterns_with_cache(self, current_idx: int) -> Tuple[List[Dict], List[Dict]]:
        """
        Detect patterns with caching for improved performance.
        Only re-detects when necessary.

        Args:
            current_idx: Current bar index in walk-forward simulation

        Returns:
            Tuple of (unformed_patterns, formed_patterns)
        """
        # Check if we should skip detection (use cache)
        if (current_idx - self.last_detection_idx) < self.detection_interval:
            # Return cached results if available
            if current_idx in self.cached_patterns['unformed']:
                return (
                    self.cached_patterns['unformed'][current_idx],
                    self.cached_patterns['formed'].get(current_idx, [])
                )

        # Perform new detection
        end_idx = max(0, current_idx - self.future_buffer)

        if end_idx < 1:  # Allow detection from bar 1
            return [], []

        # Check if extremums need updating
        if end_idx not in self.cached_patterns['extremums']:
            # Use all data from beginning up to current point
            data_slice = self.data.iloc[:end_idx].copy()

            # Find extremum points (expensive operation - cache it!)
            # Use configurable extremum_length (default=1 to match GUI)
            extremum_points = find_extremum_points(data_slice, length=self.extremum_length)

            # Convert extremum points from timestamps to indices
            # This fixes the "out of bounds" errors
            fixed_extremums = []
            for point in extremum_points:
                # Extract 4-tuple format
                timestamp, price, is_high, bar_index = point
                try:
                    # Handle numpy.datetime64
                    if isinstance(timestamp, np.datetime64):
                        # Convert to pandas timestamp
                        ts = pd.Timestamp(timestamp)
                        # Find exact index in data_slice
                        try:
                            idx = data_slice.index.get_loc(ts)
                        except KeyError:
                            # If exact match not found, find the closest
                            distances = abs(data_slice.index - ts)
                            idx = distances.argmin()
                    elif hasattr(timestamp, 'to_pydatetime'):
                        # It's already a pandas timestamp
                        try:
                            idx = data_slice.index.get_loc(timestamp)
                        except KeyError:
                            distances = abs(data_slice.index - timestamp)
                            idx = distances.argmin()
                    elif isinstance(timestamp, (int, np.int64)):
                        if timestamp > 1e15:
                            # It's nanoseconds, convert to timestamp
                            ts = pd.Timestamp(timestamp)
                            try:
                                idx = data_slice.index.get_loc(ts)
                            except KeyError:
                                distances = abs(data_slice.index - ts)
                                idx = distances.argmin()
                        else:
                            # It might already be an index
                            idx = int(timestamp)
                    else:
                        # Try to find it directly
                        try:
                            idx = data_slice.index.get_loc(timestamp)
                        except KeyError:
                            distances = abs(data_slice.index - pd.Timestamp(timestamp))
                            idx = distances.argmin()

                    # Only add if index is valid
                    if 0 <= idx < len(data_slice):
                        fixed_extremums.append((idx, price, is_high, bar_index))
                except Exception as e:
                    # Skip invalid extremum points (silent to avoid spam)
                    continue

            extremum_points = fixed_extremums
            self.cached_patterns['extremums'][end_idx] = extremum_points
            self.current_extremum_points = extremum_points  # Store for update_c_points
        else:
            data_slice = self.data.iloc[:end_idx].copy()
            extremum_points = self.cached_patterns['extremums'][end_idx]
            self.current_extremum_points = extremum_points  # Store for update_c_points

        # Don't skip - let pattern detection functions handle minimum requirements
        # This ensures we track extremums even before patterns are possible
        # if len(extremum_points) < 3:  # Removed to allow extremum tracking from start
        #     return [], []

        unformed_patterns = []
        formed_patterns = []

        # Detect unformed patterns (signals)
        try:
            # Only detect if we have enough new data
            if self.last_detection_idx < 0 or (current_idx - self.last_detection_idx) >= self.detection_interval:

                # Only attempt pattern detection if we have minimum extremums
                # ABCD needs 4, XABCD needs 5
                if len(extremum_points) >= 4:
                    # ABCD patterns - use extremums that are before current position
                    # Extremums are (timestamp, price, is_high) tuples
                    # We want extremums that could form patterns up to current position
                    unformed_abcd = detect_unformed_abcd_patterns(
                        extremum_points,  # Use all extremums, let the detection function handle filtering
                        df=data_slice  # Pass DataFrame for price containment validation
                        # Removed backtest_mode - not supported by the function
                    )
                    for pattern in unformed_abcd:
                        pattern['pattern_type'] = 'ABCD'
                        pattern['pattern_hash'] = self.pattern_tracker.generate_pattern_id(pattern)
                    unformed_patterns.extend(unformed_abcd)

                if len(extremum_points) >= 5:
                    # Debug: At bar 111, show all extremums
                    if current_idx == 111:
                        print(f"\n=== DEBUG: Extremums available at bar {current_idx} ===")
                        for i, ext in enumerate(extremum_points):
                            bar_idx = ext[3] if len(ext) > 3 else i
                            is_high = ext[2]
                            price = ext[1]
                            point_type = "HIGH" if is_high else "LOW"
                            print(f"  Extremum #{i}: Bar {bar_idx} - {point_type} @ {price:.2f}")
                        print("=" * 50)

                    # XABCD patterns - NO LIMITS
                    unformed_xabcd = detect_strict_unformed_xabcd_patterns(
                        extremum_points,  # Use all extremums
                        data_slice,
                        max_patterns=None,  # NO LIMIT - detect ALL patterns
                        max_search_window=None  # NO LIMIT - search entire history
                    )
                    if current_idx % 50 == 0 and current_idx > 0:  # Debug every 50 bars
                        print(f"DEBUG XABCD at bar {current_idx}: {len(extremum_points)} extremums, found {len(unformed_xabcd)} unformed XABCD")
                    for pattern in unformed_xabcd:
                        pattern['pattern_type'] = 'XABCD'
                        pattern['pattern_hash'] = self.pattern_tracker.generate_pattern_id(pattern)
                    unformed_patterns.extend(unformed_xabcd)

                # For now, don't filter - we want to see all unformed patterns
                # Later we can add proper filtering based on timestamps
                # Just filter out already traded patterns
                filtered_unformed = []
                for pattern in unformed_patterns:
                    pattern_hash = pattern.get('pattern_hash', '')
                    if pattern_hash and pattern_hash not in self.traded_patterns:
                        filtered_unformed.append(pattern)

                unformed_patterns = filtered_unformed

                # Cache results
                self.cached_patterns['unformed'][current_idx] = unformed_patterns
                self.last_detection_idx = current_idx

        except Exception as e:
            print(f"Error detecting unformed patterns: {e}")
            import traceback
            traceback.print_exc()

        # DON'T detect formed patterns separately in backtest
        # In a proper walk-forward backtest, ALL patterns start as unformed
        # and transition to formed when price enters the PRZ zone
        # This ensures 100% accuracy - we never "discover" a pattern that's already formed
        formed_patterns = []

        return unformed_patterns, formed_patterns

    def generate_signal(self, pattern: Dict, current_bar: pd.Series) -> Optional[PatternSignal]:
        """
        Convert an unformed pattern into a trading signal.

        Args:
            pattern: Unformed pattern dictionary
            current_bar: Current OHLCV bar

        Returns:
            PatternSignal if valid, None otherwise
        """
        # Check if we've already traded this pattern
        pattern_hash = pattern.get('pattern_hash', '')
        if pattern_hash in self.traded_patterns:
            return None

        # Extract pattern details
        pattern_type = pattern.get('pattern_type', 'ABCD')
        is_bullish = pattern.get('bullish', True)

        # Get PRZ levels from pattern
        prz_levels = []

        # Try to extract PRZ from different pattern formats
        if 'd_min' in pattern and 'd_max' in pattern:
            prz_levels = [pattern['d_min'], pattern['d_max']]
        elif 'prz_levels' in pattern:
            prz_levels = pattern['prz_levels']
        elif 'D_projected' in pattern:
            d_proj = pattern['D_projected']
            if isinstance(d_proj, dict):
                if 'min' in d_proj and 'max' in d_proj:
                    prz_levels = [d_proj['min'], d_proj['max']]
                elif 'price' in d_proj:
                    price = d_proj['price']
                    prz_levels = [price * 0.995, price * 1.005]

        if not prz_levels or len(prz_levels) < 2:
            return None

        # Determine entry, stop loss, and targets
        if is_bullish:
            direction = TradeDirection.LONG
            entry_price = min(prz_levels)  # Enter at bottom of PRZ
            stop_loss = entry_price * 0.97  # 3% stop loss
            take_profit_1 = entry_price * 1.05  # 5% first target
            take_profit_2 = entry_price * 1.10  # 10% second target
        else:
            direction = TradeDirection.SHORT
            entry_price = max(prz_levels)  # Enter at top of PRZ
            stop_loss = entry_price * 1.03  # 3% stop loss
            take_profit_1 = entry_price * 0.95  # 5% first target
            take_profit_2 = entry_price * 0.90  # 10% second target

        # Calculate confidence score
        confidence_score = self.calculate_pattern_confidence(pattern)

        if confidence_score < self.min_pattern_score:
            return None

        return PatternSignal(
            timestamp=current_bar.name,
            pattern_type=pattern_type,
            pattern_name=pattern.get('name', 'Unknown'),
            direction=direction,
            prz_levels=prz_levels,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            confidence_score=confidence_score,
            pattern_data=pattern,
            pattern_hash=pattern_hash
        )

    def calculate_pattern_confidence(self, pattern: Dict) -> float:
        """Calculate confidence score for a pattern"""
        score = 0.5  # Base score

        # Check if pattern has validation flags
        if pattern.get('prz_valid', False):
            score += 0.15
        if pattern.get('d_lines_valid', False):
            score += 0.15
        if pattern.get('structural_valid', False):
            score += 0.1

        # Pattern-specific scoring
        pattern_name = pattern.get('name', '').lower()
        if 'gartley' in pattern_name:
            score += 0.1
        elif 'bat' in pattern_name:
            score += 0.08
        elif 'butterfly' in pattern_name:
            score += 0.05

        # Check if ratios are within tight tolerance
        if pattern.get('ratio_quality', 0) > 0.9:
            score += 0.1

        return min(max(score, 0.0), 1.0)

    def check_entry_conditions(self, signal: PatternSignal, current_bar: pd.Series) -> bool:
        """Check if price has reached entry zone"""
        if signal.direction == TradeDirection.LONG:
            return current_bar['Low'] <= signal.entry_price <= current_bar['High']
        else:
            return current_bar['Low'] <= signal.entry_price <= current_bar['High']

    def execute_trade(self, signal: PatternSignal, entry_bar: pd.Series) -> TradeResult:
        """Execute a trade based on signal"""
        # Mark pattern as traded
        if signal.pattern_hash:
            self.traded_patterns.add(signal.pattern_hash)

        trade = TradeResult(
            signal=signal,
            entry_time=entry_bar.name
        )

        self.open_trades.append(trade)
        return trade

    def update_open_trades(self, current_bar: pd.Series, current_idx: int, formed_patterns: List[Dict]):
        """Update open trades with current bar data"""
        for trade in self.open_trades[:]:  # Copy list to allow modification
            if trade.exit_time:
                continue

            # Calculate current P&L
            if trade.signal.direction == TradeDirection.LONG:
                current_pnl = (current_bar['Close'] - trade.signal.entry_price) / trade.signal.entry_price

                # Check stop loss
                if current_bar['Low'] <= trade.signal.stop_loss:
                    trade.exit_time = current_bar.name
                    trade.exit_price = trade.signal.stop_loss
                    trade.exit_reason = "stop_loss"
                    trade.pnl_percent = (trade.signal.stop_loss - trade.signal.entry_price) / trade.signal.entry_price
                # Check take profit
                elif current_bar['High'] >= trade.signal.take_profit_1:
                    trade.exit_time = current_bar.name
                    trade.exit_price = trade.signal.take_profit_1
                    trade.exit_reason = "take_profit_1"
                    trade.pnl_percent = (trade.signal.take_profit_1 - trade.signal.entry_price) / trade.signal.entry_price
            else:  # SHORT
                current_pnl = (trade.signal.entry_price - current_bar['Close']) / trade.signal.entry_price

                # Check stop loss
                if current_bar['High'] >= trade.signal.stop_loss:
                    trade.exit_time = current_bar.name
                    trade.exit_price = trade.signal.stop_loss
                    trade.exit_reason = "stop_loss"
                    trade.pnl_percent = (trade.signal.entry_price - trade.signal.stop_loss) / trade.signal.entry_price
                # Check take profit
                elif current_bar['Low'] <= trade.signal.take_profit_1:
                    trade.exit_time = current_bar.name
                    trade.exit_price = trade.signal.take_profit_1
                    trade.exit_reason = "take_profit_1"
                    trade.pnl_percent = (trade.signal.entry_price - trade.signal.take_profit_1) / trade.signal.entry_price

            # Update max excursions
            trade.max_favorable_excursion = max(trade.max_favorable_excursion, current_pnl)
            trade.max_adverse_excursion = min(trade.max_adverse_excursion, current_pnl)

            # Pattern completion is now tracked via zone checking, not here
            # The pattern_completed flag is set when price enters the PRZ/d_lines zone

            # Close trade if exit triggered
            if trade.exit_time:
                trade.pnl = self.current_capital * self.position_size * trade.pnl_percent
                trade.trade_duration_bars = current_idx - self.data.index.get_loc(trade.entry_time)

                self.closed_trades.append(trade)
                self.open_trades.remove(trade)
                self.current_capital += trade.pnl


    def run_backtest(self, progress_callback=None) -> BacktestStatistics:
        """Run the complete backtest simulation"""
        import time
        start_time = time.time()

        print(f"\nStarting Optimized Walk-Forward Backtest")
        print(f"Data range: {self.data.index[0]} to {self.data.index[-1]}")
        print(f"Total bars: {len(self.data)}")
        print(f"Detection interval: Every {self.detection_interval} bars")
        print(f"Future buffer: {self.future_buffer} bars")
        print(f"Initial capital: ${self.initial_capital:,.2f}")
        print(f"Min pattern score: {self.min_pattern_score}")
        print("-" * 60)

        # Reset state
        self.current_capital = self.initial_capital
        self.open_trades = []
        self.closed_trades = []
        self.all_signals = []
        self.equity_curve = [self.initial_capital]
        self.cached_patterns = {'unformed': {}, 'formed': {}, 'extremums': {}}
        self.last_detection_idx = -1
        self.traded_patterns = set()
        self.pattern_cache = set()  # Reset pattern cache
        self.pattern_tracker.reset()  # Reset pattern tracker
        self.formed_pattern_ids = set()  # Track unique formed pattern IDs

        # Reset Fibonacci tracking
        self.fibonacci_trackers = {}
        self.active_fibonacci_tracking = set()

        # Track statistics during backtest
        total_unformed_found = 0
        total_formed_found = 0
        unique_patterns_found = set()
        unique_unformed_patterns_found = set()
        unique_formed_patterns = set()  # Track unique formed patterns
        pattern_type_counts = {}  # Track how many instances of each pattern type

        # Track pending signals
        pending_signals = []

        # Track warnings for display in GUI
        self.tracking_warnings = []

        # Walk forward through time
        # Start from bar 1 for TRUE 100% coverage
        # Patterns will be detected as soon as enough extremums are available
        start_idx = 1  # Start from bar 1 for 100% coverage
        print(f"Starting walk-forward from bar {start_idx} for 100% coverage")
        for idx in range(start_idx, len(self.data)):
            current_bar = self.data.iloc[idx]

            # Update progress
            if progress_callback and idx % 100 == 0:
                progress = (idx / len(self.data)) * 100
                progress_callback(progress)

            # Print progress every 500 bars
            if idx % 500 == 0:
                print(f"Processing bar {idx}/{len(self.data)} ({idx/len(self.data)*100:.1f}%) - Patterns found: {len(self.pattern_cache)} - Trades: {len(self.closed_trades)}")

            # Detect patterns with caching
            unformed_patterns, formed_patterns = self.detect_patterns_with_cache(idx)

            # Skip incremental extremum tracking - we'll count from full dataset at the end
            # This ensures we match GUI exactly (which counts from full dataset)
            # The cached extremums are still used for pattern detection

            # Track pattern counts
            if unformed_patterns:
                total_unformed_found += len(unformed_patterns)
                xabcd_count_new = 0
                xabcd_count_total = 0
                for pattern in unformed_patterns:
                    if pattern.get('pattern_type') == 'XABCD':
                        xabcd_count_total += 1
                    # Use the same ID generation method as the tracker for consistency
                    pattern_id = self.pattern_tracker.generate_pattern_id(pattern)

                    # Debug: Check if this is one of the patterns found in full dataset
                    indices = pattern.get('indices', {})
                    x_idx = indices.get('X', '?')
                    a_idx = indices.get('A', '?')
                    b_idx = indices.get('B', '?')
                    c_idx = indices.get('C', '?')
                    if (a_idx in [72, 82] and b_idx == 96 and c_idx == 100):
                        print(f"DEBUG UNFORMED DETECTION @ bar {idx}: {pattern.get('name', 'unknown')} - X:{x_idx} A:{a_idx} B:{b_idx} C:{c_idx}")
                        print(f"  Pattern ID: {pattern_id}")

                    if pattern_id not in unique_unformed_patterns_found:
                        unique_unformed_patterns_found.add(pattern_id)
                        # Track unformed pattern with PatternTracker ONLY if unique
                        self.pattern_tracker.track_unformed_pattern(pattern, idx)
                        if pattern.get('pattern_type') == 'XABCD':
                            xabcd_count_new += 1
                        # Track pattern type counts
                        pattern_type = pattern.get('name', 'unknown')
                        if pattern_type not in pattern_type_counts:
                            pattern_type_counts[pattern_type] = 0
                        pattern_type_counts[pattern_type] += 1
                if xabcd_count_total > 0 and idx % 50 == 0:
                    print(f"DEBUG at bar {idx}: Found {xabcd_count_total} XABCD, {xabcd_count_new} are new/unique")
            # Formed patterns are no longer detected separately
            # All patterns transition from unformed → formed when price enters PRZ
            # This block is intentionally removed for 100% walk-forward accuracy

            # Update C points for pending patterns when new extremums appear
            updated_c_patterns = self.pattern_tracker.update_c_points(
                extremum_points=self.current_extremum_points,
                current_bar=idx
            )

            # Check for pattern dismissals (structure breaks)
            dismissed_patterns = self.pattern_tracker.check_pattern_dismissal(
                price_high=current_bar['High'],
                price_low=current_bar['Low'],
                current_bar=idx
            )

            # Check if current price enters any pattern's D zone
            current_timestamp = current_bar.name if hasattr(current_bar, 'name') else None
            data_for_detection = self.data.iloc[:idx+1] if idx < len(self.data) else self.data
            completed_pattern_ids = self.pattern_tracker.check_price_in_zone(
                price_high=current_bar['High'],
                price_low=current_bar['Low'],
                current_bar=idx,
                current_timestamp=current_timestamp,
                data_for_detection=data_for_detection
            )

            # Initialize Fibonacci tracking for patterns that just entered PRZ
            if completed_pattern_ids:
                for pattern_id in completed_pattern_ids:
                    # Skip if we're already tracking this pattern
                    if pattern_id in self.fibonacci_trackers:
                        continue

                    # Get the pattern from tracker
                    if pattern_id in self.pattern_tracker.tracked_patterns:
                        tracked_pattern = self.pattern_tracker.tracked_patterns[pattern_id]

                        # Reconstruct pattern dict from TrackedPattern object
                        pattern_data = {
                            'name': tracked_pattern.subtype,
                            'pattern_type': tracked_pattern.pattern_type,
                            'formation_status': 'formed',
                            'points': {},
                            'indices': {}
                        }

                        # Add all points with indices
                        if tracked_pattern.x_point:
                            pattern_data['points']['X'] = {
                                'price': tracked_pattern.x_point[1],
                                'index': tracked_pattern.x_point[0],
                                'time': None
                            }
                            pattern_data['indices']['X'] = tracked_pattern.x_point[0]

                        pattern_data['points']['A'] = {
                            'price': tracked_pattern.a_point[1],
                            'index': tracked_pattern.a_point[0],
                            'time': tracked_pattern.a_timestamp
                        }
                        pattern_data['indices']['A'] = tracked_pattern.a_point[0]

                        pattern_data['points']['B'] = {
                            'price': tracked_pattern.b_point[1],
                            'index': tracked_pattern.b_point[0],
                            'time': tracked_pattern.b_timestamp
                        }
                        pattern_data['indices']['B'] = tracked_pattern.b_point[0]

                        pattern_data['points']['C'] = {
                            'price': tracked_pattern.c_point[1],
                            'index': tracked_pattern.c_point[0],
                            'time': tracked_pattern.c_timestamp
                        }
                        pattern_data['indices']['C'] = tracked_pattern.c_point[0]

                        # Add D point from zone entry
                        d_idx = tracked_pattern.zone_entry_bar if tracked_pattern.zone_entry_bar else idx
                        pattern_data['points']['D'] = {
                            'price': tracked_pattern.zone_entry_price if tracked_pattern.zone_entry_price else current_bar['Close'],
                            'index': d_idx,
                            'time': tracked_pattern.zone_entry_timestamp if tracked_pattern.zone_entry_timestamp else current_timestamp
                        }
                        pattern_data['indices']['D'] = d_idx

                        # Add PRZ zones
                        if tracked_pattern.prz_zones:
                            pattern_data['ratios'] = {'prz_zones': tracked_pattern.prz_zones}

                        # Initialize Fibonacci tracking for this newly completed pattern
                        self.initialize_fibonacci_tracking(pattern_data, idx)

            # Check for zone violations (failures)
            failed_patterns = self.pattern_tracker.check_zone_violation(
                price_high=current_bar['High'],
                price_low=current_bar['Low'],
                current_bar=idx
            )

            # Mark trades as pattern_completed if their pattern ID is in completed list
            for trade in self.open_trades:
                if not trade.pattern_completed and trade.signal.pattern_data:
                    # Generate pattern ID for this trade's pattern
                    pattern_id = self.pattern_tracker.generate_pattern_id(trade.signal.pattern_data)
                    if pattern_id in completed_pattern_ids:
                        trade.pattern_completed = True

            # Generate signals from unformed patterns
            for pattern in unformed_patterns:
                # Add pattern to cache for tracking
                pattern_hash = self.pattern_tracker.generate_pattern_id(pattern)
                if pattern_hash:
                    self.pattern_cache.add(pattern_hash)

                signal = self.generate_signal(pattern, current_bar)
                if signal:
                    self.all_signals.append(signal)
                    pending_signals.append(signal)

            # Check pending signals for entry
            for signal in pending_signals[:]:
                if self.check_entry_conditions(signal, current_bar):
                    # Execute trade if we have capacity
                    if len(self.open_trades) < self.max_open_trades:
                        self.execute_trade(signal, current_bar)
                        pending_signals.remove(signal)
                # Remove old signals (>20 bars)
                elif idx - self.data.index.get_loc(signal.timestamp) > 20:
                    pending_signals.remove(signal)

            # Update Fibonacci tracking for all active formed patterns
            self.update_fibonacci_tracking(current_bar, idx)

            # Update open trades
            self.update_open_trades(current_bar, idx, formed_patterns)

            # Update equity curve
            open_pnl = sum(
                self.current_capital * self.position_size *
                ((current_bar['Close'] - t.signal.entry_price) / t.signal.entry_price
                 if t.signal.direction == TradeDirection.LONG else
                 (t.signal.entry_price - current_bar['Close']) / t.signal.entry_price)
                for t in self.open_trades
            )
            current_equity = self.current_capital + open_pnl
            self.equity_curve.append(current_equity)

        # Close any remaining open trades
        final_bar = self.data.iloc[-1]
        for trade in self.open_trades:
            trade.exit_time = final_bar.name
            trade.exit_price = final_bar['Close']
            trade.exit_reason = "end_of_data"

            if trade.signal.direction == TradeDirection.LONG:
                trade.pnl_percent = (trade.exit_price - trade.signal.entry_price) / trade.signal.entry_price
            else:
                trade.pnl_percent = (trade.signal.entry_price - trade.exit_price) / trade.signal.entry_price

            trade.pnl = self.current_capital * self.position_size * trade.pnl_percent
            self.closed_trades.append(trade)

        # Print pattern detection summary
        print("\n" + "="*60)
        print("PATTERN DETECTION SUMMARY")
        print("="*60)
        print(f"Pattern Types Found: {len(pattern_type_counts)} unique types")
        print(f"Pattern Instances Found: {len(unique_unformed_patterns_found)} unique instances")
        print(f"Total Formed Patterns: {len(unique_formed_patterns)}")
        print(f"Patterns that generated signals: {len(self.all_signals)}")
        print(f"Patterns that resulted in trades: {len(self.closed_trades)}")

        # Only show detection events in debug mode or when detection interval > 1
        if self.detection_interval > 1:
            print(f"  (Detection interval: every {self.detection_interval} bars)")

        # Store pattern counts for statistics - use UNIQUE counts for clarity
        self.total_unformed_found = len(unique_unformed_patterns_found)  # Store unique count instead
        self.total_formed_found = len(unique_formed_patterns)  # Store unique formed count
        self.detection_events = total_unformed_found  # Keep raw count for debugging if needed
        self.pattern_type_counts = pattern_type_counts  # Store pattern type distribution

        # Count extremums from the FULL dataset for accurate reporting
        # (backtesting excludes last future_buffer bars, but GUI doesn't)
        full_extremums = find_extremum_points(self.data, length=self.extremum_length)
        self.total_extremum_points = len(full_extremums)
        self.high_extremum_points = sum(1 for e in full_extremums if e[2])
        self.low_extremum_points = len(full_extremums) - self.high_extremum_points

        # Also count formed patterns from FULL dataset to match GUI
        print("\nCounting formed patterns from full dataset...")
        # Convert extremums to indices
        extremums_with_idx = []
        for ext in full_extremums:
            # Extract 4-tuple format
            timestamp, price, is_high, bar_index = ext
            try:
                idx = self.data.index.get_loc(timestamp)
                extremums_with_idx.append((idx, price, is_high, bar_index))
            except:
                pass

        # Detect ALL patterns from full dataset
        data_with_date = self.data.reset_index()
        all_abcd_full, all_xabcd_full = detect_all_gui_patterns(extremums_with_idx, data_with_date, max_patterns=200)

        # Count formed patterns (those with D point)
        formed_abcd_patterns = [p for p in all_abcd_full if 'points' in p and 'D' in p['points']]
        formed_xabcd_patterns = [p for p in all_xabcd_full if 'points' in p and 'D' in p['points']]

        self.formed_abcd_count = len(formed_abcd_patterns)
        self.formed_xabcd_count = len(formed_xabcd_patterns)

        # Update the total formed count to match GUI
        self.total_formed_found = self.formed_abcd_count + self.formed_xabcd_count
        print(f"Formed patterns from full dataset: {self.formed_abcd_count} ABCD + {self.formed_xabcd_count} XABCD = {self.total_formed_found}")

        # Debug: Show pattern IDs from full dataset
        print(f"\nDEBUG: Formed pattern IDs from full dataset:")
        for p in formed_xabcd_patterns:
            pattern_id = self.pattern_tracker.generate_pattern_id(p)
            indices = p.get('indices', {})
            print(f"  {pattern_id[:20]}... {p.get('name', 'unknown')} - X:{indices.get('X','?')} A:{indices.get('A','?')} B:{indices.get('B','?')} C:{indices.get('C','?')}")

        print(f"\nDEBUG: Fibonacci tracked pattern IDs:")
        for pid, tracker in self.fibonacci_trackers.items():
            print(f"  {pid[:20]}... {tracker.pattern_name} ({tracker.pattern_type})")

        # Print extremum summary
        print("\n" + "="*60)
        print("EXTREMUM POINTS SUMMARY")
        print("="*60)
        print(f"Total extremum points detected: {self.total_extremum_points}")
        print(f"High extremums: {self.high_extremum_points}")
        print(f"Low extremums: {self.low_extremum_points}")
        print(f"Extremum detection length used: {self.extremum_length}")
        print("Note: Counted from full dataset to match GUI display")

        # Get pattern tracking statistics
        tracking_stats = self.pattern_tracker.get_completion_statistics()
        print("\n" + "="*60)
        print("PATTERN TRACKING ANALYSIS")
        print("="*60)
        print(f"Total patterns tracked: {tracking_stats['total_tracked']}")
        print(f"Patterns with outcomes:")
        print(f"  Success (Zone + Reversal): {tracking_stats['success']}")
        print(f"  Failed (Zone Violated): {tracking_stats['failed']}")
        print(f"  Dismissed (Structure Break): {tracking_stats['dismissed']}")
        print(f"  Pending (Still Valid): {tracking_stats['pending']}")

        if tracking_stats['concluded'] > 0:
            print(f"\nTrading Performance (Success vs Failed):")
            print(f"  Zone Success Rate: {tracking_stats['zone_success_rate']*100:.1f}%")
            print(f"  Average projection accuracy: {tracking_stats['avg_projection_accuracy']*100:.1f}%")
            print(f"  Average bars to complete: {tracking_stats['avg_bars_to_complete']:.1f}")

        if tracking_stats['top_performing_patterns']:
            print("\nTop Performing Pattern Types (by completion rate):")
            for i, pattern_info in enumerate(tracking_stats['top_performing_patterns'][:5], 1):
                print(f"{i}. {pattern_info['type']}: {pattern_info['completion_rate']*100:.1f}% "
                      f"(completed {pattern_info['completed']}/{pattern_info['total']})")

        # Calculate statistics with time taken
        stats = self.calculate_statistics()
        stats.time_taken = time.time() - start_time
        return stats

    def calculate_statistics(self) -> BacktestStatistics:
        """Calculate comprehensive backtest statistics"""
        stats = BacktestStatistics()

        # Always populate pattern counts
        stats.patterns_detected = len(self.pattern_cache)
        stats.patterns_traded = len(self.all_signals)
        stats.total_unformed_patterns = getattr(self, 'total_unformed_found', 0)
        stats.total_formed_patterns = getattr(self, 'total_formed_found', 0)

        # Add pattern type distribution
        stats.pattern_type_counts = getattr(self, 'pattern_type_counts', {})

        # Add extremum counts to statistics
        stats.total_extremum_points = getattr(self, 'total_extremum_points', 0)
        stats.high_extremum_points = getattr(self, 'high_extremum_points', 0)
        stats.low_extremum_points = getattr(self, 'low_extremum_points', 0)

        # Get pattern tracking statistics
        tracking_stats = self.pattern_tracker.get_completion_statistics()

        # Debug print to see what's in tracking stats
        print("\n=== DEBUG: Pattern Tracking Statistics ===")
        print(f"Total tracked: {tracking_stats.get('total_tracked', 0)}")
        print(f"Success: {tracking_stats.get('success', 0)}")
        print(f"In Zone: {tracking_stats.get('in_zone', 0)}")
        print(f"Failed: {tracking_stats.get('failed', 0)}")
        print(f"Dismissed: {tracking_stats.get('dismissed', 0)}")
        print(f"Pending: {tracking_stats.get('pending', 0)}")
        print("==========================================\n")

        stats.patterns_tracked = tracking_stats['total_tracked']
        stats.patterns_success = tracking_stats['success']
        stats.patterns_failed = tracking_stats['failed']
        stats.patterns_dismissed = tracking_stats['dismissed']
        stats.patterns_pending = tracking_stats['pending']
        stats.patterns_in_zone = tracking_stats.get('in_zone', 0)
        stats.patterns_success_rate = tracking_stats['zone_success_rate']
        stats.avg_projection_accuracy = tracking_stats['avg_projection_accuracy']

        # Pattern type completion rates
        for pattern_type, type_stats in tracking_stats['pattern_type_stats'].items():
            if type_stats['total_detected'] > 0:
                stats.pattern_type_completion_rates[pattern_type] = type_stats['completion_rate']

        if not self.closed_trades:
            print("\n" + "="*60)
            print("BACKTEST COMPLETED - NO TRADES EXECUTED")
            print("="*60)
            print(f"Patterns detected: {len(self.pattern_cache)}")
            print(f"Signals generated: {len(self.all_signals)}")
            print("\nPossible reasons for no trades:")
            print(f"- Min pattern score too high (current: {self.min_pattern_score})")
            print("- Patterns not meeting entry conditions")
            print("- Try lowering min_pattern_score to 0.1 or 0.2")

            stats.equity_curve = self.equity_curve if self.equity_curve else [self.initial_capital]
            return stats

        # Basic counts
        stats.total_signals = len(self.all_signals)
        stats.total_trades = len(self.closed_trades)
        # patterns_detected and patterns_traded already set above

        # Win/Loss analysis
        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]

        stats.winning_trades = len(winning_trades)
        stats.losing_trades = len(losing_trades)
        stats.win_rate = stats.winning_trades / stats.total_trades if stats.total_trades > 0 else 0

        # Average P&L
        if winning_trades:
            stats.avg_win = np.mean([t.pnl_percent for t in winning_trades]) * 100
        if losing_trades:
            stats.avg_loss = np.mean([abs(t.pnl_percent) for t in losing_trades]) * 100

        # Profit factor
        total_wins = sum(t.pnl for t in winning_trades) if winning_trades else 0
        total_losses = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 1
        stats.profit_factor = total_wins / total_losses if total_losses > 0 else 0

        # Pattern completion rate
        completed_patterns = [t for t in self.closed_trades if t.pattern_completed]
        stats.pattern_completion_rate = len(completed_patterns) / stats.total_trades if stats.total_trades > 0 else 0

        # Total return
        final_capital = self.equity_curve[-1] if self.equity_curve else self.initial_capital
        stats.total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        # Maximum drawdown
        equity_array = np.array(self.equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max
        stats.max_drawdown = abs(drawdown.min()) * 100 if len(drawdown) > 0 else 0

        # Sharpe ratio (simplified - daily returns)
        if len(self.equity_curve) > 1:
            returns = np.diff(self.equity_curve) / self.equity_curve[:-1]
            if returns.std() > 0:
                stats.sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(252)  # Annualized

        # Pattern-specific performance
        pattern_names = {}
        for trade in self.closed_trades:
            pattern_name = trade.signal.pattern_name
            if pattern_name not in pattern_names:
                pattern_names[pattern_name] = []
            pattern_names[pattern_name].append(trade)

        for pattern_name, trades in pattern_names.items():
            wins = [t for t in trades if t.pnl > 0]
            stats.pattern_performance[pattern_name] = {
                'count': len(trades),
                'win_rate': (len(wins) / len(trades)) * 100 if trades else 0,
                'avg_pnl': np.mean([t.pnl_percent * 100 for t in trades]) if trades else 0,
                'total_pnl': sum(t.pnl for t in trades)
            }

        stats.equity_curve = self.equity_curve

        # Add tracking warnings to stats
        stats.tracking_warnings = self.tracking_warnings

        # Add Fibonacci analysis to stats
        stats.fibonacci_analysis = list(self.fibonacci_trackers.values())

        return stats

    def print_summary(self, stats: BacktestStatistics):
        """Print a formatted summary of backtest results"""

        print("\n" + "="*60)
        print("OPTIMIZED WALK-FORWARD BACKTEST RESULTS")
        print("="*60)

        print(f"\nSignal Generation:")
        print(f"  Total Signals Generated: {stats.total_signals}")
        print(f"  Total Trades Executed: {stats.total_trades}")
        print(f"  Signal Conversion Rate: {(stats.total_trades/stats.total_signals*100) if stats.total_signals > 0 else 0:.1f}%")

        print(f"\nTrade Performance:")
        print(f"  Winning Trades: {stats.winning_trades}")
        print(f"  Losing Trades: {stats.losing_trades}")
        print(f"  Win Rate: {stats.win_rate*100:.1f}%")
        print(f"  Average Win: +{stats.avg_win:.2f}%")
        print(f"  Average Loss: -{stats.avg_loss:.2f}%")
        print(f"  Profit Factor: {stats.profit_factor:.2f}")

        print(f"\nPortfolio Performance:")
        print(f"  Total Return: {stats.total_return:.2f}%")
        print(f"  Maximum Drawdown: {stats.max_drawdown:.2f}%")
        print(f"  Sharpe Ratio: {stats.sharpe_ratio:.2f}")
        print(f"  Pattern Completion Rate: {stats.pattern_completion_rate*100:.1f}%")

        print(f"  Final Capital: ${self.equity_curve[-1]:,.2f}")

        if stats.pattern_performance:
            print("\n" + "-"*40)
            print("TOP PERFORMING PATTERNS")
            print("-"*40)

            # Sort by win rate
            sorted_patterns = sorted(
                stats.pattern_performance.items(),
                key=lambda x: x[1]['win_rate'],
                reverse=True
            )[:5]

            for pattern, perf in sorted_patterns:
                print(f"\n{pattern}:")
                print(f"  Trades: {perf['count']}")
                print(f"  Win Rate: {perf['win_rate']:.1f}%")
                print(f"  Avg P&L: {perf['avg_pnl']:.2f}%")
                print(f"  Total P&L: ${perf['total_pnl']:.2f}")

    def export_results(self, filename: str = "optimized_backtest_results.json"):
        """Export backtest results to JSON file"""
        stats = self.calculate_statistics()

        results = {
            'metadata': {
                'backtest_date': datetime.now().isoformat(),
                'data_range': f"{self.data.index[0]} to {self.data.index[-1]}",
                'total_bars': len(self.data),
                'initial_capital': self.initial_capital,
                'position_size': self.position_size,
                'detection_interval': self.detection_interval,
                'future_buffer': self.future_buffer,
                'min_pattern_score': self.min_pattern_score,
                'optimization': 'Enabled with caching'
            },
            'performance': {
                'total_return': stats.total_return,
                'max_drawdown': stats.max_drawdown,
                'sharpe_ratio': stats.sharpe_ratio,
                'win_rate': stats.win_rate * 100,
                'profit_factor': stats.profit_factor,
                'total_trades': stats.total_trades
            },
            'pattern_performance': stats.pattern_performance,
            'trades': []
        }

        # Add trade details
        for trade in self.closed_trades[:100]:  # Limit to first 100 trades
            results['trades'].append({
                'entry_time': str(trade.entry_time),
                'exit_time': str(trade.exit_time),
                'pattern': trade.signal.pattern_name,
                'direction': trade.signal.direction.value,
                'entry_price': trade.signal.entry_price,
                'exit_price': trade.exit_price,
                'pnl_percent': trade.pnl_percent * 100,
                'exit_reason': trade.exit_reason,
                'pattern_completed': trade.pattern_completed
            })

        # Save to file
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\nResults exported to {filename}")


def run_optimized_backtest():
    """Example function to demonstrate optimized backtester usage"""

    print("Loading data...")
    data = pd.read_csv('btcusdt_1d.csv')

    # Rename columns to match expected format
    data.rename(columns={
        'time': 'Date',
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }, inplace=True)

    data['Date'] = pd.to_datetime(data['Date'])
    data.set_index('Date', inplace=True)

    # Initialize optimized backtester
    backtester = OptimizedWalkForwardBacktester(
        data=data,
        initial_capital=10000,
        position_size=0.02,  # 2% risk per trade
        future_buffer=5,  # Stop 5 bars before current
        min_pattern_score=0.5,  # Lower threshold for more trades
        max_open_trades=5,
        detection_interval=10  # Detect patterns every 10 bars
    )

    # Run backtest
    print("\nRunning optimized walk-forward backtest...")
    stats = backtester.run_backtest()

    # Print results
    backtester.print_summary(stats)

    # Export detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backtester.export_results(f"optimized_backtest_{timestamp}.json")

    return backtester, stats


if __name__ == "__main__":
    backtester, stats = run_optimized_backtest()