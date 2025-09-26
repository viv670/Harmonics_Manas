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
from comprehensive_abcd_patterns import detect_unformed_abcd_patterns
from comprehensive_xabcd_patterns import detect_strict_unformed_xabcd_patterns
from gui_compatible_detection import detect_all_gui_patterns
# Extremum detection now done inline with scipy.signal.argrelextrema
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

    def get_pattern_hash(self, pattern: Dict) -> str:
        """Create unique hash for pattern to avoid duplicate trades"""
        pattern_type = pattern.get('pattern_type', 'unknown')
        name = pattern.get('name', 'unknown')

        # Use key points to create unique ID
        if pattern_type == 'XABCD':
            x = pattern.get('X', 0)
            a = pattern.get('A', 0)
            b = pattern.get('B', 0)
            c = pattern.get('C', 0)
            return f"{name}_{x}_{a}_{b}_{c}"
        else:
            a = pattern.get('A', 0)
            b = pattern.get('B', 0)
            c = pattern.get('C', 0)
            return f"{name}_{a}_{b}_{c}"

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
            # Use scipy.signal.argrelextrema for consistent results with GUI
            from scipy.signal import argrelextrema
            import numpy as np

            local_maxima = argrelextrema(data_slice['High'].values, np.greater, order=self.extremum_length)[0]
            local_minima = argrelextrema(data_slice['Low'].values, np.less, order=self.extremum_length)[0]

            extremum_points = []
            for idx in local_maxima:
                extremum_points.append((data_slice.index[idx], data_slice.iloc[idx]['High'], True))
            for idx in local_minima:
                extremum_points.append((data_slice.index[idx], data_slice.iloc[idx]['Low'], False))

            # Sort by timestamp
            extremum_points.sort(key=lambda x: x[0])

            # No conversion needed - extremums are already in (timestamp, price, is_high) format
            self.cached_patterns['extremums'][end_idx] = extremum_points
        else:
            data_slice = self.data.iloc[:end_idx].copy()
            extremum_points = self.cached_patterns['extremums'][end_idx]

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
                        df=data_slice,  # Pass DataFrame for price containment validation
                        backtest_mode=False  # NO LIMITS - detect ALL patterns for 100% certainty
                    )
                    for pattern in unformed_abcd:
                        pattern['pattern_type'] = 'ABCD'
                        pattern['pattern_hash'] = self.get_pattern_hash(pattern)
                    unformed_patterns.extend(unformed_abcd)

                if len(extremum_points) >= 5:
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
                        pattern['pattern_hash'] = self.get_pattern_hash(pattern)
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

        # Detect formed patterns every bar for maximum accuracy
        if True:  # Check every single bar
            try:
                # Only attempt if we have minimum extremums
                if len(extremum_points) >= 4:
                    # Get ALL patterns using GUI-compatible detection
                    # Reset index to have Date as a column (gui_compatible_detection expects this)
                    data_slice_with_date = data_slice.reset_index()

                    # CRITICAL FIX: Convert extremums to index format for formed pattern detection
                    # GUI detection of formed patterns (with D point) requires indices, not timestamps
                    extremums_with_idx = []
                    for timestamp, price, is_high in extremum_points:
                        try:
                            idx = data_slice.index.get_loc(timestamp)
                            extremums_with_idx.append((idx, price, is_high))
                        except:
                            # Skip if timestamp not found
                            pass

                    # Use a reasonable max_patterns limit to avoid hanging
                    # GUI typically shows < 100 patterns for any given timeframe
                    all_abcd, all_xabcd = detect_all_gui_patterns(extremums_with_idx, data_slice_with_date, max_patterns=200)
                else:
                    all_abcd, all_xabcd = [], []

                # Separate formed (with D point) from unformed (without D point)
                for pattern in all_abcd:
                    pattern['pattern_type'] = 'ABCD'
                    # Check if pattern has D point (formed) or not (unformed)
                    if 'points' in pattern and 'D' in pattern['points']:
                        # Add pattern hash for deduplication
                        pattern['pattern_hash'] = self.get_pattern_hash(pattern)
                        formed_patterns.append(pattern)

                for pattern in all_xabcd:
                    pattern['pattern_type'] = 'XABCD'
                    # Check if pattern has D point (formed) or not (unformed)
                    if 'points' in pattern and 'D' in pattern['points']:
                        # Add pattern hash for deduplication
                        pattern['pattern_hash'] = self.get_pattern_hash(pattern)
                        formed_patterns.append(pattern)

                # Cache formed patterns
                self.cached_patterns['formed'][current_idx] = formed_patterns

            except Exception as e:
                print(f"ERROR: Failed to detect formed patterns at index {current_idx}: {str(e)}")
                import traceback
                traceback.print_exc()
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
            if formed_patterns:
                # Check if formed patterns match existing unformed patterns
                for pattern in formed_patterns:
                    # First try to update existing unformed pattern
                    updated_pattern_id = self.pattern_tracker.update_unformed_to_formed(pattern, idx)

                    if updated_pattern_id:
                        # This formed pattern matched an existing unformed pattern
                        if updated_pattern_id not in self.formed_pattern_ids:
                            self.formed_pattern_ids.add(updated_pattern_id)
                            unique_formed_patterns.add(updated_pattern_id)
                            total_formed_found += 1
                            if pattern.get('pattern_type') == 'XABCD':
                                print(f"  XABCD pattern {updated_pattern_id[:8]}... transitioned to formed")
                    else:
                        # This is a new formed pattern not previously seen as unformed
                        # This shouldn't happen in a proper walk-forward, but handle it
                        pattern_id = self.pattern_tracker.generate_pattern_id(pattern)

                        if pattern_id not in self.formed_pattern_ids:
                            self.formed_pattern_ids.add(pattern_id)
                            unique_formed_patterns.add(pattern_id)
                            total_formed_found += 1
                            # Note: We don't track it as a new pattern since it should have been seen as unformed first
                            warning_msg = f"Pattern {pattern.get('name', pattern_id[:8])} detected as formed without being tracked as unformed first"
                            print(f"WARNING: {warning_msg}")
                            self.tracking_warnings.append(warning_msg)

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
                pattern_hash = self.get_pattern_hash(pattern)
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
        from scipy.signal import argrelextrema
        import numpy as np

        local_maxima_full = argrelextrema(self.data['High'].values, np.greater, order=self.extremum_length)[0]
        local_minima_full = argrelextrema(self.data['Low'].values, np.less, order=self.extremum_length)[0]

        self.total_extremum_points = len(local_maxima_full) + len(local_minima_full)
        self.high_extremum_points = len(local_maxima_full)
        self.low_extremum_points = len(local_minima_full)

        # Also count formed patterns from FULL dataset to match GUI
        print("\nCounting formed patterns from full dataset...")

        # Create full extremums list for compatibility
        full_extremums = []
        for idx in local_maxima_full:
            full_extremums.append((self.data.index[idx], self.data.iloc[idx]['High'], True))
        for idx in local_minima_full:
            full_extremums.append((self.data.index[idx], self.data.iloc[idx]['Low'], False))
        full_extremums.sort(key=lambda x: x[0])

        # Convert extremums to indices
        extremums_with_idx = []
        for ext in full_extremums:
            timestamp, price, is_high = ext
            try:
                idx = self.data.index.get_loc(timestamp)
                extremums_with_idx.append((idx, price, is_high))
            except:
                pass

        # Detect ALL patterns from full dataset
        data_with_date = self.data.reset_index()
        all_abcd_full, all_xabcd_full = detect_all_gui_patterns(extremums_with_idx, data_with_date, max_patterns=200)

        # Count formed patterns (those with D point)
        self.formed_abcd_count = sum(1 for p in all_abcd_full if 'points' in p and 'D' in p['points'])
        self.formed_xabcd_count = sum(1 for p in all_xabcd_full if 'points' in p and 'D' in p['points'])

        # Update the total formed count to match GUI
        self.total_formed_found = self.formed_abcd_count + self.formed_xabcd_count
        print(f"Formed patterns from full dataset: {self.formed_abcd_count} ABCD + {self.formed_xabcd_count} XABCD = {self.total_formed_found}")

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
            print(f"  Success Rate: {tracking_stats['success_rate']*100:.1f}%")
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
        stats.patterns_success_rate = tracking_stats['success_rate']
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