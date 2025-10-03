"""
Pattern detection algorithms for formed and unformed patterns.
Contains detection functions for ABCD and XABCD patterns.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Optional
from pattern_ratios_2_Final import (
    ABCD_PATTERN_RATIOS,
    XABCD_PATTERN_RATIOS,
    PATTERN_COLORS,
    PRZ_PROJECTION_PAIRS
)


def validate_xabcd_price_containment_bullish(df: pd.DataFrame,
                                            x_idx: int, a_idx: int, b_idx: int,
                                            c_idx: int, d_idx: int,
                                            x_price: float, a_price: float,
                                            b_price: float, c_price: float,
                                            d_price: float) -> bool:
    """
    Validate price containment for bullish XABCD patterns.

    Bullish: X(Low) -> A(High) -> B(Low) -> C(High) -> D(Low)

    Proper validation rules:
    1. X should be the lowest point between X and A
    2. A should be the highest point between X and B
    3. B should be > X and the lowest point between A and C
    4. C should be the highest point between B and D
    5. D should be the lowest point between C and D, and D < B
    """
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

        # Rule 4: C should be the highest between B-D (excluding C and D endpoints)
        if b_idx < d_idx:
            segment_bd = df.iloc[b_idx:d_idx]
            if any(segment_bd[high_col] > c_price):
                return False  # Found a higher high than C

        # Rule 5a: D should be the lowest between C-D (excluding D itself)
        if c_idx < d_idx:
            segment_cd = df.iloc[c_idx:d_idx]
            if any(segment_cd[low_col] < d_price):
                return False  # Found a lower low than D

        # Rule 5b: D should be lower than B
        if d_price >= b_price:
            return False  # D must be lower than B for valid pattern

        return True

    except Exception:
        return False


def validate_xabcd_price_containment_bearish(df: pd.DataFrame,
                                            x_idx: int, a_idx: int, b_idx: int,
                                            c_idx: int, d_idx: int,
                                            x_price: float, a_price: float,
                                            b_price: float, c_price: float,
                                            d_price: float) -> bool:
    """
    Validate price containment for bearish XABCD patterns.

    Bearish: X(High) -> A(Low) -> B(High) -> C(Low) -> D(High)

    Proper validation rules:
    1. X should be the highest point between X and A
    2. A should be the lowest point between X and B
    3. B should be < X and the highest point between A and C
    4. C should be the lowest point between B and D
    5. D should be the highest point between C and D, and D > B
    """
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

        # Rule 4: C should be the lowest between B-D (excluding C and D endpoints)
        if b_idx < d_idx:
            segment_bd = df.iloc[b_idx:d_idx]
            if any(segment_bd[low_col] < c_price):
                return False  # Found a lower low than C

        # Rule 5a: D should be the highest between C-D (excluding D itself)
        if c_idx < d_idx:
            segment_cd = df.iloc[c_idx:d_idx]
            if any(segment_cd[high_col] > d_price):
                return False  # Found a higher high than D

        # Rule 5b: D should be higher than B
        if d_price <= b_price:
            return False  # D must be higher than B for valid pattern

        return True

    except Exception:
        return False


def detect_abcd_patterns_fast(extremum_points: List[Tuple], log_details: bool = False) -> List[Dict]:
    """
    Fast ABCD pattern detection without search window limitations.

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
        log_details: Whether to print detailed logs

    Returns:
        List of dictionaries containing pattern information
    """
    patterns = []
    n = len(extremum_points)

    if n < 4:
        if log_details:
            print(f"Not enough extremum points for ABCD: {n} < 4")
        return patterns

    if log_details:
        print(f"\nDetecting ABCD with {n} extremum points:")
        for i, ep in enumerate(extremum_points[:10]):
            point_type = "High" if ep[2] else "Low"
            print(f"  [{i}] {ep[0].date() if hasattr(ep[0], 'date') else ep[0]}: {ep[1]:.2f} ({point_type})")

    # Separate highs and lows with bar indices
    # Use ep[3] (bar index) instead of enumeration index for proper pattern tracking
    highs = []
    lows = []

    for i, ep in enumerate(extremum_points):
        # Get bar index from 4th element (ep[3])
        bar_idx = ep[3] if len(ep) > 3 else i

        if ep[2]:  # Is high
            highs.append((bar_idx, ep[0], ep[1]))
        else:  # Is low
            lows.append((bar_idx, ep[0], ep[1]))

    patterns_found = 0

    for pattern_name, ratio_range in ABCD_PATTERN_RATIOS.items():
        # Determine if bullish or bearish from pattern name
        is_bullish = 'bull' in pattern_name

        # For bullish: A=High, B=Low, C=High, D=Low
        # For bearish: A=Low, B=High, C=Low, D=High
        if is_bullish:
            a_candidates = highs
            b_candidates = lows
            c_candidates = highs
            d_candidates = lows
        else:
            a_candidates = lows
            b_candidates = highs
            c_candidates = lows
            d_candidates = highs

        # Iterate through all valid combinations
        for a_idx, a_time, a_price in a_candidates:
            # Find valid B points (after A)
            valid_b = [b for b in b_candidates if b[0] > a_idx]

            for b_idx, b_time, b_price in valid_b:
                # Calculate AB move
                ab_move = abs(b_price - a_price)
                if ab_move == 0:
                    continue

                # Find valid C points (after B)
                valid_c = [c for c in c_candidates if c[0] > b_idx]

                for c_idx, c_time, c_price in valid_c:
                    # Calculate BC retracement
                    bc_move = abs(c_price - b_price)
                    bc_retracement = (bc_move / ab_move) * 100

                    # Check if BC retracement is within pattern requirements
                    if not (ratio_range['retr'][0] <= bc_retracement <= ratio_range['retr'][1]):
                        continue

                    # Find valid D points (after C)
                    valid_d = [d for d in d_candidates if d[0] > c_idx]

                    for d_idx, d_time, d_price in valid_d:
                        # Calculate CD projection
                        cd_move = abs(d_price - c_price)
                        if cd_move == 0:
                            continue
                        cd_projection = (cd_move / bc_move) * 100

                        # Check if CD projection is within pattern requirements
                        if not (ratio_range['proj'][0] <= cd_projection <= ratio_range['proj'][1]):
                            continue

                        # Validate pattern structure
                        if is_bullish:
                            # Bullish conditions
                            valid = (
                                a_price > b_price and  # A (high) > B (low)
                                c_price > b_price and  # C (high) > B (low)
                                c_price > d_price and  # C (high) > D (low)
                                c_price < a_price      # C makes a lower high than A
                            )
                        else:
                            # Bearish conditions
                            valid = (
                                a_price < b_price and  # A (low) < B (high)
                                c_price < b_price and  # C (low) < B (high)
                                c_price < d_price and  # C (low) < D (high)
                                c_price > a_price      # C makes a higher low than A
                            )

                        if valid:
                            pattern = {
                                'name': pattern_name,
                                'type': 'bullish' if is_bullish else 'bearish',
                                'points': {
                                    'A': {'time': a_time, 'price': a_price},
                                    'B': {'time': b_time, 'price': b_price},
                                    'C': {'time': c_time, 'price': c_price},
                                    'D': {'time': d_time, 'price': d_price}
                                },
                                'ratios': {
                                    'bc': bc_retracement,
                                    'cd': cd_projection
                                },
                                'indices': [a_idx, b_idx, c_idx, d_idx]
                            }
                            patterns.append(pattern)
                            patterns_found += 1

                            if log_details:
                                print(f"Found {pattern_name} ({'bullish' if is_bullish else 'bearish'}): "
                                      f"A={a_price:.2f}, B={b_price:.2f}, C={c_price:.2f}, D={d_price:.2f} | "
                                      f"BC={bc_retracement:.1f}%, CD={cd_projection:.1f}%")

    if log_details:
        print(f"Found {patterns_found} AB=CD patterns")

    return patterns


def calculate_d_lines_for_formed_pattern(x_price: float, a_price: float, b_price: float, c_price: float,
                                         pattern_data: Dict, is_bullish: bool) -> List[float]:
    """
    Calculate horizontal D lines for formed XABCD patterns (same as unformed algorithm)

    Returns list of horizontal price levels where D was expected based on pattern ratios
    """
    d_lines = []

    # Calculate moves
    xa_move = abs(a_price - x_price)
    bc_move = abs(c_price - b_price)

    if xa_move == 0 or bc_move == 0:
        return []

    # Get ranges from pattern data (tuple format from XABCD_PATTERN_RATIOS)
    ad_min, ad_max = pattern_data['ad_xa']
    cd_min, cd_max = pattern_data['cd_bc']

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


def detect_xabcd_patterns(extremum_points: List[Tuple], df: pd.DataFrame = None,
                         log_details: bool = False, strict_validation: bool = True,
                         max_search_window: Optional[int] = 30) -> List[Dict]:
    """
    XABCD pattern detection with optional price containment validation.
    Detects complete 5-point XABCD patterns (X-A-B-C-D).

    Args:
        extremum_points: List of tuples (timestamp, price, is_high, bar_index)
        df: DataFrame with OHLC data for price containment validation
        log_details: Whether to print detailed logs
        strict_validation: Whether to apply strict price containment
        max_search_window: Maximum extremum points between pattern points (default 30)
                          Reduces O(n^5) to O(n*w^4) for performance
                          Set to None for unlimited search (very slow)

    Returns:
        List of dictionaries containing pattern information
    """
    patterns = []
    n = len(extremum_points)
    patterns_checked = 0
    patterns_rejected_structure = 0
    patterns_rejected_containment = 0

    if n < 5:
        if log_details:
            print(f"Not enough extremum points for XABCD: {n} < 5")
        return patterns

    if log_details:
        print(f"XABCD detection with {n} extremum points")
        print(f"Search window: {max_search_window if max_search_window else 'UNLIMITED (slow!)'}")
        if strict_validation and df is not None:
            print("Price containment validation: ENABLED")
        else:
            print("Price containment validation: DISABLED")

    # OPTIMIZATION: Pre-compute min/max values for D point crossing validation
    # Cache results per unique D point to avoid redundant calculations
    high_col = 'High' if df is not None and 'High' in df.columns else 'high'
    low_col = 'Low' if df is not None and 'Low' in df.columns else 'low'

    # Cache for D point crossing checks: (d_bar_idx, d_price, is_bullish) -> bool
    d_point_crossing_cache = {}

    # Determine search window for loops
    # Limit search to reasonable pattern sizes for performance
    # Pattern points typically appear within 20-40 extremum points of each other
    search_window = max_search_window if max_search_window is not None else n

    # OPTIMIZED: Check 5-point combinations with search window limits
    # This reduces complexity from O(n^5) to O(n*w^4) where w is the window size
    # IMPORTANT: Window is measured in BAR INDEX distance, not extremum_points distance
    # This ensures consistency when same bar appears as both high and low
    for x_i in range(n - 4):
        X = extremum_points[x_i]
        X_bar = X[3] if len(X) > 3 else x_i

        # Search all A points (will filter by bar index distance below)
        a_end = n - 3
        for a_i in range(x_i + 1, a_end):
            A = extremum_points[a_i]
            A_bar = A[3] if len(A) > 3 else a_i

            # EARLY EXIT: Check bar index distance from X to A
            if search_window != n and (A_bar - X_bar) > search_window:
                continue

            # EARLY EXIT: Check X-A alternation
            if X[2] == A[2]:  # Must alternate (X high -> A low, or X low -> A high)
                continue

            # EARLY EXIT: Check timestamp
            if X[0] == A[0]:
                continue

            # Search all B points (will filter by bar index distance below)
            b_end = n - 2
            for b_i in range(a_i + 1, b_end):
                B = extremum_points[b_i]
                B_bar = B[3] if len(B) > 3 else b_i

                # EARLY EXIT: Check bar index distance from A to B
                if search_window != n and (B_bar - A_bar) > search_window:
                    continue

                # EARLY EXIT: Check A-B alternation
                if A[2] == B[2]:
                    continue

                # EARLY EXIT: Check timestamps
                if X[0] == B[0] or A[0] == B[0]:
                    continue

                # Search all C points (will filter by bar index distance below)
                c_end = n - 1
                for c_i in range(b_i + 1, c_end):
                    C = extremum_points[c_i]
                    C_bar = C[3] if len(C) > 3 else c_i

                    # EARLY EXIT: Check bar index distance from B to C
                    if search_window != n and (C_bar - B_bar) > search_window:
                        continue

                    # EARLY EXIT: Check B-C alternation
                    if B[2] == C[2]:
                        continue

                    # EARLY EXIT: Check timestamps
                    if X[0] == C[0] or A[0] == C[0] or B[0] == C[0]:
                        continue

                    # Search all D points (will filter by bar index distance below)
                    d_end = n
                    for d_i in range(c_i + 1, d_end):
                        D = extremum_points[d_i]
                        D_bar = D[3] if len(D) > 3 else d_i

                        # EARLY EXIT: Check bar index distance from C to D
                        if search_window != n and (D_bar - C_bar) > search_window:
                            continue

                        # EARLY EXIT: Check C-D alternation
                        if C[2] == D[2]:
                            continue

                        # EARLY EXIT: Check all timestamps
                        if (X[0] == D[0] or A[0] == D[0] or
                            B[0] == D[0] or C[0] == D[0]):
                            continue

                        # Determine pattern type (already validated alternating in early exits)
                        is_bullish_pattern = not X[2]  # X is low = bullish
                        # Note: Alternating is already guaranteed by early exits above

                        # Get prices
                        x_price = X[1]
                        a_price = A[1]
                        b_price = B[1]
                        c_price = C[1]
                        d_price = D[1]

                        # Validate price relationships based on pattern type
                        if is_bullish_pattern:
                            # Basic bullish structure
                            valid_structure = (
                                x_price < a_price and  # X < A
                                b_price < a_price and  # B < A
                                c_price > b_price and  # C > B
                                d_price < c_price      # D < C
                            )
                        else:
                            # Basic bearish structure
                            valid_structure = (
                                x_price > a_price and  # X > A
                                b_price > a_price and  # B > A
                                c_price < b_price and  # C < B
                                d_price > c_price      # D > C
                            )

                        if not valid_structure:
                            patterns_rejected_structure += 1
                            continue

                        # Calculate movements
                        xa_move = abs(a_price - x_price)
                        ab_move = abs(b_price - a_price)
                        bc_move = abs(c_price - b_price)
                        cd_move = abs(d_price - c_price)
                        ad_move = abs(d_price - a_price)

                        # Skip if any movement is zero
                        if xa_move == 0 or ab_move == 0 or bc_move == 0 or cd_move == 0:
                            continue

                        # Calculate ratios ONCE for this 5-point combination
                        ab_xa_ratio = (ab_move / xa_move) * 100
                        bc_ab_ratio = (bc_move / ab_move) * 100
                        cd_bc_ratio = (cd_move / bc_move) * 100
                        ad_xa_ratio = (ad_move / xa_move) * 100

                        # Now check against all matching pattern types
                        for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
                            # Check if pattern type matches
                            pattern_is_bullish = 'bull' in pattern_name
                            if pattern_is_bullish != is_bullish_pattern:
                                continue

                            # Check if all ratios match the pattern requirements
                            ab_xa_match = ratios['ab_xa'][0] <= ab_xa_ratio <= ratios['ab_xa'][1]
                            bc_ab_match = ratios['bc_ab'][0] <= bc_ab_ratio <= ratios['bc_ab'][1]
                            cd_bc_match = ratios['cd_bc'][0] <= cd_bc_ratio <= ratios['cd_bc'][1]
                            ad_xa_match = ratios['ad_xa'][0] <= ad_xa_ratio <= ratios['ad_xa'][1]

                            if not (ab_xa_match and bc_ab_match and cd_bc_match and ad_xa_match):
                                continue

                            patterns_checked += 1

                            # Get bar indices from extremum points (needed for pattern ID generation)
                            x_bar_idx = X[3] if len(X) > 3 else x_i
                            a_bar_idx = A[3] if len(A) > 3 else a_i
                            b_bar_idx = B[3] if len(B) > 3 else b_i
                            c_bar_idx = C[3] if len(C) > 3 else c_i
                            d_bar_idx = D[3] if len(D) > 3 else d_i

                            # Apply price containment validation if enabled
                            if strict_validation and df is not None:
                                # Validate price containment
                                if is_bullish_pattern:
                                    containment_valid = validate_xabcd_price_containment_bullish(
                                        df, x_bar_idx, a_bar_idx, b_bar_idx, c_bar_idx, d_bar_idx,
                                        x_price, a_price, b_price, c_price, d_price
                                    )
                                else:
                                    containment_valid = validate_xabcd_price_containment_bearish(
                                        df, x_bar_idx, a_bar_idx, b_bar_idx, c_bar_idx, d_bar_idx,
                                        x_price, a_price, b_price, c_price, d_price
                                    )

                                if not containment_valid:
                                    patterns_rejected_containment += 1
                                    if log_details:
                                        print(f"Pattern {pattern_name} rejected due to price containment violation")
                                    continue

                            # Calculate d_lines using the same algorithm as unformed XABCD
                            d_lines = calculate_d_lines_for_formed_pattern(
                                x_price, a_price, b_price, c_price,
                                ratios, is_bullish_pattern
                            )

                            # Validate that D point is within PRZ zone (min/max of d_lines)
                            if d_lines:
                                prz_min = min(d_lines)
                                prz_max = max(d_lines)

                                if not (prz_min <= d_price <= prz_max):
                                    patterns_rejected_containment += 1
                                    if log_details:
                                        print(f"  Rejected {pattern_name}: D point {d_price:.2f} not in PRZ [{prz_min:.2f}, {prz_max:.2f}]")
                                    continue

                                # Validate that price doesn't cross D point after formation
                                # OPTIMIZED: Cache results to avoid recalculating for same D point
                                if d_bar_idx < len(df) - 1:
                                    # Create cache key for this D point check
                                    cache_key = (d_bar_idx, d_price, is_bullish_pattern)

                                    # Check if we've already validated this D point
                                    if cache_key not in d_point_crossing_cache:
                                        # Calculate and cache the result
                                        d_point_crossed = False
                                        if is_bullish_pattern:
                                            # For bullish: D is a low, check if any bar after D goes below D
                                            min_low_after = df[low_col].iloc[d_bar_idx+1:].min()
                                            if min_low_after < d_price:
                                                d_point_crossed = True
                                        else:
                                            # For bearish: D is a high, check if any bar after D goes above D
                                            max_high_after = df[high_col].iloc[d_bar_idx+1:].max()
                                            if max_high_after > d_price:
                                                d_point_crossed = True

                                        d_point_crossing_cache[cache_key] = d_point_crossed

                                    # Use cached result
                                    if d_point_crossing_cache[cache_key]:
                                        patterns_rejected_containment += 1
                                        if log_details:
                                            print(f"  Rejected {pattern_name}: D point crossed after formation")
                                        continue

                            # Found valid pattern
                            pattern = {
                                'name': pattern_name,
                                'type': 'bullish' if is_bullish_pattern else 'bearish',
                                'pattern_type': 'XABCD',  # Add pattern type
                                'points': {
                                    'X': {'time': X[0], 'price': x_price, 'index': x_bar_idx},
                                    'A': {'time': A[0], 'price': a_price, 'index': a_bar_idx},
                                    'B': {'time': B[0], 'price': b_price, 'index': b_bar_idx},
                                    'C': {'time': C[0], 'price': c_price, 'index': c_bar_idx},
                                    'D': {'time': D[0], 'price': d_price, 'index': d_bar_idx}
                                },
                                'indices': {
                                    'X': x_bar_idx,
                                    'A': a_bar_idx,
                                    'B': b_bar_idx,
                                    'C': c_bar_idx,
                                    'D': d_bar_idx
                                },
                                'ratios': {
                                    'ab_xa': ab_xa_ratio,
                                    'bc_ab': bc_ab_ratio,
                                    'cd_bc': cd_bc_ratio,
                                    'ad_xa': ad_xa_ratio
                                },
                                'd_lines': d_lines  # Add d_lines to pattern
                            }

                            patterns.append(pattern)

                            if log_details:
                                print(f"Found {pattern_name}: AB/XA={ab_xa_ratio:.1f}%, BC/AB={bc_ab_ratio:.1f}%, CD/BC={cd_bc_ratio:.1f}%, AD/XA={ad_xa_ratio:.1f}%")

    if log_details:
        print(f"\nXABCD Detection Summary:")
        print(f"  Patterns checked: {patterns_checked}")
        print(f"  Rejected (structure): {patterns_rejected_structure}")
        if strict_validation and df is not None:
            print(f"  Rejected (containment): {patterns_rejected_containment}")
        print(f"  Total found: {len(patterns)}")

    return patterns

