"""
Strict Formed XABCD Pattern Detection
Implements zero-tolerance validation for formed XABCD harmonic patterns
"""

from typing import List, Dict, Tuple
import pandas as pd
from formed_and_unformed_patterns import detect_xabcd_patterns_fast as original_detect


def validate_strict_xabcd_pattern(pattern: Dict, df: pd.DataFrame) -> bool:
    """
    Apply strict price containment validation to a formed XABCD pattern.

    For Bullish patterns (X-Low, A-High, B-Low, C-High, D-Low):
    1. X→A: No candle between X and A has a low that breaks X
    2. A→B: No candle between X and B has a high that exceeds A
    3. B→C: No candle between A and C has a low that breaks B
    4. C→D: No candle between B and D has a high that exceeds C
    5. After D: No candle before D has a low that breaks D

    For Bearish patterns (X-High, A-Low, B-High, C-Low, D-High):
    1. X→A: No candle between X and A has a high that exceeds X
    2. A→B: No candle between X and B has a low that breaks A
    3. B→C: No candle between A and C has a high that exceeds B
    4. C→D: No candle between B and C has a low that breaks C
    5. After D: No candle before D has a high that exceeds D
    """

    try:
        # Extract pattern points
        points = pattern['points']
        x_time = points['X']['time']
        a_time = points['A']['time']
        b_time = points['B']['time']
        c_time = points['C']['time']
        d_time = points['D']['time']

        x_price = points['X']['price']
        a_price = points['A']['price']
        b_price = points['B']['price']
        c_price = points['C']['price']
        d_price = points['D']['price']

        # Get indices in dataframe
        x_idx = df.index.get_loc(x_time)
        a_idx = df.index.get_loc(a_time)
        b_idx = df.index.get_loc(b_time)
        c_idx = df.index.get_loc(c_time)
        d_idx = df.index.get_loc(d_time)

        # Determine pattern type
        is_bullish = pattern['type'] == 'bullish'

        # Column names
        high_col = 'High'
        low_col = 'Low'

        if is_bullish:
            # BULLISH VALIDATION (X-Low, A-High, B-Low, C-High, D-Low)

            # Rule 1: X→A - No low breaks X
            if x_idx < a_idx:
                segment_xa = df.iloc[x_idx:a_idx+1]
                if any(segment_xa[low_col] < x_price):
                    return False

            # Rule 2: X→B - No high exceeds A
            if x_idx < b_idx:
                segment_xb = df.iloc[x_idx:b_idx+1]
                if any(segment_xb[high_col] > a_price):
                    return False

            # Rule 3: A→C - No low breaks B
            if a_idx < c_idx:
                segment_ac = df.iloc[a_idx:c_idx+1]
                if any(segment_ac[low_col] < b_price):
                    return False

            # Rule 4: B→D - No high exceeds C
            if b_idx < d_idx:
                segment_bd = df.iloc[b_idx:d_idx+1]
                if any(segment_bd[high_col] > c_price):
                    return False

            # Rule 5: Before D - No low breaks D
            if d_idx > 0:
                segment_before_d = df.iloc[0:d_idx]
                if any(segment_before_d[low_col] < d_price):
                    return False

        else:
            # BEARISH VALIDATION (X-High, A-Low, B-High, C-Low, D-High)

            # Rule 1: X→A - No high exceeds X
            if x_idx < a_idx:
                segment_xa = df.iloc[x_idx:a_idx+1]
                if any(segment_xa[high_col] > x_price):
                    return False

            # Rule 2: X→B - No low breaks A
            if x_idx < b_idx:
                segment_xb = df.iloc[x_idx:b_idx+1]
                if any(segment_xb[low_col] < a_price):
                    return False

            # Rule 3: A→C - No high exceeds B
            if a_idx < c_idx:
                segment_ac = df.iloc[a_idx:c_idx+1]
                if any(segment_ac[high_col] > b_price):
                    return False

            # Rule 4: B→D - No low breaks C
            if b_idx < d_idx:
                segment_bd = df.iloc[b_idx:d_idx+1]
                if any(segment_bd[low_col] < c_price):
                    return False

            # Rule 5: Before D - No high exceeds D
            if d_idx > 0:
                segment_before_d = df.iloc[0:d_idx]
                if any(segment_before_d[high_col] > d_price):
                    return False

        return True

    except Exception as e:
        print(f"Error validating pattern: {e}")
        return False


def detect_strict_xabcd_patterns(
    extremum_points: List[Tuple],
    df: pd.DataFrame,
    log_details: bool = False,
    max_patterns: int = None,
    max_search_window: int = None
) -> List[Dict]:
    """
    Detect strict formed XABCD patterns with zero-tolerance validation.

    Args:
        extremum_points: List of detected extremum points
        df: Full dataframe with OHLC data
        log_details: Enable detailed logging
        max_patterns: Maximum number of patterns to return
        max_search_window: Maximum search window for pattern detection

    Returns:
        List of validated strict XABCD patterns
    """

    # First get all potential XABCD patterns using original detection
    all_patterns = original_detect(extremum_points, log_details)

    if log_details:
        print(f"Found {len(all_patterns)} potential XABCD patterns")

    # Apply strict validation
    strict_patterns = []
    for pattern in all_patterns:
        if validate_strict_xabcd_pattern(pattern, df):
            strict_patterns.append(pattern)

            if max_patterns and len(strict_patterns) >= max_patterns:
                break

    if log_details:
        print(f"After strict validation: {len(strict_patterns)} patterns remain")

    # Add strict flag to patterns
    for pattern in strict_patterns:
        pattern['strict_validated'] = True

    return strict_patterns