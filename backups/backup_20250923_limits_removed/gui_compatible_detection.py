"""
GUI-Compatible Pattern Detection
================================
This module provides detection functions that match the GUI's exact behavior,
including proper timestamp conversion for strict pattern validation.
"""

import pandas as pd
from typing import List, Tuple, Dict, Any
from strict_abcd_patterns import detect_strict_abcd_patterns
from strict_xabcd_patterns import detect_strict_xabcd_patterns


def convert_extremums_to_timestamps(extremums: List[Tuple], df: pd.DataFrame) -> List[Tuple]:
    """
    Convert extremum points with integer indices to actual DataFrame timestamps.

    This fixes the critical issue where extremum detection returns integer indices
    but strict validation expects actual timestamps.

    Args:
        extremums: List of tuples (index, price, is_high) from detect_extremum_points
        df: DataFrame with Date column containing timestamps

    Returns:
        List of tuples (timestamp, price, is_high) for strict validation
    """
    converted_extremums = []

    for idx, price, is_high in extremums:
        # Map integer index to actual DataFrame timestamp
        if idx < len(df):
            actual_timestamp = df.iloc[idx]['Date']
            converted_extremums.append((actual_timestamp, price, is_high))
        else:
            print(f"Warning: extremum index {idx} is out of bounds for DataFrame length {len(df)}")

    return converted_extremums


def detect_gui_compatible_abcd_patterns(extremums: List[Tuple],
                                      df: pd.DataFrame,
                                      log_details: bool = False,
                                      max_patterns: int = None) -> List[Dict]:
    """
    Detect ABCD patterns using the exact same method as the GUI.

    This function:
    1. Converts extremum indices to timestamps (fixing the critical bug)
    2. Calls strict_abcd_patterns with proper parameters
    3. Returns patterns that match GUI display exactly

    Args:
        extremums: Raw extremum points from detect_extremum_points
        df: DataFrame with OHLC data and Date column
        log_details: Whether to print detailed logs
        max_patterns: Maximum number of patterns to return (None = no limit)

    Returns:
        List of ABCD pattern dictionaries matching GUI format
    """
    # Convert integer indices to timestamps
    timestamp_extremums = convert_extremums_to_timestamps(extremums, df)

    # Call strict detection with converted timestamps
    return detect_strict_abcd_patterns(
        timestamp_extremums,
        df,
        log_details=log_details,
        max_patterns=max_patterns
    )


def detect_gui_compatible_xabcd_patterns(extremums: List[Tuple],
                                       df: pd.DataFrame,
                                       log_details: bool = False,
                                       max_patterns: int = None,
                                       max_window: int = None) -> List[Dict]:
    """
    Detect XABCD patterns using the exact same method as the GUI.

    IMPORTANT: Unlike ABCD patterns, XABCD patterns expect raw integer indices,
    NOT converted timestamps. This is why we use the raw extremums directly.

    Args:
        extremums: Raw extremum points from detect_extremum_points (with integer indices)
        df: DataFrame with OHLC data and Date column
        log_details: Whether to print detailed logs
        max_patterns: Maximum number of patterns to return (None = no limit)
        max_window: Maximum search window for pattern combinations (None = no limit)

    Returns:
        List of XABCD pattern dictionaries matching GUI format
    """
    # XABCD detection uses raw integer indices directly (unlike ABCD)
    return detect_strict_xabcd_patterns(
        extremums,  # Use raw extremums with integer indices
        df,
        log_details=log_details,
        max_patterns=max_patterns,
        max_window=max_window
    )


def detect_all_gui_patterns(extremums: List[Tuple],
                          df: pd.DataFrame,
                          log_details: bool = False,
                          max_patterns: int = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Detect both ABCD and XABCD patterns exactly as the GUI does.

    This is the main function that should be used by backtesting systems
    to get consistent results with the GUI display.

    Args:
        extremums: Raw extremum points from detect_extremum_points
        df: DataFrame with OHLC data and Date column
        log_details: Whether to print detailed logs
        max_patterns: Maximum number of patterns per type (None = no limit)

    Returns:
        Tuple of (abcd_patterns, xabcd_patterns) matching GUI exactly
    """
    # Get patterns using GUI-compatible methods
    abcd_patterns = detect_gui_compatible_abcd_patterns(
        extremums, df, log_details, max_patterns
    )

    xabcd_patterns = detect_gui_compatible_xabcd_patterns(
        extremums, df, log_details, max_patterns
    )

    return abcd_patterns, xabcd_patterns


def simulate_gui_display(extremums: List[Tuple],
                        df: pd.DataFrame,
                        display_limit: int = None) -> List[Dict]:
    """
    Simulate the exact GUI display logic including sorting and limiting.

    This function replicates the complete GUI pattern display pipeline:
    1. Detect patterns using strict methods
    2. Combine ABCD and XABCD patterns
    3. Sort by C point timestamp (most recent first)
    4. Apply display limit

    Args:
        extremums: Raw extremum points from detect_extremum_points
        df: DataFrame with OHLC data and Date column
        display_limit: Maximum patterns to display (None = no limit)

    Returns:
        List of patterns exactly as shown in GUI
    """
    # Get all patterns using GUI methods
    abcd_patterns, xabcd_patterns = detect_all_gui_patterns(extremums, df)

    # Combine patterns
    all_patterns = abcd_patterns + xabcd_patterns

    # Sort by C point timestamp (most recent first) - same as GUI
    def get_c_timestamp(pattern):
        if 'points' in pattern and 'C' in pattern['points']:
            c_point = pattern['points']['C']
            if isinstance(c_point, dict) and 'timestamp' in c_point:
                return pd.to_datetime(c_point['timestamp'])
            elif isinstance(c_point, dict) and 'index' in c_point:
                return c_point['index']  # Fallback to index
        return 0

    sorted_patterns = sorted(all_patterns, key=get_c_timestamp, reverse=True)

    # Apply display limit (if any)
    gui_displayed = sorted_patterns[:display_limit] if display_limit else sorted_patterns

    return gui_displayed