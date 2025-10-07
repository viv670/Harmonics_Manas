"""
Pattern Strength Scoring System
Evaluates pattern quality based on multiple factors

Scoring Components (0-100 scale):
1. Ratio Precision (0-30 pts) - How close to ideal Fibonacci ratios
2. Volume Confirmation (0-20 pts) - Volume profile at pattern points
3. Trend Alignment (0-20 pts) - Alignment with higher timeframe trend
4. Price Cleanliness (0-15 pts) - Clean formation without violations
5. Time Symmetry (0-15 pts) - Balanced time between points

Benefits:
- Filter low-quality patterns
- Prioritize high-probability setups
- Objective pattern ranking
- Backtest optimization
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import timedelta


class PatternStrengthScorer:
    """
    Score pattern quality based on multiple factors.

    Uses a comprehensive scoring system to rank patterns from 0-100.
    """

    # Ideal Fibonacci ratios for common patterns
    IDEAL_RATIOS = {
        'Gartley': {'retr': 61.8, 'proj': 127.2},
        'Butterfly': {'retr': 78.6, 'proj': 161.8},
        'Bat': {'retr': 38.2, 'proj': 88.6},
        'Crab': {'retr': 38.2, 'proj': 161.8},
        'Shark': {'retr': 88.6, 'proj': 113.0},
    }

    def __init__(self):
        pass

    def score_pattern(self, pattern: Dict, df: pd.DataFrame) -> int:
        """
        Calculate comprehensive quality score for a pattern.

        Args:
            pattern: Pattern dictionary with points and ratios
            df: OHLC DataFrame for context

        Returns:
            Score from 0-100
        """
        score = 0

        # Component 1: Ratio Precision (0-30 points)
        score += self._score_ratio_precision(pattern)

        # Component 2: Volume Confirmation (0-20 points)
        score += self._score_volume_confirmation(pattern, df)

        # Component 3: Trend Alignment (0-20 points)
        score += self._score_trend_alignment(pattern, df)

        # Component 4: Price Cleanliness (0-15 points)
        score += self._score_price_cleanliness(pattern, df)

        # Component 5: Time Symmetry (0-15 points)
        score += self._score_time_symmetry(pattern)

        return min(100, max(0, int(score)))

    def _score_ratio_precision(self, pattern: Dict) -> float:
        """
        Score how close ratios are to ideal values (0-30 points).

        Closer to ideal ratios = higher score
        """
        ratios = pattern.get('ratios', {})
        pattern_name = pattern.get('name', '')

        # Extract pattern type from name
        pattern_type = None
        for ptype in self.IDEAL_RATIOS.keys():
            if ptype in pattern_name:
                pattern_type = ptype
                break

        if not pattern_type or pattern_type not in self.IDEAL_RATIOS:
            # Unknown pattern type - score based on standard ranges
            return 15.0  # Average score

        ideal = self.IDEAL_RATIOS[pattern_type]
        score = 0

        # Score retracement ratio
        if 'bc_retracement' in ratios:
            retr = ratios['bc_retracement']
            ideal_retr = ideal['retr']
            deviation = abs(retr - ideal_retr)

            # Score inversely proportional to deviation
            # Max 15 points for perfect match, 0 for >30% deviation
            retr_score = max(0, 15 - (deviation / 2))
            score += retr_score

        # Score projection ratio
        if 'cd_projection' in ratios:
            proj = ratios['cd_projection']
            ideal_proj = ideal['proj']
            deviation = abs(proj - ideal_proj)

            # Max 15 points for perfect match
            proj_score = max(0, 15 - (deviation / 3))
            score += proj_score

        return score

    def _score_volume_confirmation(self, pattern: Dict, df: pd.DataFrame) -> float:
        """
        Score based on volume profile (0-20 points).

        Good volume confirmation:
        - High volume at point D (reversal)
        - Decreasing volume into PRZ
        - Volume spike at reversal point
        """
        if 'Volume' not in df.columns and 'volume' not in df.columns:
            return 10.0  # Neutral score if no volume data

        volume_col = 'Volume' if 'Volume' in df.columns else 'volume'
        points = pattern.get('points', {})

        score = 0

        try:
            # Get average volume
            avg_volume = df[volume_col].rolling(window=20).mean()

            # Check if this is ABCD or XABCD
            if 'D' in points:
                # Formed pattern - check actual D point volume
                d_time = points['D']['time']
                d_idx = df.index.get_loc(d_time) if hasattr(df.index, 'get_loc') else None

                if d_idx is not None:
                    d_volume = df[volume_col].iloc[d_idx]
                    avg_vol = avg_volume.iloc[d_idx]

                    # High volume at D (reversal point) is good
                    if d_volume > avg_vol * 1.5:
                        score += 10
                    elif d_volume > avg_vol:
                        score += 5

            # Check C point volume
            if 'C' in points:
                c_time = points['C']['time']
                c_idx = df.index.get_loc(c_time) if hasattr(df.index, 'get_loc') else None

                if c_idx is not None:
                    c_volume = df[volume_col].iloc[c_idx]
                    avg_vol = avg_volume.iloc[c_idx]

                    # Lower volume approaching C is good (shows exhaustion)
                    if c_volume < avg_vol * 0.8:
                        score += 10
                    elif c_volume < avg_vol:
                        score += 5

        except (KeyError, IndexError, ValueError):
            return 10.0  # Neutral score on error

        return score

    def _score_trend_alignment(self, pattern: Dict, df: pd.DataFrame) -> float:
        """
        Score based on trend alignment (0-20 points).

        Patterns aligned with higher timeframe trend score higher.
        """
        points = pattern.get('points', {})
        direction = pattern.get('type', 'unknown')

        score = 0

        try:
            # Calculate trend using moving averages
            if len(df) < 50:
                return 10.0  # Not enough data

            # Use 20 and 50 period moving averages
            ma_20 = df['Close'].rolling(window=20).mean()
            ma_50 = df['Close'].rolling(window=50).mean()

            # Get current trend (bullish if MA20 > MA50)
            is_uptrend = ma_20.iloc[-1] > ma_50.iloc[-1]

            # Bullish pattern in uptrend = good
            # Bearish pattern in downtrend = good
            if (direction == 'bullish' and is_uptrend) or \
               (direction == 'bearish' and not is_uptrend):
                score += 20
            else:
                score += 5  # Counter-trend pattern (lower score)

        except (KeyError, IndexError, ValueError):
            return 10.0

        return score

    def _score_price_cleanliness(self, pattern: Dict, df: pd.DataFrame) -> float:
        """
        Score based on price action cleanliness (0-15 points).

        Clean patterns have:
        - No false breakouts
        - Clear swings
        - Minimal wicks
        """
        points = pattern.get('points', {})
        score = 15.0  # Start with perfect score

        try:
            # Check each point for excessive wicks
            for point_name, point_data in points.items():
                if point_name in ['A', 'B', 'C', 'D']:
                    point_time = point_data.get('time')
                    if point_time is None:
                        continue

                    point_idx = df.index.get_loc(point_time) if hasattr(df.index, 'get_loc') else None
                    if point_idx is None:
                        continue

                    # Get candle data
                    candle = df.iloc[point_idx]
                    high, low, open_p, close = candle['High'], candle['Low'], candle['Open'], candle['Close']

                    # Calculate body and wick sizes
                    body_size = abs(close - open_p)
                    total_range = high - low

                    if total_range > 0:
                        body_ratio = body_size / total_range

                        # Penalize if body is less than 30% of total range (big wicks)
                        if body_ratio < 0.3:
                            score -= 3

        except (KeyError, IndexError, ValueError):
            pass

        return max(0, score)

    def _score_time_symmetry(self, pattern: Dict) -> float:
        """
        Score based on time symmetry (0-15 points).

        Symmetric patterns (balanced time between points) score higher.
        """
        points = pattern.get('points', {})
        score = 0

        try:
            # Get timestamps for points
            times = []
            point_names = []

            for point_name in ['X', 'A', 'B', 'C', 'D']:
                if point_name in points:
                    time = points[point_name].get('time')
                    if time is not None:
                        times.append(pd.Timestamp(time))
                        point_names.append(point_name)

            if len(times) < 3:
                return 7.5  # Not enough points

            # Calculate time intervals
            intervals = []
            for i in range(len(times) - 1):
                interval = (times[i+1] - times[i]).total_seconds()
                intervals.append(interval)

            if len(intervals) < 2:
                return 7.5

            # Calculate coefficient of variation (lower is more symmetric)
            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals)

            if mean_interval > 0:
                cv = std_interval / mean_interval

                # Score: cv = 0 (perfect) = 15 points
                # cv = 1 (high variance) = 0 points
                score = max(0, 15 * (1 - min(1, cv)))

        except (KeyError, ValueError, AttributeError):
            return 7.5  # Neutral score on error

        return score

    def get_score_breakdown(self, pattern: Dict, df: pd.DataFrame) -> Dict[str, float]:
        """
        Get detailed score breakdown for analysis.

        Args:
            pattern: Pattern dictionary
            df: OHLC DataFrame

        Returns:
            Dictionary with score for each component
        """
        return {
            'ratio_precision': self._score_ratio_precision(pattern),
            'volume_confirmation': self._score_volume_confirmation(pattern, df),
            'trend_alignment': self._score_trend_alignment(pattern, df),
            'price_cleanliness': self._score_price_cleanliness(pattern, df),
            'time_symmetry': self._score_time_symmetry(pattern),
            'total': self.score_pattern(pattern, df)
        }


def filter_patterns_by_score(patterns: List[Dict], df: pd.DataFrame,
                            min_score: int = 50) -> List[Dict]:
    """
    Filter patterns by minimum quality score.

    Args:
        patterns: List of pattern dictionaries
        df: OHLC DataFrame
        min_score: Minimum acceptable score (0-100)

    Returns:
        Filtered list of high-quality patterns
    """
    scorer = PatternStrengthScorer()
    scored_patterns = []

    for pattern in patterns:
        score = scorer.score_pattern(pattern, df)
        if score >= min_score:
            pattern['quality_score'] = score
            scored_patterns.append(pattern)

    # Sort by score (highest first)
    scored_patterns.sort(key=lambda p: p.get('quality_score', 0), reverse=True)

    return scored_patterns


if __name__ == "__main__":
    print("Testing Pattern Strength Scoring System...")
    print()

    # Create test data
    dates = pd.date_range('2024-01-01', periods=100)
    test_df = pd.DataFrame({
        'High': np.random.randn(100).cumsum() + 100,
        'Low': np.random.randn(100).cumsum() + 95,
        'Open': np.random.randn(100).cumsum() + 97,
        'Close': np.random.randn(100).cumsum() + 98,
        'Volume': np.random.randint(1000, 10000, 100)
    }, index=dates)

    # Create test pattern
    test_pattern = {
        'name': 'Gartley_bull',
        'type': 'bullish',
        'points': {
            'A': {'time': dates[10], 'price': 100},
            'B': {'time': dates[20], 'price': 95},
            'C': {'time': dates[30], 'price': 98},
            'D': {'time': dates[40], 'price': 96}
        },
        'ratios': {
            'bc_retracement': 61.8,
            'cd_projection': 127.2
        }
    }

    # Score the pattern
    scorer = PatternStrengthScorer()
    score = scorer.score_pattern(test_pattern, test_df)
    breakdown = scorer.get_score_breakdown(test_pattern, test_df)

    print(f"Pattern: {test_pattern['name']}")
    print(f"Total Score: {score}/100")
    print()
    print("Score Breakdown:")
    for component, value in breakdown.items():
        if component != 'total':
            print(f"  {component.replace('_', ' ').title()}: {value:.1f}")

    print()
    print("✅ Pattern scoring system ready!")
