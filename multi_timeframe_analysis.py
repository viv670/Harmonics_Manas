"""
Multi-Timeframe Pattern Analysis

Detect and analyze harmonic patterns across multiple timeframes simultaneously.

Features:
- Detect patterns on 1m, 5m, 15m, 1h, 4h, 1d timeframes
- Pattern confluence detection (same pattern on multiple TFs)
- Higher timeframe bias analysis
- Multi-TF signal strength scoring
- Automatic timeframe correlation

Benefits:
- Higher probability setups
- Better context for pattern strength
- Confluence-based entry signals
- Multi-TF trend alignment
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import yfinance as yf


@dataclass
class TimeframePattern:
    """Pattern detected on a specific timeframe"""
    timeframe: str
    pattern_name: str
    pattern_type: str  # 'bullish' or 'bearish'
    direction: str
    points: Dict
    ratios: Dict
    prz_zone: Dict
    quality_score: int = 0
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class MultiTimeframeSignal:
    """Signal with multi-timeframe context"""
    symbol: str
    primary_timeframe: str
    primary_pattern: TimeframePattern
    supporting_patterns: List[TimeframePattern] = field(default_factory=list)
    confluence_score: float = 0.0
    higher_tf_bias: str = 'neutral'  # 'bullish', 'bearish', 'neutral'
    signal_strength: str = 'weak'  # 'weak', 'moderate', 'strong', 'very_strong'

    def calculate_confluence(self) -> float:
        """Calculate confluence score based on supporting patterns"""
        if not self.supporting_patterns:
            return 0.0

        # Score based on number of supporting patterns
        base_score = min(len(self.supporting_patterns) * 20, 60)

        # Bonus for same direction patterns
        same_direction = sum(1 for p in self.supporting_patterns
                           if p.direction == self.primary_pattern.direction)
        direction_bonus = (same_direction / len(self.supporting_patterns)) * 20

        # Bonus for higher timeframe patterns
        higher_tf_patterns = sum(1 for p in self.supporting_patterns
                                if self._is_higher_timeframe(p.timeframe, self.primary_timeframe))
        htf_bonus = min(higher_tf_patterns * 10, 20)

        total_score = base_score + direction_bonus + htf_bonus
        return min(total_score, 100.0)

    def _is_higher_timeframe(self, tf1: str, tf2: str) -> bool:
        """Check if tf1 is higher than tf2"""
        tf_order = ['1m', '5m', '15m', '30m', '1h', '4h', '12h', '1d', '1w', '1M']
        try:
            return tf_order.index(tf1) > tf_order.index(tf2)
        except ValueError:
            return False

    def determine_signal_strength(self):
        """Determine overall signal strength"""
        confluence = self.confluence_score

        if confluence >= 75:
            self.signal_strength = 'very_strong'
        elif confluence >= 50:
            self.signal_strength = 'strong'
        elif confluence >= 25:
            self.signal_strength = 'moderate'
        else:
            self.signal_strength = 'weak'


class MultiTimeframeAnalyzer:
    """
    Analyze patterns across multiple timeframes.

    Detects confluence, higher timeframe bias, and multi-TF signal strength.
    """

    # Standard timeframe intervals
    TIMEFRAMES = {
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '1h': '1h',
        '4h': '4h',
        '12h': '12h',
        '1d': '1d',
        '1w': '1wk',
        '1M': '1mo'
    }

    def __init__(self, pattern_detector=None):
        """
        Initialize multi-timeframe analyzer.

        Args:
            pattern_detector: Pattern detection function/class
        """
        self.pattern_detector = pattern_detector
        self.timeframe_data = {}
        self.detected_patterns = {}

    def load_timeframe_data(self, symbol: str, timeframes: List[str],
                           period: str = '1mo') -> Dict[str, pd.DataFrame]:
        """
        Load data for multiple timeframes.

        Args:
            symbol: Trading symbol
            timeframes: List of timeframes to load
            period: Data period (e.g., '1mo', '3mo', '1y')

        Returns:
            Dictionary mapping timeframe to DataFrame
        """
        data = {}

        for tf in timeframes:
            if tf not in self.TIMEFRAMES:
                print(f"Unknown timeframe: {tf}, skipping...")
                continue

            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=period, interval=self.TIMEFRAMES[tf])

                if not df.empty:
                    data[tf] = df
                    print(f"Loaded {tf} data: {len(df)} bars")
                else:
                    print(f"No data for {tf}")

            except Exception as e:
                print(f"Error loading {tf} data: {e}")

        self.timeframe_data = data
        return data

    def detect_patterns_multi_tf(self, symbol: str, timeframes: List[str],
                                 detection_func) -> Dict[str, List[TimeframePattern]]:
        """
        Detect patterns across multiple timeframes.

        Args:
            symbol: Trading symbol
            timeframes: List of timeframes
            detection_func: Pattern detection function

        Returns:
            Dictionary mapping timeframe to list of patterns
        """
        all_patterns = {}

        for tf in timeframes:
            if tf not in self.timeframe_data:
                print(f"No data for {tf}, skipping pattern detection")
                continue

            df = self.timeframe_data[tf]

            try:
                # Detect patterns on this timeframe
                patterns = detection_func(df)

                # Convert to TimeframePattern objects
                tf_patterns = []
                for pattern in patterns:
                    tf_pattern = TimeframePattern(
                        timeframe=tf,
                        pattern_name=pattern.get('name', 'Unknown'),
                        pattern_type=pattern.get('pattern_type', 'ABCD'),
                        direction=pattern.get('type', 'unknown'),
                        points=pattern.get('points', {}),
                        ratios=pattern.get('ratios', {}),
                        prz_zone=pattern.get('prz_zone', {}),
                        quality_score=pattern.get('quality_score', 0)
                    )
                    tf_patterns.append(tf_pattern)

                all_patterns[tf] = tf_patterns
                print(f"{tf}: Found {len(tf_patterns)} patterns")

            except Exception as e:
                print(f"Error detecting patterns on {tf}: {e}")
                all_patterns[tf] = []

        self.detected_patterns = all_patterns
        return all_patterns

    def find_confluence_signals(self, primary_tf: str,
                               supporting_tfs: List[str] = None) -> List[MultiTimeframeSignal]:
        """
        Find signals with multi-timeframe confluence.

        Args:
            primary_tf: Primary timeframe for signals
            supporting_tfs: Supporting timeframes (default: all higher TFs)

        Returns:
            List of multi-timeframe signals with confluence
        """
        if primary_tf not in self.detected_patterns:
            return []

        # Default to all higher timeframes
        if supporting_tfs is None:
            tf_order = list(self.TIMEFRAMES.keys())
            primary_idx = tf_order.index(primary_tf)
            supporting_tfs = tf_order[primary_idx + 1:]

        signals = []
        primary_patterns = self.detected_patterns[primary_tf]

        for primary_pattern in primary_patterns:
            # Find supporting patterns
            supporting_patterns = []

            for sup_tf in supporting_tfs:
                if sup_tf not in self.detected_patterns:
                    continue

                for pattern in self.detected_patterns[sup_tf]:
                    # Check if patterns align (same direction)
                    if pattern.direction == primary_pattern.direction:
                        # Check if pattern zones overlap
                        if self._patterns_overlap(primary_pattern, pattern):
                            supporting_patterns.append(pattern)

            # Create signal
            signal = MultiTimeframeSignal(
                symbol=self.symbol,
                primary_timeframe=primary_tf,
                primary_pattern=primary_pattern,
                supporting_patterns=supporting_patterns
            )

            # Calculate confluence and strength
            signal.confluence_score = signal.calculate_confluence()
            signal.higher_tf_bias = self._get_higher_tf_bias(supporting_patterns)
            signal.determine_signal_strength()

            signals.append(signal)

        # Sort by confluence score
        signals.sort(key=lambda s: s.confluence_score, reverse=True)

        return signals

    def _patterns_overlap(self, pattern1: TimeframePattern,
                         pattern2: TimeframePattern) -> bool:
        """Check if two patterns overlap in price"""
        try:
            # Get PRZ zones
            prz1 = pattern1.prz_zone
            prz2 = pattern2.prz_zone

            if not prz1 or not prz2:
                return False

            # Extract price ranges
            prz1_low = min(prz1.get('low', float('inf')), prz1.get('high', float('inf')))
            prz1_high = max(prz1.get('low', 0), prz1.get('high', 0))

            prz2_low = min(prz2.get('low', float('inf')), prz2.get('high', float('inf')))
            prz2_high = max(prz2.get('low', 0), prz2.get('high', 0))

            # Check overlap
            return not (prz1_high < prz2_low or prz2_high < prz1_low)

        except (KeyError, TypeError):
            return False

    def _get_higher_tf_bias(self, supporting_patterns: List[TimeframePattern]) -> str:
        """Determine higher timeframe bias"""
        if not supporting_patterns:
            return 'neutral'

        bullish = sum(1 for p in supporting_patterns if p.direction == 'bullish')
        bearish = sum(1 for p in supporting_patterns if p.direction == 'bearish')

        if bullish > bearish * 1.5:
            return 'bullish'
        elif bearish > bullish * 1.5:
            return 'bearish'
        else:
            return 'neutral'

    def get_higher_tf_trend(self, timeframe: str, lookback: int = 50) -> str:
        """
        Get trend direction on higher timeframe.

        Args:
            timeframe: Timeframe to analyze
            lookback: Number of bars to analyze

        Returns:
            'bullish', 'bearish', or 'neutral'
        """
        if timeframe not in self.timeframe_data:
            return 'neutral'

        df = self.timeframe_data[timeframe]

        if len(df) < lookback:
            return 'neutral'

        # Use moving average crossover
        ma_fast = df['Close'].rolling(window=20).mean()
        ma_slow = df['Close'].rolling(window=50).mean()

        if ma_fast.iloc[-1] > ma_slow.iloc[-1]:
            return 'bullish'
        elif ma_fast.iloc[-1] < ma_slow.iloc[-1]:
            return 'bearish'
        else:
            return 'neutral'

    def generate_report(self, signals: List[MultiTimeframeSignal]) -> str:
        """Generate text report of multi-TF analysis"""
        report = []
        report.append("=" * 60)
        report.append("MULTI-TIMEFRAME PATTERN ANALYSIS REPORT")
        report.append("=" * 60)
        report.append("")

        for i, signal in enumerate(signals, 1):
            report.append(f"{i}. {signal.primary_pattern.pattern_name}")
            report.append(f"   Primary TF: {signal.primary_timeframe}")
            report.append(f"   Direction: {signal.primary_pattern.direction.upper()}")
            report.append(f"   Confluence Score: {signal.confluence_score:.1f}/100")
            report.append(f"   Signal Strength: {signal.signal_strength.upper()}")
            report.append(f"   Higher TF Bias: {signal.higher_tf_bias.upper()}")

            if signal.supporting_patterns:
                report.append(f"   Supporting Patterns ({len(signal.supporting_patterns)}):")
                for pattern in signal.supporting_patterns:
                    report.append(f"     - {pattern.timeframe}: {pattern.pattern_name}")

            report.append("")

        if not signals:
            report.append("No patterns with confluence detected.")

        report.append("=" * 60)

        return "\n".join(report)


def analyze_symbol_multi_tf(symbol: str, primary_tf: str = '1h',
                            supporting_tfs: List[str] = None,
                            detection_func=None) -> List[MultiTimeframeSignal]:
    """
    Convenience function for multi-timeframe analysis.

    Args:
        symbol: Trading symbol
        primary_tf: Primary timeframe
        supporting_tfs: Supporting timeframes
        detection_func: Pattern detection function

    Returns:
        List of multi-timeframe signals
    """
    if supporting_tfs is None:
        supporting_tfs = ['4h', '1d']

    analyzer = MultiTimeframeAnalyzer()

    # Load data
    all_tfs = [primary_tf] + supporting_tfs
    analyzer.load_timeframe_data(symbol, all_tfs)

    # Detect patterns
    if detection_func:
        analyzer.detect_patterns_multi_tf(symbol, all_tfs, detection_func)

    # Find confluence
    signals = analyzer.find_confluence_signals(primary_tf, supporting_tfs)

    return signals


if __name__ == "__main__":
    print("Testing Multi-Timeframe Analysis...")
    print()

    # Example usage
    symbol = "AAPL"

    # Mock pattern detection function
    def mock_detect_patterns(df):
        """Mock pattern detection for testing"""
        patterns = []

        if len(df) > 50:
            # Create a mock pattern
            pattern = {
                'name': 'Gartley_bull',
                'pattern_type': 'XABCD',
                'type': 'bullish',
                'points': {
                    'X': {'time': df.index[-50], 'price': df['Low'].iloc[-50]},
                    'A': {'time': df.index[-40], 'price': df['High'].iloc[-40]},
                    'B': {'time': df.index[-30], 'price': df['Low'].iloc[-30]},
                    'C': {'time': df.index[-20], 'price': df['High'].iloc[-20]},
                    'D': {'time': df.index[-10], 'price': df['Low'].iloc[-10]}
                },
                'ratios': {'bc_retracement': 61.8, 'cd_projection': 127.2},
                'prz_zone': {
                    'low': df['Low'].iloc[-10] * 0.99,
                    'high': df['Low'].iloc[-10] * 1.01
                },
                'quality_score': 75
            }
            patterns.append(pattern)

        return patterns

    # Run analysis
    print(f"Analyzing {symbol} across multiple timeframes...")
    print()

    analyzer = MultiTimeframeAnalyzer()

    # Load data
    timeframes = ['1h', '4h', '1d']
    analyzer.symbol = symbol
    analyzer.load_timeframe_data(symbol, timeframes, period='3mo')

    # Detect patterns
    if analyzer.timeframe_data:
        analyzer.detect_patterns_multi_tf(symbol, timeframes, mock_detect_patterns)

        # Find confluence signals
        signals = analyzer.find_confluence_signals('1h', ['4h', '1d'])

        # Generate report
        report = analyzer.generate_report(signals)
        print(report)

    print()
    print("✅ Multi-timeframe analysis tool ready!")
