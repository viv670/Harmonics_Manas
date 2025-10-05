"""
Unformed ABCD Pattern Detection Module
Detects incomplete ABCD patterns (3-point patterns A-B-C with projected D)

This module provides:
1. Unformed ABCD patterns with projected D points
2. Strict price containment validation
3. PRZ (Potential Reversal Zone) calculation
4. Optimized performance with pattern lookup
"""

from typing import List, Tuple, Dict, Set, Optional
import pandas as pd
import numpy as np
import threading
import time
from pattern_ratios_2_Final import ABCD_PATTERN_RATIOS
from pattern_data_standard import StandardPattern, PatternPoint, standardize_pattern_name, fix_unicode_issues

# Configuration constants
EPSILON = 1e-10
MAX_FUTURE_CANDLES = 100
DEFAULT_MAX_PATTERNS = 100
DEFAULT_SEARCH_WINDOW = 30
PRICE_TOLERANCE = 0.1


class PatternLookup:
    """Thread-safe pre-computed pattern lookup tables for O(1) access"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if not self._initialized:
                self.bull_patterns = {}
                self.bear_patterns = {}
                self._build_lookup_tables()
                self._initialized = True

    def _build_lookup_tables(self):
        """Pre-compute pattern ranges for fast lookup"""
        for pattern_name, ratios in ABCD_PATTERN_RATIOS.items():
            retr_range = ratios['retr']
            proj_range = ratios['proj']

            pattern_data = {
                'name': pattern_name,
                'retr_min': retr_range[0],
                'retr_max': retr_range[1],
                'proj_min': proj_range[0],
                'proj_max': proj_range[1]
            }

            if 'bull' in pattern_name:
                self.bull_patterns[pattern_name] = pattern_data
            else:
                self.bear_patterns[pattern_name] = pattern_data

    def find_matching_patterns(self, bc_retracement: float, is_bullish: bool) -> List[Dict]:
        """Fast O(1) pattern matching using pre-computed tables"""
        patterns = self.bull_patterns if is_bullish else self.bear_patterns
        matches = []

        for pattern_name, data in patterns.items():
            if data['retr_min'] <= bc_retracement <= data['retr_max']:
                matches.append(data)

        return matches


# Global pattern lookup instance
PATTERN_LOOKUP = PatternLookup()


def validate_price_containment_bullish(df: pd.DataFrame,
                                      a_idx: int, b_idx: int,
                                      c_idx: int, d_idx: Optional[int],
                                      a_price: float, b_price: float,
                                      c_price: float, d_price: Optional[float] = None) -> bool:
    """
    Validate price containment for bullish patterns.
    Works for unformed patterns (without D).

    Bullish: A(High) -> B(Low) -> C(High) -> D(Low)

    Rules:
    1. A->B: No candle between A and B has a high that exceeds A
    2. B->C: No candle between A and C has a low that breaks B
    3. C->D (if D exists): No candle between B and D has a high that exceeds C
    """
    # Assertions for 100% accuracy
    assert df is not None, "DataFrame cannot be None for validation"
    assert isinstance(a_idx, (int, np.integer)), f"a_idx must be integer, got {type(a_idx)}"
    assert isinstance(b_idx, (int, np.integer)), f"b_idx must be integer, got {type(b_idx)}"
    assert isinstance(c_idx, (int, np.integer)), f"c_idx must be integer, got {type(c_idx)}"
    assert 0 <= a_idx < len(df), f"a_idx {a_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= b_idx < len(df), f"b_idx {b_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= c_idx < len(df), f"c_idx {c_idx} out of bounds (0-{len(df)-1})"
    assert a_idx <= b_idx <= c_idx, f"Invalid index order: A({a_idx}) <= B({b_idx}) <= C({c_idx})"

    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Check A to B: no high exceeds A (excluding A itself)
        if a_idx + 1 < b_idx:
            segment_ab = df.iloc[a_idx+1:b_idx+1]
            if any(segment_ab[high_col] > a_price):
                return False

        # Check A to C: no low breaks B (excluding A, including B and C)
        if a_idx + 1 < c_idx:
            segment_ac = df.iloc[a_idx+1:c_idx+1]
            if any(segment_ac[low_col] < b_price):
                return False

        # Check B to C: no high exceeds C (excluding C itself, as C IS the high)
        if b_idx < c_idx:
            segment_bc = df.iloc[b_idx:c_idx]
            if any(segment_bc[high_col] > c_price):
                return False

        # Post-C validation REMOVED: Price can move above C before reaching D zone
        # Pattern invalidation is handled by the tracking system, not detection

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.error(f"Validation error in validate_price_containment_bullish: {e}")
        # For 100% accuracy, treat errors as validation failures
        return False


def validate_price_containment_bearish(df: pd.DataFrame,
                                      a_idx: int, b_idx: int,
                                      c_idx: int, d_idx: Optional[int],
                                      a_price: float, b_price: float,
                                      c_price: float, d_price: Optional[float] = None) -> bool:
    """
    Validate price containment for bearish patterns.
    Works for unformed patterns (without D).

    Bearish: A(Low) -> B(High) -> C(Low) -> D(High)

    Rules:
    1. A->B: No candle between A and B has a low that breaks A
    2. B->C: No candle between A and C has a high that exceeds B
    3. C->D (if D exists): No candle between B and D has a low that breaks C
    """
    # Assertions for 100% accuracy
    assert df is not None, "DataFrame cannot be None for validation"
    assert isinstance(a_idx, (int, np.integer)), f"a_idx must be integer, got {type(a_idx)}"
    assert isinstance(b_idx, (int, np.integer)), f"b_idx must be integer, got {type(b_idx)}"
    assert isinstance(c_idx, (int, np.integer)), f"c_idx must be integer, got {type(c_idx)}"
    assert 0 <= a_idx < len(df), f"a_idx {a_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= b_idx < len(df), f"b_idx {b_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= c_idx < len(df), f"c_idx {c_idx} out of bounds (0-{len(df)-1})"
    assert a_idx <= b_idx <= c_idx, f"Invalid index order: A({a_idx}) <= B({b_idx}) <= C({c_idx})"

    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Check A to B: no low breaks A (excluding A itself)
        if a_idx + 1 < b_idx:
            segment_ab = df.iloc[a_idx+1:b_idx+1]
            if any(segment_ab[low_col] < a_price):
                return False

        # Check A to C: no high exceeds B (excluding A, including B and C)
        if a_idx + 1 < c_idx:
            segment_ac = df.iloc[a_idx+1:c_idx+1]
            if any(segment_ac[high_col] > b_price):
                return False

        # Check B to C: no low breaks C (excluding C itself, as C IS the low)
        if b_idx < c_idx:
            segment_bc = df.iloc[b_idx:c_idx]
            if any(segment_bc[low_col] < c_price):
                return False

        # Post-C validation REMOVED: Price can move below C before reaching D zone
        # Pattern invalidation is handled by the tracking system, not detection

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.error(f"Validation error in validate_price_containment_bearish: {e}")
        # For 100% accuracy, treat errors as validation failures
        return False


def _is_valid_abc_pattern(A: Tuple, B: Tuple, C: Tuple) -> bool:
    """Fast validation of ABC pattern structure"""
    # Check alternating pattern
    if A[2] != C[2] or A[2] == B[2] or B[2] == C[2]:
        return False

    # Validate price relationships
    a_price, b_price, c_price = A[1], B[1], C[1]
    is_bullish = A[2]

    if is_bullish:
        return a_price > b_price and c_price > b_price and c_price < a_price
    else:
        return a_price < b_price and c_price < b_price and c_price > a_price


def _process_abc_combination_optimized(A: Tuple, B: Tuple, C: Tuple, signature: Tuple, validation_type: str = "strict_containment") -> Optional[Dict]:
    """Process valid ABC combination and calculate PRZ zones"""
    is_bullish = A[2]

    # Calculate ratios
    AB = abs(B[1] - A[1])
    BC = abs(C[1] - B[1])

    if AB == 0 or BC == 0:
        return None

    bc_retracement = (BC / (AB + EPSILON)) * 100

    # Find matching patterns
    matching_patterns_data = PATTERN_LOOKUP.find_matching_patterns(bc_retracement, is_bullish)

    if not matching_patterns_data:
        return None

    # Calculate PRZ zones for all matching patterns
    comprehensive_prz_zones = []
    matching_pattern_names = []

    for pattern_data in matching_patterns_data:
        pattern_name = pattern_data['name']
        proj_min, proj_max = pattern_data['proj_min'], pattern_data['proj_max']

        matching_pattern_names.append(pattern_name)

        # Calculate PRZ zone
        if is_bullish:
            prz_min = C[1] - (BC * proj_max / 100)
            prz_max = C[1] - (BC * proj_min / 100)
        else:
            prz_min = C[1] + (BC * proj_min / 100)
            prz_max = C[1] + (BC * proj_max / 100)

        comprehensive_prz_zones.append({
            'min': prz_min,
            'max': prz_max,
            'proj_min': proj_min,
            'proj_max': proj_max,
            'pattern_source': pattern_name
        })

    # Sort PRZ zones by price
    comprehensive_prz_zones.sort(key=lambda x: x['min'])

    # Use first matching pattern as base name
    base_name = matching_pattern_names[0]

    return {
        'name': f"{base_name}_unformed",
        'type': 'bullish' if is_bullish else 'bearish',
        'points': {
            'A': {'time': A[0], 'price': A[1]},
            'B': {'time': B[0], 'price': B[1]},
            'C': {'time': C[0], 'price': C[1]},
            'D_projected': {'prz_zones': comprehensive_prz_zones}
        },
        'ratios': {
            'bc_retracement': bc_retracement,
            'matching_patterns': matching_pattern_names,
            'prz_zones': comprehensive_prz_zones
        },
        'indices': {
            'A': A[3] if len(A) > 3 else signature[0],  # Use bar_index from extremum tuple
            'B': B[3] if len(B) > 3 else signature[1],
            'C': C[3] if len(C) > 3 else signature[2]
        },
        'quality_score': len(matching_pattern_names),
        'validation': validation_type
    }


def detect_unformed_abcd_patterns_optimized(extremum_points: List[Tuple],
                                           df: Optional[pd.DataFrame] = None,
                                           log_details: bool = False,
                                           max_patterns: int = None,
                                           max_search_window: int = None,
                                           strict_validation: bool = True) -> List[Dict]:
    """
    Detect unformed ABCD patterns (3-point patterns with projected D).

    Args:
        extremum_points: List of tuples (timestamp, price, is_high, bar_index)
        df: Optional DataFrame for strict validation
        log_details: Whether to print detailed logs
        max_patterns: Maximum number of patterns to return
        max_search_window: Maximum distance between pattern points
        strict_validation: Whether to apply strict price containment for A-B-C

    Returns:
        List of dictionaries containing unformed ABCD patterns with PRZ zones
    """

    if len(extremum_points) < 3:
        return []

    n = len(extremum_points)
    patterns = []
    processed_combinations = set()

    # ==================== SEARCH WINDOW CONFIGURATION ====================
    # max_search_window controls how far apart pattern points can be:
    # - None = unlimited (search entire dataset)
    # - Number = maximum distance between points
    # ======================================================================
    if max_search_window is None:
        # Unlimited mode - search all combinations
        search_window_j = n
        search_window_k = n
    else:
        # Limited mode - restrict search distance
        search_window_j = min(max_search_window, n)
        search_window_k = min(max_search_window, n)

    # Prepare DataFrame for validation if needed
    df_copy = None
    if strict_validation:
        # Assert DataFrame is provided when strict validation is enabled
        assert df is not None, "DataFrame is required for strict validation"
        assert not df.empty, "DataFrame cannot be empty for strict validation"
        df_copy = df.copy()
        if 'timestamp' not in df_copy.columns:
            if isinstance(df_copy.index, pd.DatetimeIndex):
                df_copy.reset_index(inplace=True)
                df_copy['timestamp'] = pd.to_datetime(df_copy.iloc[:, 0])
            elif 'Date' in df_copy.columns:
                df_copy['timestamp'] = pd.to_datetime(df_copy['Date'])
            elif 'time' in df_copy.columns:
                df_copy['timestamp'] = pd.to_datetime(df_copy['time'])

    if log_details:
        print(f"\nDetecting Unformed ABCD patterns with {n} extremum points")
        print(f"Search window: J={search_window_j}, K={search_window_k}")
        print(f"Strict validation: {strict_validation}")
        print(f"Max patterns: {max_patterns}")
        import sys
        sys.stdout.flush()

    patterns_checked = 0
    patterns_rejected = 0

    # OPTIMIZATION: Cache C point crossing checks
    high_col = 'High' if df_copy is not None and 'High' in df_copy.columns else 'high'
    low_col = 'Low' if df_copy is not None and 'Low' in df_copy.columns else 'low'
    c_point_crossing_cache = {}  # (c_idx, c_price, is_bullish) -> bool

    # Track time for timeout
    start_time = time.time()
    timeout = 10  # 10 second timeout for GUI responsiveness

    # Process all points in the limited dataset
    for i in range(n - 3, -1, -1):  # Process all points provided
        # Check for timeout
        if time.time() - start_time > timeout:
            if log_details:
                print(f"TIMEOUT: Detection taking too long (>{timeout}s), returning early with {len(patterns)} patterns")
            break

        # Limit search for B to reasonable window (by bar index, not extremum index)
        j_end = n - 1

        for j in range(i + 1, j_end):  # Check all j points
            B = extremum_points[j]

            # Skip if B is beyond search window (measured in bar indices)
            if max_search_window is not None:
                A_bar = extremum_points[i][3]
                B_bar = B[3]
                if B_bar - A_bar > max_search_window:
                    continue

            # Limit search for C to reasonable window (by bar index, not extremum index)
            k_end = n

            for k in range(j + 1, k_end):  # Check all k points
                C = extremum_points[k]

                # Skip if C is beyond search window (measured in bar indices)
                if max_search_window is not None:
                    B_bar = B[3]
                    C_bar = C[3]
                    if C_bar - B_bar > max_search_window:
                        continue

                A = extremum_points[i]

                # Check that no two points share the same timestamp
                # (prevents same candle from being both high and low)
                if A[0] == B[0] or B[0] == C[0] or A[0] == C[0]:
                    continue

                # Check alternating pattern
                if not _is_valid_abc_pattern(A, B, C):
                    continue

                # Avoid duplicate processing
                # Use bar indices AND is_high flag to differentiate high vs low at same bar
                # When extremum=1, same bar can appear twice (as high and low)
                # Signature includes is_high to distinguish them
                signature = (A[3], A[2], B[3], B[2], C[3], C[2])  # (bar_idx, is_high) for each point

                if signature in processed_combinations:
                    if log_details and A[3] == 252:
                        print(f"  SKIPPED DUPLICATE: A={A[3]} ({A[2]}), B={B[3]} ({B[2]}), C={C[3]} ({C[2]})")
                    continue
                processed_combinations.add(signature)

                if log_details and A[3] == 252:
                    print(f"  CHECKING: A={A[3]} ({A[2]}), B={B[3]} ({B[2]}), C={C[3]} ({C[2]})")

                patterns_checked += 1

                # Apply strict validation if enabled
                validation_type = "strict_containment"  # Always use strict_containment
                if strict_validation and df_copy is not None:
                    try:
                        # Use bar indices directly from extremum points
                        a_candle_idx = A[3]
                        b_candle_idx = B[3]
                        c_candle_idx = C[3]

                        # Skip if indices are the same (same candle)
                        if a_candle_idx == b_candle_idx or b_candle_idx == c_candle_idx or a_candle_idx == c_candle_idx:
                            patterns_rejected += 1
                            continue

                        if None not in [a_candle_idx, b_candle_idx, c_candle_idx]:
                            is_bullish = A[2]  # A is HIGH for bullish

                            # Validate A-B-C price containment
                            if is_bullish:
                                containment_valid = validate_price_containment_bullish(
                                    df_copy, a_candle_idx, b_candle_idx, c_candle_idx, None,
                                    A[1], B[1], C[1], None
                                )
                            else:
                                containment_valid = validate_price_containment_bearish(
                                    df_copy, a_candle_idx, b_candle_idx, c_candle_idx, None,
                                    A[1], B[1], C[1], None
                                )

                            if not containment_valid:
                                patterns_rejected += 1

                                # Comprehensive logging for rejected patterns
                                if log_details and patterns_rejected % 100 == 0:
                                    pattern_type = "Bullish" if is_bullish else "Bearish"
                                    print(f"  {patterns_rejected} patterns rejected due to price containment violations")

                                continue

                            # Validate that price doesn't cross C point after formation
                            # Check all bars after C to ensure C point integrity
                            if c_candle_idx < len(df_copy) - 1:
                                high_col = 'High' if 'High' in df_copy.columns else 'high'
                                low_col = 'Low' if 'Low' in df_copy.columns else 'low'

                                c_point_crossed = False
                                if is_bullish:
                                    # For bullish: C is a high, check if any bar after C goes above C
                                    max_high_after = df_copy[high_col].iloc[c_candle_idx+1:].max()
                                    if max_high_after > C[1]:  # C[1] is C price
                                        c_point_crossed = True
                                else:
                                    # For bearish: C is a low, check if any bar after C goes below C
                                    min_low_after = df_copy[low_col].iloc[c_candle_idx+1:].min()
                                    if min_low_after < C[1]:  # C[1] is C price
                                        c_point_crossed = True

                                if c_point_crossed:
                                    patterns_rejected += 1
                                    if log_details:
                                        print(f"  Rejected pattern: C point crossed after formation")
                                    continue

                    except Exception as e:
                        # ALWAYS reject pattern on validation error for 100% accuracy
                        patterns_rejected += 1

                        # Log validation errors
                        if log_details:
                            print(f"Pattern rejected due to validation error: {e}")
                            import traceback
                            traceback.print_exc()

                        # CRITICAL: Continue to next pattern, DON'T process this one
                        continue

                # Process the valid ABC combination
                pattern_data = _process_abc_combination_optimized(A, B, C, signature, validation_type)
                if pattern_data:
                    patterns.append(pattern_data)

                    # Check if we've found enough patterns
                    if max_patterns and len(patterns) >= max_patterns:
                        if log_details:
                            print(f"  Reached max_patterns limit ({max_patterns})")
                        return patterns[:max_patterns]

                    if log_details and len(patterns) % 10 == 0:
                        print(f"  Found {len(patterns)} unformed patterns...")

    # Sort patterns by quality
    patterns.sort(key=lambda p: (
        len(p['ratios']['matching_patterns']),
        -abs(p['ratios']['bc_retracement'] - 50)
    ), reverse=True)

    if log_details:
        print(f"\nUnformed ABCD Summary:")
        print(f"  Checked: {patterns_checked} combinations")
        print(f"  Found: {len(patterns)} valid patterns")
        if strict_validation:
            print(f"  Rejected: {patterns_rejected} (price violations)")

    return patterns[:max_patterns] if max_patterns else patterns


def detect_unformed_abcd_patterns(extremum_points: List[Tuple],
                                 df: Optional[pd.DataFrame] = None,
                                 log_details: bool = False,
                                 max_search_window: Optional[int] = None,
                                 backtest_mode: bool = False) -> List[Dict]:
    """
    Main entry point for unformed ABCD pattern detection.

    Args:
        extremum_points: List of tuples (timestamp, price, is_high, bar_index)
        df: DataFrame with OHLC data for validation
        log_details: Whether to print detailed logs
        max_search_window: Maximum distance between pattern points (None = unlimited)
        backtest_mode: Whether in backtesting mode (unused, for compatibility)

    Returns:
        List of unformed ABCD patterns
    """
    # Call the optimized version with appropriate settings
    return detect_unformed_abcd_patterns_optimized(
        extremum_points,
        df=df,
        log_details=log_details,
        max_patterns=None,  # No limit for complete detection
        max_search_window=max_search_window,
        strict_validation=True  # Always enable strict validation
    )


# Alias for backward compatibility
detect_strict_unformed_abcd_patterns = detect_unformed_abcd_patterns


if __name__ == "__main__":
    # Test the unformed detection
    print("Testing Unformed ABCD Pattern Detection...")

    # Create test data
    import pandas as pd

    df = pd.DataFrame({
        'Date': pd.date_range('2024-01-01', periods=100),
        'High': np.random.randn(100).cumsum() + 100,
        'Low': np.random.randn(100).cumsum() + 95,
        'Close': np.random.randn(100).cumsum() + 97
    })

    # Create some extremum points
    extremum_points = [
        (df.Date[10], 100, True, 10),   # High
        (df.Date[20], 95, False, 20),   # Low
        (df.Date[30], 98, True, 30),    # High
        (df.Date[40], 93, False, 40),   # Low
    ]

    patterns = detect_unformed_abcd_patterns(
        extremum_points,
        df=df,
        log_details=True
    )

    print(f"\nFound {len(patterns)} unformed ABCD patterns")