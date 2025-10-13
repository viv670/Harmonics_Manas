"""
Smart XABCD Detection - Adaptive Algorithm Selection
=====================================================

Automatically selects the best XABCD implementation based on dataset size:
- Small datasets (n < 60): Original O(n⁵) with early optimizations
- Large datasets (n >= 60): O(n³) meet-in-the-middle algorithm

Performance characteristics:
- n < 60:  Original is competitive due to early termination optimizations
- n >= 60: O(n³) provides 3-4x speedup
- n >= 100: O(n³) provides 10-100x speedup
- n >= 150: O(n³) provides 100-1000x speedup

Author: Generated for Harmonics Trading System
Date: 2025-10-09
"""

from typing import List, Tuple, Dict, Optional
import pandas as pd


# Adaptive threshold - can be adjusted based on performance testing
ADAPTIVE_THRESHOLD = 60  # Switch to O(n³) for n >= 60


def detect_xabcd_patterns_smart(extremum_points: List[Tuple],
                                 df: pd.DataFrame = None,
                                 log_details: bool = False,
                                 strict_validation: bool = True,
                                 max_search_window: Optional[int] = None,
                                 validate_d_crossing: bool = True) -> List[Dict]:
    """
    Smart XABCD detection with automatic algorithm selection.

    Automatically selects between:
    - Original O(n⁵) implementation: Best for small extremum sets (n < 60)
    - O(n³) optimized implementation: Best for large extremum sets (n >= 60)

    Args:
        extremum_points: List of (timestamp, price, is_high, bar_index)
        df: DataFrame for validation (required for strict_validation)
        log_details: Print progress and algorithm selection
        strict_validation: Apply price containment validation
        max_search_window: Max distance between points (None = unlimited)
        validate_d_crossing: Validate D point crossing

    Returns:
        List of pattern dictionaries with structure:
        {
            'name': str,              # Pattern name (e.g., 'Gartley_bull')
            'type': str,              # 'bullish' or 'bearish'
            'pattern_type': str,      # 'XABCD'
            'points': {               # Pattern points with time/price/index
                'X': {'time': float, 'price': float, 'index': int},
                'A': {...}, 'B': {...}, 'C': {...}, 'D': {...}
            },
            'indices': {              # Bar indices
                'X': int, 'A': int, 'B': int, 'C': int, 'D': int
            },
            'ratios': {               # Fibonacci ratios
                'ab_xa': float,       # AB/XA ratio (%)
                'bc_ab': float,       # BC/AB ratio (%)
                'cd_bc': float,       # CD/BC ratio (%)
                'ad_xa': float        # AD/XA ratio (%)
            }
        }

    Example:
        >>> from extremum import detect_extremum_points
        >>> extremum = detect_extremum_points(df, length=3)
        >>> patterns = detect_xabcd_patterns_smart(extremum, df)
        >>> print(f"Found {len(patterns)} XABCD patterns")
    """
    n = len(extremum_points)

    # Handle edge case
    if n < 5:
        if log_details:
            print(f"[Smart XABCD] Insufficient extremum points: {n} (need 5)")
        return []

    # Adaptive algorithm selection
    if n >= ADAPTIVE_THRESHOLD:
        # Use O(n³) for large datasets
        from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3

        if log_details:
            print(f"[Smart XABCD] Using O(n³) algorithm for n={n} extremum points")
            print(f"[Smart XABCD] Expected 3-100x speedup vs original")

        return detect_xabcd_patterns_o_n3(
            extremum_points, df, log_details,
            strict_validation, max_search_window, validate_d_crossing
        )
    else:
        # Use original for small datasets
        from formed_xabcd import detect_xabcd_patterns

        if log_details:
            print(f"[Smart XABCD] Using original algorithm for n={n} extremum points")
            print(f"[Smart XABCD] Original is efficient for small n due to early optimizations")

        return detect_xabcd_patterns(
            extremum_points, df, log_details,
            strict_validation, max_search_window, validate_d_crossing
        )


def detect_xabcd_patterns_force_original(extremum_points: List[Tuple],
                                          df: pd.DataFrame = None,
                                          log_details: bool = False,
                                          strict_validation: bool = True,
                                          max_search_window: Optional[int] = None,
                                          validate_d_crossing: bool = True) -> List[Dict]:
    """
    Force use of original O(n⁵) implementation.

    Use this if you need to compare results or troubleshoot.
    Generally, use detect_xabcd_patterns_smart() instead.
    """
    from formed_xabcd import detect_xabcd_patterns
    return detect_xabcd_patterns(
        extremum_points, df, log_details,
        strict_validation, max_search_window, validate_d_crossing
    )


def detect_xabcd_patterns_force_optimized(extremum_points: List[Tuple],
                                           df: pd.DataFrame = None,
                                           log_details: bool = False,
                                           strict_validation: bool = True,
                                           max_search_window: Optional[int] = None,
                                           validate_d_crossing: bool = True) -> List[Dict]:
    """
    Force use of O(n³) optimized implementation.

    Use this if you want to always use the optimized version,
    even for small n. Generally, use detect_xabcd_patterns_smart() instead.
    """
    from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3
    return detect_xabcd_patterns_o_n3(
        extremum_points, df, log_details,
        strict_validation, max_search_window, validate_d_crossing
    )


# Default export - use the smart adaptive version
detect_xabcd_patterns = detect_xabcd_patterns_smart


# For backward compatibility and explicit imports
__all__ = [
    'detect_xabcd_patterns',
    'detect_xabcd_patterns_smart',
    'detect_xabcd_patterns_force_original',
    'detect_xabcd_patterns_force_optimized',
    'ADAPTIVE_THRESHOLD'
]
