"""
Extremum point detection for harmonic patterns.
Detects ALL high and low points without filtering to ensure maximum pattern coverage.
"""

from typing import List, Tuple
import pandas as pd
import numpy as np


def detect_extremum_points(df: pd.DataFrame, length: int = 1) -> List[Tuple]:
    """
    Detect ALL high and low extremum points from OHLC data.

    This function detects ALL local highs and lows without any filtering
    or alternation requirement. This ensures maximum pattern coverage
    by considering all possible pivot points.

    Args:
        df: DataFrame with OHLC data (must have 'High' and 'Low' columns)
        length: Look-back/forward window for detecting pivots (default 1)

    Returns:
        List of tuples: (timestamp, price, is_high, bar_index)
        where is_high is True for high points, False for low points
        and bar_index is the position in the DataFrame
    """

    extremum_points = []

    # Convert to numpy arrays for faster processing
    # Handle both capitalized and lowercase column names
    high_col = 'High' if 'High' in df.columns else 'high'
    low_col = 'Low' if 'Low' in df.columns else 'low'
    highs = df[high_col].values
    lows = df[low_col].values
    timestamps = df.index.values if isinstance(df.index, pd.DatetimeIndex) else df.index
    n = len(df)

    # Detect ALL high and low pivots
    for i in range(length, n - length):
        # Use numpy operations for window comparisons
        left_window = slice(i-length, i)
        right_window = slice(i+1, i+length+1)

        # Check for high pivot - a local maximum
        is_high_pivot = (
            highs[i] >= np.max(highs[left_window]) and
            highs[i] >= np.max(highs[right_window])
        )

        # Check for low pivot - a local minimum
        is_low_pivot = (
            lows[i] <= np.min(lows[left_window]) and
            lows[i] <= np.min(lows[right_window])
        )

        # Add BOTH high and low pivots if they exist
        # This ensures we capture ALL extremum points
        # Unlike GUI which chooses one, we keep both to allow pattern detection flexibility
        if is_high_pivot:
            extremum_points.append((timestamps[i], highs[i], True, i))

        # Add low pivot separately (not elif) to capture both if they exist on same candle
        if is_low_pivot:
            extremum_points.append((timestamps[i], lows[i], False, i))

    # Sort by date
    extremum_points.sort(key=lambda x: x[0])

    # Count highs and lows for reporting
    high_count = sum(1 for _, _, is_high, _ in extremum_points if is_high)
    low_count = len(extremum_points) - high_count

    return extremum_points