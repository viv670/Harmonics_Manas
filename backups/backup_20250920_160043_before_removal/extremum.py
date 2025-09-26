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
        List of tuples: (timestamp, price, is_high)
        where is_high is True for high points, False for low points
    """

    extremum_points = []

    # Convert to numpy arrays for faster processing
    highs = df['High'].values
    lows = df['Low'].values
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
        if is_high_pivot:
            extremum_points.append((timestamps[i], highs[i], True))

        # Add low pivot separately (not elif) to capture both if they exist on same candle
        if is_low_pivot:
            extremum_points.append((timestamps[i], lows[i], False))

    # Sort by date
    extremum_points.sort(key=lambda x: x[0])

    # Count highs and lows for reporting
    high_count = sum(1 for _, _, is_high in extremum_points if is_high)
    low_count = len(extremum_points) - high_count

    print(f"Detected {len(extremum_points)} total extremum points:")
    print(f"  - {high_count} high points")
    print(f"  - {low_count} low points")
    print(f"  - Total: {high_count + low_count} points")

    return extremum_points


def detect_alternating_extremum_points(df: pd.DataFrame, length: int = 1) -> List[Tuple]:
    """
    Detect extremum points with alternating high/low pattern.

    This is the traditional approach that ensures alternating highs and lows
    by keeping only the most extreme point when consecutive points of the
    same type are found.

    Args:
        df: DataFrame with OHLC data
        length: Look-back/forward window for detecting pivots

    Returns:
        List of alternating extremum points
    """

    # First get all extremum points
    all_points = detect_extremum_points(df, length)

    if len(all_points) <= 1:
        return all_points

    # Clean up to ensure alternating pattern
    cleaned = []
    i = 0

    while i < len(all_points):
        current = all_points[i]
        cleaned.append(current)

        # Look ahead for consecutive points of the same type
        j = i + 1
        while j < len(all_points) and all_points[j][2] == current[2]:
            # Same type (both highs or both lows)
            if current[2]:  # Both are highs
                # Keep the higher high
                if all_points[j][1] > current[1]:
                    cleaned[-1] = all_points[j]  # Replace with higher high
                    current = all_points[j]
            else:  # Both are lows
                # Keep the lower low
                if all_points[j][1] < current[1]:
                    cleaned[-1] = all_points[j]  # Replace with lower low
                    current = all_points[j]
            j += 1

        i = j  # Skip the consecutive points we just processed

    print(f"After alternation cleanup: {len(cleaned)} points")

    return cleaned