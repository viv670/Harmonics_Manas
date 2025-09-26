"""
Walk-Forward Harmonic Pattern Backtesting System
================================================
Real-time simulation backtester that avoids look-ahead bias.
Uses unformed patterns for entry signals and tracks their completion.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import json
from enum import Enum
import warnings
warnings.filterwarnings('ignore')

# Import pattern detection modules
from comprehensive_abcd_patterns import detect_unformed_abcd_patterns
from comprehensive_xabcd_patterns import detect_strict_unformed_xabcd_patterns
from gui_compatible_detection import (
    detect_gui_compatible_abcd_patterns,
    detect_gui_compatible_xabcd_patterns,
    detect_all_gui_patterns,
    simulate_gui_display
)
from extremum import detect_extremum_points as find_extremum_points


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

    # Pattern-specific stats
    pattern_performance: Dict[str, Dict] = field(default_factory=dict)
    # Time-based analysis
    monthly_returns: List[float] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class WalkForwardBacktester:
    """
    Walk-forward backtesting engine for harmonic patterns.
    Simulates real-time trading without look-ahead bias.
    """

    def __init__(
        self,
        data: pd.DataFrame,
        initial_capital: float = 10000,
        position_size: float = 0.02,  # 2% risk per trade
        lookback_window: int = 100,  # Bars to look back for pattern detection
        future_buffer: int = 5,  # Bars to leave as buffer (avoid look-ahead)
        min_pattern_score: float = 0.7,  # Minimum confidence score to trade
        max_open_trades: int = 5  # Maximum concurrent trades
    ):
        """
        Initialize the backtester.

        Args:
            data: DataFrame with OHLCV data
            initial_capital: Starting capital
            position_size: Risk per trade as fraction of capital
            lookback_window: Number of bars to analyze for patterns
            future_buffer: Bars to exclude from current time (prevent bias)
            min_pattern_score: Minimum pattern quality score to generate signal
            max_open_trades: Maximum number of concurrent open trades
        """
        self.data = data.copy()
        self.initial_capital = initial_capital
        self.position_size = position_size
        self.lookback_window = lookback_window
        self.future_buffer = future_buffer
        self.min_pattern_score = min_pattern_score
        self.max_open_trades = max_open_trades

        # Trading state
        self.current_capital = initial_capital
        self.open_trades: List[TradeResult] = []
        self.closed_trades: List[TradeResult] = []
        self.all_signals: List[PatternSignal] = []

        # Performance tracking
        self.equity_curve = [initial_capital]
        self.drawdown_curve = []

    def detect_patterns_at_bar(self, current_idx: int) -> Tuple[List[Dict], List[Dict]]:
        """
        Detect patterns using only data available up to current bar.

        Args:
            current_idx: Current bar index in walk-forward simulation

        Returns:
            Tuple of (unformed_patterns, formed_patterns)
        """
        # FIXED: Use ALL historical data up to current point (minus buffer)
        # This ensures we can detect patterns that started long ago
        end_idx = max(0, current_idx - self.future_buffer)

        if end_idx < 20:  # Need minimum data for pattern detection
            return [], []

        # Use all data from beginning up to current point
        data_slice = self.data.iloc[:end_idx].copy()

        # Find extremum points on historical data only
        extremum_points = find_extremum_points(data_slice, length=5)

        if len(extremum_points) < 4:  # Need minimum extremums
            return [], []

        unformed_patterns = []
        formed_patterns = []

        # Detect unformed patterns (signals)
        try:
            # ABCD patterns
            unformed_abcd = detect_unformed_abcd_patterns(
                data_slice,
                extremum_points,
                formed_patterns=[]  # Empty as we're not using GUI patterns
            )
            for pattern in unformed_abcd:
                pattern['pattern_type'] = 'ABCD'
            unformed_patterns.extend(unformed_abcd)

            # XABCD patterns
            unformed_xabcd = detect_strict_unformed_xabcd_patterns(
                extremum_points,
                data_slice,
                formed_patterns=[]
            )
            for pattern in unformed_xabcd:
                pattern['pattern_type'] = 'XABCD'
            unformed_patterns.extend(unformed_xabcd)
        except Exception as e:
            pass  # Silent fail in backtesting

        # Filter unformed patterns - only keep recent ones (C point within last 50 bars)
        filtered_unformed = []
        for pattern in unformed_patterns:
            # Get C point index
            c_idx = pattern.get('C', -1000)
            # Only keep if C is recent (within last 50 bars of our window)
            if c_idx >= end_idx - 50:
                filtered_unformed.append(pattern)
        unformed_patterns = filtered_unformed

        # Detect formed patterns (confirmations)
        try:
            # Formed ABCD
            formed_abcd = detect_gui_compatible_abcd_patterns(extremum_points, data_slice)
            for pattern in formed_abcd:
                pattern['pattern_type'] = 'ABCD'
            formed_patterns.extend(formed_abcd)

            # Formed XABCD
            formed_xabcd = detect_gui_compatible_xabcd_patterns(extremum_points, data_slice)
            for pattern in formed_xabcd:
                pattern['pattern_type'] = 'XABCD'
            formed_patterns.extend(formed_xabcd)
        except Exception as e:
            pass  # Silent fail in backtesting

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
                    # Single level, create zone
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
            pattern_data=pattern
        )

    def calculate_pattern_confidence(self, pattern: Dict) -> float:
        """
        Calculate confidence score for a pattern based on various factors.

        Args:
            pattern: Pattern dictionary

        Returns:
            Confidence score between 0 and 1
        """
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
            score += 0.1  # Gartley patterns are historically reliable
        elif 'bat' in pattern_name:
            score += 0.08
        elif 'butterfly' in pattern_name:
            score += 0.05

        # Check if ratios are within tight tolerance
        if pattern.get('ratio_quality', 0) > 0.9:
            score += 0.1

        # Ensure score is between 0 and 1
        return min(max(score, 0.0), 1.0)

    def check_entry_conditions(self, signal: PatternSignal, current_bar: pd.Series) -> bool:
        """
        Check if price has reached entry zone.

        Args:
            signal: Trading signal
            current_bar: Current OHLCV bar

        Returns:
            True if entry conditions met
        """
        if signal.direction == TradeDirection.LONG:
            # For long, check if low touched PRZ
            return current_bar['Low'] <= signal.entry_price <= current_bar['High']
        else:
            # For short, check if high touched PRZ
            return current_bar['Low'] <= signal.entry_price <= current_bar['High']

    def execute_trade(self, signal: PatternSignal, entry_bar: pd.Series) -> TradeResult:
        """
        Execute a trade based on signal.

        Args:
            signal: Trading signal
            entry_bar: Bar where entry occurs

        Returns:
            TradeResult object
        """
        trade = TradeResult(
            signal=signal,
            entry_time=entry_bar.name
        )

        self.open_trades.append(trade)
        return trade

    def update_open_trades(self, current_bar: pd.Series, current_idx: int, formed_patterns: List[Dict]):
        """
        Update open trades with current bar data.
        Check for stop loss, take profit, or pattern completion.

        Args:
            current_bar: Current OHLCV bar
            current_idx: Current bar index
            formed_patterns: List of formed patterns at current bar
        """
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

            # Check if unformed pattern completed
            if not trade.pattern_completed and formed_patterns:
                trade.pattern_completed = self.check_pattern_completion(
                    trade.signal.pattern_data,
                    formed_patterns
                )

            # Close trade if exit triggered
            if trade.exit_time:
                trade.pnl = self.current_capital * self.position_size * trade.pnl_percent
                trade.trade_duration_bars = current_idx - self.data.index.get_loc(trade.entry_time)

                self.closed_trades.append(trade)
                self.open_trades.remove(trade)
                self.current_capital += trade.pnl

    def check_pattern_completion(self, unformed_pattern: Dict, formed_patterns: List[Dict]) -> bool:
        """
        Check if an unformed pattern has completed (became formed).

        Args:
            unformed_pattern: The original unformed pattern
            formed_patterns: List of currently formed patterns

        Returns:
            True if pattern completed, False otherwise
        """
        # Match based on pattern points and type
        for formed in formed_patterns:
            # Check if same pattern type
            if formed.get('pattern_type') != unformed_pattern.get('pattern_type'):
                continue

            # Check if same pattern name (Gartley, Bat, etc.)
            if formed.get('name', '').split()[0] != unformed_pattern.get('name', '').split()[0]:
                continue

            # For ABCD, check A, B, C points match
            if 'A' in unformed_pattern and 'A' in formed:
                if abs(unformed_pattern['A'] - formed['A']) > 5:  # 5 bar tolerance
                    continue
            if 'B' in unformed_pattern and 'B' in formed:
                if abs(unformed_pattern['B'] - formed['B']) > 5:
                    continue
            if 'C' in unformed_pattern and 'C' in formed:
                if abs(unformed_pattern['C'] - formed['C']) > 5:
                    continue

            # For XABCD, also check X point
            if unformed_pattern.get('pattern_type') == 'XABCD':
                if 'X' in unformed_pattern and 'X' in formed:
                    if abs(unformed_pattern['X'] - formed['X']) > 5:
                        continue

            # Pattern matches
            return True

        return False

    def run_backtest(self, progress_callback=None) -> BacktestStatistics:
        """
        Run the complete backtest simulation.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            BacktestStatistics with complete results
        """
        print(f"\nStarting Walk-Forward Backtest")
        print(f"Data range: {self.data.index[0]} to {self.data.index[-1]}")
        print(f"Total bars: {len(self.data)}")
        print(f"Lookback window: {self.lookback_window}, Future buffer: {self.future_buffer}")
        print(f"Initial capital: ${self.initial_capital:,.2f}")
        print("-" * 60)

        # Reset state
        self.current_capital = self.initial_capital
        self.open_trades = []
        self.closed_trades = []
        self.all_signals = []
        self.equity_curve = [self.initial_capital]

        # Track pending signals (not yet triggered)
        pending_signals = []

        # Walk forward through time
        for idx in range(self.lookback_window, len(self.data)):
            current_bar = self.data.iloc[idx]

            # Update progress
            if progress_callback and idx % 100 == 0:
                progress = (idx / len(self.data)) * 100
                progress_callback(progress)

            # Print progress every 500 bars
            if idx % 500 == 0:
                print(f"Processing bar {idx}/{len(self.data)} ({idx/len(self.data)*100:.1f}%)")

            # Detect patterns with look-ahead protection
            unformed_patterns, formed_patterns = self.detect_patterns_at_bar(idx)

            # Generate signals from unformed patterns
            for pattern in unformed_patterns:
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

        # Calculate statistics
        return self.calculate_statistics()

    def calculate_statistics(self) -> BacktestStatistics:
        """
        Calculate comprehensive backtest statistics.

        Returns:
            BacktestStatistics object
        """
        stats = BacktestStatistics()

        if not self.closed_trades:
            print("\nNo trades executed during backtest period.")
            return stats

        # Basic counts
        stats.total_signals = len(self.all_signals)
        stats.total_trades = len(self.closed_trades)

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

        return stats

    def print_summary(self, stats: BacktestStatistics):
        """Print a formatted summary of backtest results."""

        print("\n" + "="*60)
        print("WALK-FORWARD BACKTEST RESULTS")
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

    def export_results(self, filename: str = "walk_forward_backtest.json"):
        """
        Export backtest results to JSON file.

        Args:
            filename: Output filename
        """
        stats = self.calculate_statistics()

        results = {
            'metadata': {
                'backtest_date': datetime.now().isoformat(),
                'data_range': f"{self.data.index[0]} to {self.data.index[-1]}",
                'total_bars': len(self.data),
                'initial_capital': self.initial_capital,
                'position_size': self.position_size,
                'lookback_window': self.lookback_window,
                'future_buffer': self.future_buffer,
                'min_pattern_score': self.min_pattern_score
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


def run_backtest_example():
    """Example function to demonstrate backtester usage."""

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

    # Initialize backtester
    backtester = WalkForwardBacktester(
        data=data,
        initial_capital=10000,
        position_size=0.02,  # 2% risk per trade
        lookback_window=100,
        future_buffer=5,  # Stop 5 bars before current to avoid bias
        min_pattern_score=0.6,  # Lower threshold for more trades
        max_open_trades=5
    )

    # Run backtest
    print("\nRunning walk-forward backtest...")
    stats = backtester.run_backtest()

    # Print results
    backtester.print_summary(stats)

    # Export detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backtester.export_results(f"walk_forward_backtest_{timestamp}.json")

    return backtester, stats


if __name__ == "__main__":
    backtester, stats = run_backtest_example()