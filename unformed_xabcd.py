"""
Comprehensive XABCD Pattern Detection System
Detects strict unformed XABCD patterns with comprehensive price containment validation

This module provides:
1. Unformed XABCD patterns (4-point patterns X-A-B-C with projected D)
2. Strict price containment validation between all segments
3. Horizontal line calculation for projected D points (not PRZ zones)
4. Optimized performance with pattern lookup
5. Validation that price doesn't violate C after formation
6. Unified pattern data structure for compatibility
"""

from typing import List, Tuple, Dict, Set, Optional
import pandas as pd
import numpy as np
import threading
from pattern_ratios_2_Final import XABCD_PATTERN_RATIOS
from pattern_data_standard import StandardPattern, PatternPoint, standardize_pattern_name, fix_unicode_issues

# Configuration constants
EPSILON = 1e-10
MAX_FUTURE_CANDLES = 100
DEFAULT_MAX_PATTERNS = 50
DEFAULT_SEARCH_WINDOW = 30
PRICE_TOLERANCE = 0.1


class XABCDPatternLookup:
    """Thread-safe pre-computed XABCD pattern lookup tables for O(1) access"""

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
        for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
            ab_xa_range = ratios['ab_xa']
            bc_ab_range = ratios['bc_ab']
            cd_bc_range = ratios['cd_bc']
            ad_xa_range = ratios['ad_xa']

            pattern_data = {
                'name': pattern_name,
                'ab_xa_min': ab_xa_range[0],
                'ab_xa_max': ab_xa_range[1],
                'bc_ab_min': bc_ab_range[0],
                'bc_ab_max': bc_ab_range[1],
                'cd_bc_min': cd_bc_range[0],
                'cd_bc_max': cd_bc_range[1],
                'ad_xa_min': ad_xa_range[0],
                'ad_xa_max': ad_xa_range[1]
            }

            if 'bull' in pattern_name:
                self.bull_patterns[pattern_name] = pattern_data
            else:
                self.bear_patterns[pattern_name] = pattern_data

    def find_matching_patterns(self, ab_xa: float, bc_ab: float, is_bullish: bool) -> List[Dict]:
        """Fast O(1) pattern matching using pre-computed tables"""
        patterns = self.bull_patterns if is_bullish else self.bear_patterns
        matches = []

        for pattern_name, data in patterns.items():
            if (data['ab_xa_min'] <= ab_xa <= data['ab_xa_max'] and
                data['bc_ab_min'] <= bc_ab <= data['bc_ab_max']):
                matches.append(data)

        return matches


# Global pattern lookup instance
XABCD_PATTERN_LOOKUP = XABCDPatternLookup()


def validate_price_containment_bullish_xabcd(df: pd.DataFrame,
                                            x_idx: int, a_idx: int, b_idx: int, c_idx: int,
                                            x_price: float, a_price: float,
                                            b_price: float, c_price: float) -> bool:
    """
    Validate price containment for bullish XABCD patterns (unformed, 4 points).

    Bullish: X(Low) -> A(High) -> B(Low) -> C(High)

    Validation rules for pattern structure (X-A-B-C only):
    1. X should be the lowest point between X and A
    2. A should be the highest point between X and B
    3. B should be > X and the lowest point between A and C
    4. C should be the highest point between B and C

    Note: C can be updated to new extremum highs - this is handled by pattern tracking.
    Structure break dismissal REMOVED - formed pattern detection with ratio validation
    handles pattern quality filtering. Price crossing B often forms point D.
    """
    # Assert required parameters are valid
    assert df is not None and not df.empty, "DataFrame is required for validation"
    assert x_idx is not None, "X index is required"
    assert a_idx is not None, "A index is required"
    assert b_idx is not None, "B index is required"
    assert c_idx is not None, "C index is required"

    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Rule 1: X should be the lowest between X-A (excluding X itself)
        if x_idx + 1 < a_idx:
            segment_xa = df.iloc[x_idx+1:a_idx+1]
            if any(segment_xa[low_col] < x_price):
                return False  # Found a lower low than X

        # Rule 2: A should be the highest between X-B (excluding A itself)
        if x_idx < b_idx:
            segment_xb = df.iloc[x_idx:b_idx]
            if any(segment_xb[high_col] > a_price):
                return False  # Found a higher high than A

        # Rule 3a: B should be greater than X
        if b_price <= x_price:
            return False  # B must be higher than X

        # Rule 3b: B should be the lowest between A-C (excluding B where it's the low)
        if a_idx < c_idx:
            segment_ac = df.iloc[a_idx:c_idx+1]
            if any(segment_ac[low_col] < b_price):
                return False  # Found a lower low than B

        # Rule 4: C should be the highest between B-C (excluding C itself)
        if b_idx < c_idx:
            segment_bc = df.iloc[b_idx:c_idx]
            if any(segment_bc[high_col] > c_price):
                return False  # Found a higher high than C

        # Rule 5 REMOVED: No post-C validation for unformed patterns
        # Price can move above C before reaching D zone - this is normal pattern behavior
        # Pattern invalidation is handled by the tracking system, not detection

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.error(f"CRITICAL: Pattern rejected due to validation error in validate_price_containment_bullish_xabcd: {e}")
        # CRITICAL: Always reject pattern on error - never pass invalid patterns
        return False


def validate_price_containment_bearish_xabcd(df: pd.DataFrame,
                                           x_idx: int, a_idx: int, b_idx: int, c_idx: int,
                                           x_price: float, a_price: float,
                                           b_price: float, c_price: float) -> bool:
    """
    Validate price containment for bearish XABCD patterns (unformed, 4 points).

    Bearish: X(High) -> A(Low) -> B(High) -> C(Low)

    Validation rules for pattern structure (X-A-B-C only):
    1. X should be the highest point between X and A
    2. A should be the lowest point between X and B
    3. B should be < X and the highest point between A and C
    4. C should be the lowest point between B and C

    Note: C can be updated to new extremum lows - this is handled by pattern tracking.
    Structure break dismissal REMOVED - formed pattern detection with ratio validation
    handles pattern quality filtering. Price crossing B often forms point D.
    """
    # Assert required parameters are valid
    assert df is not None and not df.empty, "DataFrame is required for validation"
    assert x_idx is not None, "X index is required"
    assert a_idx is not None, "A index is required"
    assert b_idx is not None, "B index is required"
    assert c_idx is not None, "C index is required"

    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Rule 1: X should be the highest between X-A (excluding X itself)
        if x_idx + 1 < a_idx:
            segment_xa = df.iloc[x_idx+1:a_idx+1]
            if any(segment_xa[high_col] > x_price):
                return False  # Found a higher high than X

        # Rule 2: A should be the lowest between X-B (excluding A itself)
        if x_idx < b_idx:
            segment_xb = df.iloc[x_idx:b_idx]
            if any(segment_xb[low_col] < a_price):
                return False  # Found a lower low than A

        # Rule 3a: B should be less than X
        if b_price >= x_price:
            return False  # B must be lower than X

        # Rule 3b: B should be the highest between A-C (excluding B where it's the high)
        if a_idx < c_idx:
            segment_ac = df.iloc[a_idx:c_idx+1]
            if any(segment_ac[high_col] > b_price):
                return False  # Found a higher high than B

        # Rule 4: C should be the lowest between B-C (excluding C itself)
        if b_idx < c_idx:
            segment_bc = df.iloc[b_idx:c_idx]
            if any(segment_bc[low_col] < c_price):
                return False  # Found a lower low than C

        # Rule 5 REMOVED: No post-C validation for unformed patterns
        # Price can move below C before reaching D zone - this is normal pattern behavior
        # Pattern invalidation is handled by the tracking system, not detection

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.error(f"CRITICAL: Pattern rejected due to validation error in validate_price_containment_bearish_xabcd: {e}")
        # CRITICAL: Always reject pattern on error - never pass invalid patterns
        return False




def validate_d_lines_no_candlestick_crossing(df: pd.DataFrame, c_idx: int, d_lines: List[float]) -> List[float]:
    """
    Optimized validation that horizontal D projection lines don't cross any candlesticks after point C.
    Uses vectorized operations for better performance.

    Args:
        df: DataFrame with OHLC data
        c_idx: Index of point C in the DataFrame
        d_lines: List of projected D price levels

    Returns:
        List of valid D lines that don't cross candlesticks
    """
    if not d_lines or c_idx >= len(df) - 1:
        return d_lines

    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Get candles after point C (limited to MAX_FUTURE_CANDLES)
        end_idx = min(c_idx + 1 + MAX_FUTURE_CANDLES, len(df))
        candles_after_c = df.iloc[c_idx + 1:end_idx]

        # Extract arrays for vectorized operations
        highs = candles_after_c[high_col].values
        lows = candles_after_c[low_col].values

        valid_d_lines = []

        for d_price in d_lines:
            # Vectorized check if d_price crosses any candlestick
            crosses_candle = np.any((lows <= d_price) & (d_price <= highs))

            if not crosses_candle:
                valid_d_lines.append(d_price)

        return valid_d_lines

    except (KeyError, IndexError, TypeError) as e:
        import logging
        logging.error(f"CRITICAL: D line validation failed, rejecting all lines: {e}")
        # CRITICAL: Return empty list on error - no D lines are valid if validation fails
        return []


def calculate_horizontal_d_lines(x_price: float, a_price: float, b_price: float, c_price: float,
                                pattern_data: Dict, is_bullish: bool) -> List[float]:
    """
    Calculate horizontal D lines for XABCD patterns (not PRZ zones)

    Returns list of horizontal price levels where D could complete
    """
    d_lines = []

    # Calculate moves
    xa_move = abs(a_price - x_price)
    bc_move = abs(c_price - b_price)

    if xa_move == 0 or bc_move == 0:
        return []

    # Get ranges
    ad_min, ad_max = pattern_data['ad_xa_min'], pattern_data['ad_xa_max']
    cd_min, cd_max = pattern_data['cd_bc_min'], pattern_data['cd_bc_max']

    # Calculate averages
    ad_avg = (ad_min + ad_max) / 2
    cd_avg = (cd_min + cd_max) / 2

    # Method 1: Fix AD ratios, then clamp with CD ratios
    for ad_ratio in [ad_avg, ad_max, ad_min]:
        projected_ad = xa_move * (ad_ratio / 100)
        if is_bullish:
            d_from_ad = a_price - projected_ad  # D below A
        else:
            d_from_ad = a_price + projected_ad  # D above A

        # Now validate/clamp with CD ratio
        cd_move_implied = abs(d_from_ad - c_price)
        if bc_move > 0:
            cd_ratio_implied = (cd_move_implied / bc_move) * 100
            # Clamp CD ratio to valid range
            cd_ratio_clamped = max(cd_min, min(cd_max, cd_ratio_implied))
            # Recalculate D with clamped CD ratio
            projected_cd_clamped = bc_move * (cd_ratio_clamped / 100)
            if is_bullish:
                d_final = c_price - projected_cd_clamped  # D below C
            else:
                d_final = c_price + projected_cd_clamped  # D above C
        else:
            d_final = d_from_ad

        d_lines.append(d_final)

    # Method 2: Fix CD ratios, then clamp with AD ratios
    for cd_ratio in [cd_avg, cd_max, cd_min]:
        projected_cd = bc_move * (cd_ratio / 100)
        if is_bullish:
            d_from_cd = c_price - projected_cd  # D below C
        else:
            d_from_cd = c_price + projected_cd  # D above C

        # Now validate/clamp with AD ratio
        ad_move_implied = abs(a_price - d_from_cd)
        if xa_move > 0:
            ad_ratio_implied = (ad_move_implied / xa_move) * 100
            # Clamp AD ratio to valid range
            ad_ratio_clamped = max(ad_min, min(ad_max, ad_ratio_implied))
            # Recalculate D with clamped AD ratio
            projected_ad_clamped = xa_move * (ad_ratio_clamped / 100)
            if is_bullish:
                d_final = a_price - projected_ad_clamped  # D below A
            else:
                d_final = a_price + projected_ad_clamped  # D above A
        else:
            d_final = d_from_cd

        d_lines.append(d_final)

    # Remove duplicates (within 0.1 tolerance)
    unique_d_lines = []
    for d_price in d_lines:
        is_duplicate = any(abs(d_price - existing) < 0.1 for existing in unique_d_lines)
        if not is_duplicate:
            unique_d_lines.append(d_price)

    return unique_d_lines


def detect_strict_unformed_xabcd_patterns(extremum_points: List[Tuple],
                                         df: pd.DataFrame,
                                         log_details: bool = False,
                                         max_patterns: int = None,
                                         max_search_window: int = None,
                                         strict_validation: bool = True) -> List[Dict]:
    """
    Detect strict unformed XABCD patterns (4-point patterns X-A-B-C with projected D).

    Args:
        extremum_points: List of tuples (timestamp, price, is_high, bar_index)
        df: DataFrame with OHLC data for validation
        log_details: Whether to print detailed logs
        max_patterns: IGNORED - NO LIMITS for 100% accuracy
        max_search_window: IGNORED - NO LIMITS for 100% accuracy
        strict_validation: Whether to apply strict price containment validation (default True for 100% accuracy)

    Returns:
        List of dictionaries containing unformed XABCD patterns with horizontal D lines
    """
    patterns = []
    n = len(extremum_points)

    if n < 4:
        if log_details:
            print(f"Not enough extremum points for unformed XABCD: {n} < 4")
        return patterns

    if df is None or df.empty:
        if log_details:
            print("No DataFrame provided for strict validation")
        return patterns

    # Prepare DataFrame for validation
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
        print(f"\nDetecting Strict Unformed XABCD patterns with {n} extremum points")
        print(f"DataFrame has {len(df_copy)} candles for validation")
        print(f"Max patterns limit: {max_patterns}")
        print(f"Search window: {max_search_window}")

    patterns_found = 0
    patterns_checked = 0
    patterns_rejected = 0

    # ==================== SEARCH WINDOW CONFIGURATION ====================
    # max_search_window controls how far apart pattern points can be:
    # - None = unlimited (search entire dataset)
    # - Number = maximum distance between points
    # ======================================================================
    if max_search_window is None:
        search_window = n  # Unlimited mode - search all combinations
    else:
        search_window = min(max_search_window, n)  # Limited mode - restrict distance

    # ==================== POINT RANGE CONFIGURATION ====================
    # Determine which points to process based on search window
    # ======================================================================
    if max_search_window is None:
        # Unlimited mode: process ALL points
        start_point = 0
        end_point = n - 3
    elif max_search_window <= 10:
        # Ultra-limited mode: only check last few points for performance
        start_point = max(0, n - max_search_window * 4)  # Check 4x window size
        end_point = n - 3
    else:
        # Limited mode: reasonable performance/accuracy balance
        start_point = max(0, n - 300)  # Check last 300 extremum points
        end_point = n - 3

    # IMPORTANT: Window is measured in BAR INDEX distance, not extremum_points distance
    # This ensures consistency when same bar appears as both high and low
    for i in range(start_point, end_point):  # X point
        X = extremum_points[i]
        X_bar = X[3] if len(X) > 3 else i

        # Search all A points (will filter by bar index distance below)
        j_end = n - 2

        for j in range(i + 1, j_end):  # A point
            A = extremum_points[j]
            A_bar = A[3] if len(A) > 3 else j

            # Skip if A is beyond search window (measured in bar indices)
            if max_search_window is not None and (A_bar - X_bar) > search_window:
                continue

            # OPTIMIZATION: Early same-timestamp check for X and A
            if X[0] == A[0]:
                continue

            # Search all B points (will filter by bar index distance below)
            k_end = n - 1

            for k in range(j + 1, k_end):  # B point
                B = extremum_points[k]
                B_bar = B[3] if len(B) > 3 else k

                # Skip if B is beyond search window (measured in bar indices)
                if max_search_window is not None and (B_bar - A_bar) > search_window:
                    continue

                # OPTIMIZATION: Early same-timestamp check for A and B
                if A[0] == B[0]:
                    continue

                # Search all C points (will filter by bar index distance below)
                l_end = n

                for l in range(k + 1, l_end):  # C point
                    C = extremum_points[l]
                    C_bar = C[3] if len(C) > 3 else l

                    # Skip if C is beyond search window (measured in bar indices)
                    if max_search_window is not None and (C_bar - B_bar) > search_window:
                        continue

                    # Complete same-timestamp check for all point combinations
                    # (prevents same candle from being both high and low)
                    if (X[0] == C[0] or  # X and C
                        A[0] == B[0] or  # A and B (already checked above but kept for clarity)
                        B[0] == C[0]):   # B and C
                        continue

                    # Check alternating pattern for X, A, B, C
                    if X[2] == A[2] or A[2] == B[2] or B[2] == C[2]:
                        continue

                    patterns_checked += 1

                    # Determine pattern type
                    is_bullish = not X[2]  # X is low for bullish

                    # Validate basic structure
                    x_price, a_price, b_price, c_price = X[1], A[1], B[1], C[1]

                    if is_bullish:
                        structure_valid = (
                            x_price < a_price and  # X below A
                            a_price > b_price and  # A above B
                            b_price < c_price      # B below C
                        )
                    else:
                        structure_valid = (
                            x_price > a_price and  # X above A
                            a_price < b_price and  # A below B
                            b_price > c_price      # B above C
                        )

                    if not structure_valid:
                        continue

                    # Calculate ratios
                    xa_move = abs(a_price - x_price)
                    ab_move = abs(b_price - a_price)
                    bc_move = abs(c_price - b_price)

                    if xa_move == 0 or ab_move == 0 or bc_move == 0:
                        continue

                    ab_xa_retracement = (ab_move / xa_move) * 100
                    bc_ab_projection = (bc_move / ab_move) * 100

                    # Find matching patterns
                    matching_patterns_data = XABCD_PATTERN_LOOKUP.find_matching_patterns(
                        ab_xa_retracement, bc_ab_projection, is_bullish
                    )

                    # Debug: Check if this is X:66 A:72 combination
                    x_bar = X[3] if len(X) > 3 else i
                    a_bar = A[3] if len(A) > 3 else j
                    b_bar = B[3] if len(B) > 3 else k
                    c_bar = C[3] if len(C) > 3 else l

                    is_target_pattern = (x_bar == 66 and a_bar == 72 and b_bar == 96 and c_bar == 100)

                    if is_target_pattern and not matching_patterns_data:
                        print(f"DEBUG REJECT: X:{x_bar} A:{a_bar} B:{b_bar} C:{c_bar}")
                        print(f"  AB/XA: {ab_xa_retracement:.2f}%, BC/AB: {bc_ab_projection:.2f}%")
                        print(f"  No matching patterns found for these ratios")

                    if not matching_patterns_data:
                        continue

                    # Get bar indices - needed for validation and D-line checking
                    # Use bar indices - if element [3] exists use it, otherwise use element [0]
                    # Element [0] is the timestamp/bar index, element [3] is also bar index if present
                    x_candle_idx = X[3]
                    a_candle_idx = A[3]
                    b_candle_idx = B[3]
                    c_candle_idx = C[3]

                    # Ensure indices are integers
                    x_candle_idx = int(x_candle_idx) if x_candle_idx is not None else None
                    a_candle_idx = int(a_candle_idx) if a_candle_idx is not None else None
                    b_candle_idx = int(b_candle_idx) if b_candle_idx is not None else None
                    c_candle_idx = int(c_candle_idx) if c_candle_idx is not None else None

                    if None in [x_candle_idx, a_candle_idx, b_candle_idx, c_candle_idx]:
                        patterns_rejected += 1
                        if log_details:
                            print(f"Pattern rejected: Missing bar indices")
                        continue

                    # Apply strict validation (default True for 100% accuracy)
                    if strict_validation:
                        try:
                            # Validate price containment
                            if is_bullish:
                                containment_valid = validate_price_containment_bullish_xabcd(
                                    df_copy, x_candle_idx, a_candle_idx, b_candle_idx, c_candle_idx,
                                    x_price, a_price, b_price, c_price
                                )
                            else:
                                containment_valid = validate_price_containment_bearish_xabcd(
                                    df_copy, x_candle_idx, a_candle_idx, b_candle_idx, c_candle_idx,
                                    x_price, a_price, b_price, c_price
                                )

                            if not containment_valid:
                                patterns_rejected += 1
                                if is_target_pattern:
                                    print(f"DEBUG REJECT: X:{x_bar} A:{a_bar} B:{b_bar} C:{c_bar}")
                                    print(f"  REASON: Failed price containment validation")
                                if log_details:
                                    print(f"Pattern rejected: Failed price containment validation")
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
                                    if max_high_after > c_price:
                                        c_point_crossed = True
                                else:
                                    # For bearish: C is a low, check if any bar after C goes below C
                                    min_low_after = df_copy[low_col].iloc[c_candle_idx+1:].min()
                                    if min_low_after < c_price:
                                        c_point_crossed = True

                                if c_point_crossed:
                                    patterns_rejected += 1
                                    if log_details:
                                        print(f"  Rejected pattern: C point crossed after formation")
                                    continue

                        except Exception as e:
                            patterns_rejected += 1
                            if log_details:
                                print(f"CRITICAL: Pattern rejected due to validation error: {e}")
                            # CRITICAL: Always skip pattern on error - never process invalid patterns
                            continue

                    # Calculate horizontal D lines for first matching pattern
                    first_pattern = matching_patterns_data[0]
                    d_lines = calculate_horizontal_d_lines(
                        x_price, a_price, b_price, c_price, first_pattern, is_bullish
                    )

                    if not d_lines:
                        continue

                    # Validate that D lines don't cross candlesticks after point C
                    valid_d_lines = validate_d_lines_no_candlestick_crossing(
                        df_copy, c_candle_idx, d_lines
                    )

                    if not valid_d_lines:
                        # All D lines cross candlesticks, skip this pattern
                        patterns_rejected += 1
                        continue

                    # Use only the valid D lines
                    d_lines = valid_d_lines

                    # Create standardized pattern object
                    direction = 'bullish' if is_bullish else 'bearish'
                    pattern_name = standardize_pattern_name(first_pattern['name'], 'unformed', direction)
                    pattern_name = fix_unicode_issues(pattern_name)

                    # Create pattern points with proper indices
                    # Use bar indices - if element [3] exists use it, otherwise use element [0]
                    x_bar_idx = X[3]
                    a_bar_idx = A[3]
                    b_bar_idx = B[3]
                    c_bar_idx = C[3]

                    x_point = PatternPoint(timestamp=X[0], price=x_price, index=x_bar_idx)
                    a_point = PatternPoint(timestamp=A[0], price=a_price, index=a_bar_idx)
                    b_point = PatternPoint(timestamp=B[0], price=b_price, index=b_bar_idx)
                    c_point = PatternPoint(timestamp=C[0], price=c_price, index=c_bar_idx)

                    # Create standardized pattern
                    standard_pattern = StandardPattern(
                        name=pattern_name,
                        pattern_type='XABCD',
                        formation_status='unformed',
                        direction=direction,
                        x_point=x_point,
                        a_point=a_point,
                        b_point=b_point,
                        c_point=c_point,
                        d_point=None,  # Unformed patterns don't have D point
                        d_lines=d_lines,
                        ratios={
                            'ab_xa_retracement': ab_xa_retracement,
                            'bc_ab_projection': bc_ab_projection,
                            'matching_patterns': [p['name'] for p in matching_patterns_data]
                        },
                        validation_type='strict_containment'
                    )

                    # Convert to legacy dict format for backward compatibility
                    pattern = standard_pattern.to_legacy_dict()

                    patterns.append(pattern)
                    patterns_found += 1

                    # Check if we've found enough patterns
                    if max_patterns is not None and patterns_found >= max_patterns:
                        if log_details:
                            print(f"Reached max_patterns limit ({max_patterns})")
                        return patterns

                    if log_details:
                        print(f"Found STRICT {first_pattern['name']} ({'bullish' if is_bullish else 'bearish'}): "
                              f"AB/XA={ab_xa_retracement:.1f}%, BC/AB={bc_ab_projection:.1f}%")

    if log_details:
        print(f"\nStrict Unformed XABCD Detection Summary:")
        print(f"  Checked: {patterns_checked} pattern combinations")
        print(f"  Found: {patterns_found} patterns with strict validation")
        print(f"  Rejected: {patterns_rejected} patterns due to price violations")

    return patterns


if __name__ == "__main__":
    # Test the comprehensive detection
    print("Loading test data...")

    # Load the CSV data
    df = pd.read_csv('btcusdt_1d.csv')
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)

    print(f"Loaded {len(df)} candles")

    # Simple pivot point detection for testing
    def find_pivot_points(data, window=5):
        """Find local highs and lows in the data"""
        extremum_points = []

        high_col = 'High' if 'High' in data.columns else 'high'
        low_col = 'Low' if 'Low' in data.columns else 'low'

        # Find local highs
        for i in range(window, len(data) - window):
            if data[high_col].iloc[i] == data[high_col].iloc[i-window:i+window+1].max():
                extremum_points.append((data.index[i], data[high_col].iloc[i], True, i))

        # Find local lows
        for i in range(window, len(data) - window):
            if data[low_col].iloc[i] == data[low_col].iloc[i-window:i+window+1].min():
                extremum_points.append((data.index[i], data[low_col].iloc[i], False, i))

        # Sort by timestamp
        extremum_points.sort(key=lambda x: x[0])
        return extremum_points

    # Add bar indices to extremum points for proper validation
    extremum_points_raw = find_pivot_points(df, window=5)
    extremum_points = []
    for ep in extremum_points_raw:
        # Find the bar index for this timestamp
        timestamp = ep[0]
        bar_idx = None
        if isinstance(timestamp, (int, np.integer)):
            bar_idx = timestamp
        else:
            # Find index in dataframe
            if isinstance(df.index, pd.DatetimeIndex):
                matches = df.index == timestamp
                if matches.any():
                    bar_idx = np.where(matches)[0][0]

        # Add bar index as 4th element
        extremum_points.append((*ep, bar_idx))

    print(f"Found {len(extremum_points)} extremum points")

    # Run comprehensive detection
    patterns = detect_strict_unformed_xabcd_patterns(
        extremum_points,
        df,
        log_details=True,
        max_patterns=10
    )

    # Show some example patterns
    print("\n" + "="*60)
    print("EXAMPLE PATTERNS")
    print("="*60)

    if patterns:
        print(f"\nFound {len(patterns)} strict unformed XABCD patterns")

        for i, p in enumerate(patterns[:3], 1):
            print(f"\nPattern {i}: {p['name']}")
            print(f"  Type: {p['type']}")
            print(f"  Validation: {p['validation']}")
            print(f"  AB/XA Retracement: {p['ratios']['ab_xa_retracement']:.1f}%")
            print(f"  BC/AB Projection: {p['ratios']['bc_ab_projection']:.1f}%")
            print(f"  Horizontal D Lines: {len(p['points']['D_projected']['d_lines'])}")
            for j, line in enumerate(p['points']['D_projected']['d_lines'][:3], 1):
                print(f"    Line {j}: {line:.2f}")
    else:
        print("No strict unformed XABCD patterns found")