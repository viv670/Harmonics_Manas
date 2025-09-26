"""
Ultra-Fast Strict XABCD Pattern Detection using Sliding Window Algorithm
Handles ALL extremum points efficiently with O(n?) complexity instead of O(n?)
"""

from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
import time
from collections import defaultdict
from pattern_ratios_2_Final import XABCD_PATTERN_RATIOS

# Configuration constants
EPSILON = 1e-10
MAX_FUTURE_CANDLES = 100


def validate_price_containment_fast(
    highs: np.ndarray,
    lows: np.ndarray,
    x_idx: int, a_idx: int, b_idx: int, c_idx: int, d_idx: int,
    x_price: float, a_price: float, b_price: float, c_price: float, d_price: float,
    is_bullish: bool
) -> bool:
    """
    Ultra-fast price containment validation using vectorized operations.
    """

    if is_bullish:
        # Bullish pattern validation
        # 1. X->A: No low between X and A breaks X
        if x_idx + 1 < a_idx and np.any(lows[x_idx+1:a_idx] < x_price):
            return False

        # 2. A->B: No high between X and B exceeds A
        if x_idx + 1 < b_idx and np.any(highs[x_idx+1:b_idx] > a_price):
            return False

        # 3. B->C: No low between A and C breaks B
        if a_idx + 1 < c_idx and np.any(lows[a_idx+1:c_idx] < b_price):
            return False

        # 4. C->D: No high between B and D exceeds C
        if b_idx + 1 < d_idx and np.any(highs[b_idx+1:d_idx] > c_price):
            return False

        # 5. C->D: No low between C and D breaks D
        if c_idx + 1 < d_idx and np.any(lows[c_idx+1:d_idx] < d_price):
            return False
    else:
        # Bearish pattern validation
        # 1. X->A: No high between X and A exceeds X
        if x_idx + 1 < a_idx and np.any(highs[x_idx+1:a_idx] > x_price):
            return False

        # 2. A->B: No low between X and B breaks A
        if x_idx + 1 < b_idx and np.any(lows[x_idx+1:b_idx] < a_price):
            return False

        # 3. B->C: No high between A and C exceeds B
        if a_idx + 1 < c_idx and np.any(highs[a_idx+1:c_idx] > b_price):
            return False

        # 4. C->D: No low between B and D breaks C
        if b_idx + 1 < d_idx and np.any(lows[b_idx+1:d_idx] < c_price):
            return False

        # 5. C->D: No high between C and D exceeds D
        if c_idx + 1 < d_idx and np.any(highs[c_idx+1:d_idx] > d_price):
            return False

    return True


def identify_pattern_name(ab_xa: float, bc_ab: float, cd_bc: float, ad_xa: float, is_bullish: bool) -> str:
    """
    Identify the specific harmonic pattern name based on the calculated ratios.
    Only returns a pattern name if ALL ratios are within the exact defined ranges.

    Args:
        ab_xa: AB/XA ratio percentage
        bc_ab: BC/AB ratio percentage
        cd_bc: CD/BC ratio percentage
        ad_xa: AD/XA ratio percentage
        is_bullish: Whether the pattern is bullish or bearish

    Returns:
        The specific pattern name if exact match found, None otherwise
    """

    for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
        # Check if pattern direction matches
        pattern_is_bullish = 'bull' in pattern_name.lower()
        if pattern_is_bullish != is_bullish:
            continue

        # Check if ALL ratios are within defined ranges (exact match only)
        if (ratios['ab_xa'][0] <= ab_xa <= ratios['ab_xa'][1] and
            ratios['bc_ab'][0] <= bc_ab <= ratios['bc_ab'][1] and
            ratios['cd_bc'][0] <= cd_bc <= ratios['cd_bc'][1] and
            ratios['ad_xa'][0] <= ad_xa <= ratios['ad_xa'][1]):

            return pattern_name

    # No exact match found - return None to skip this pattern
    return None


def calculate_horizontal_d_lines(x_price: float, a_price: float, b_price: float, c_price: float,
                                pattern_name: str, is_bullish: bool) -> List[float]:
    """
    Calculate horizontal D lines for XABCD patterns based on pattern ratios.
    This follows the same algorithm as comprehensive_xabcd_patterns.py

    Args:
        x_price, a_price, b_price, c_price: The X, A, B, C point prices
        pattern_name: The identified pattern name (e.g., 'Gartley1_bull')
        is_bullish: Whether the pattern is bullish or bearish

    Returns:
        List of horizontal price levels where D could complete
    """
    d_lines = []

    # Find the pattern ratios from the pattern name
    if pattern_name not in XABCD_PATTERN_RATIOS:
        return []

    ratios = XABCD_PATTERN_RATIOS[pattern_name]

    # Calculate moves
    xa_move = abs(a_price - x_price)
    bc_move = abs(c_price - b_price)

    if xa_move == 0 or bc_move == 0:
        return []

    # Get ranges
    ad_min, ad_max = ratios['ad_xa'][0], ratios['ad_xa'][1]
    cd_min, cd_max = ratios['cd_bc'][0], ratios['cd_bc'][1]

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


def detect_strict_xabcd_patterns(
    extremum_points: List[Tuple],
    df: pd.DataFrame,
    log_details: bool = False,
    max_patterns: Optional[int] = None,
    max_window: int = None  # Maximum distance between X and D (None = no limit)
) -> List[Dict]:
    """
    Ultra-efficient strict XABCD pattern detection using sliding window approach.

    Key optimizations:
    1. Sliding window to limit search space
    2. Early termination when constraints are violated
    3. Smart indexing to avoid redundant checks
    4. Vectorized operations where possible

    Time complexity: O(n? ? w) where w is window size (constant)
    Space complexity: O(n)
    """

    if log_details:
        print(f"Starting ultra-fast strict XABCD detection with {len(extremum_points)} extremum points")
        start_time = time.time()

    patterns = []

    # Pre-process extremum points for faster access
    points_by_type = {'high': [], 'low': []}
    point_indices = {}  # Map timestamp to index in df

    for i, (timestamp, price, is_high) in enumerate(extremum_points):
        point_type = 'high' if is_high else 'low'
        points_by_type[point_type].append((i, timestamp, price))
        try:
            point_indices[timestamp] = df.index.get_loc(timestamp)
        except KeyError:
            continue

    # Pre-extract numpy arrays for vectorized operations
    highs_array = df['High'].values
    lows_array = df['Low'].values

    # For bullish patterns: X(L), A(H), B(L), C(H), D(L)
    # For bearish patterns: X(H), A(L), B(H), C(L), D(H)

    def find_patterns(is_bullish: bool):
        if is_bullish:
            x_points = points_by_type['low']
            a_points = points_by_type['high']
            b_points = points_by_type['low']
            c_points = points_by_type['high']
            d_points = points_by_type['low']
        else:
            x_points = points_by_type['high']
            a_points = points_by_type['low']
            b_points = points_by_type['high']
            c_points = points_by_type['low']
            d_points = points_by_type['high']

        # Use sliding window approach
        for x_idx, x_time, x_price in x_points:
            if max_patterns and len(patterns) >= max_patterns:
                return

            # Find valid A points (must be after X, within window if limit exists)
            a_candidates = [
                (a_idx, a_time, a_price)
                for a_idx, a_time, a_price in a_points
                if a_idx > x_idx and (max_window is None or a_idx - x_idx <= max_window)
            ]

            for a_idx, a_time, a_price in a_candidates:
                # Early termination check for X-A segment
                if x_time not in point_indices or a_time not in point_indices:
                    continue

                x_df_idx = point_indices[x_time]
                a_df_idx = point_indices[a_time]

                # Quick validation of X-A segment
                if is_bullish:
                    # Check if any low between X and A breaks X
                    if x_df_idx + 1 < a_df_idx and np.any(lows_array[x_df_idx+1:a_df_idx] < x_price):
                        continue
                else:
                    # Check if any high between X and A exceeds X
                    if x_df_idx + 1 < a_df_idx and np.any(highs_array[x_df_idx+1:a_df_idx] > x_price):
                        continue

                # Find valid B points
                b_candidates = [
                    (b_idx, b_time, b_price)
                    for b_idx, b_time, b_price in b_points
                    if b_idx > a_idx and (max_window is None or b_idx - x_idx <= max_window)
                ]

                for b_idx, b_time, b_price in b_candidates:
                    if b_time not in point_indices:
                        continue
                    b_df_idx = point_indices[b_time]

                    # Early termination for A-B segment
                    if is_bullish:
                        if b_price <= x_price or b_price >= a_price:
                            continue
                        if x_df_idx + 1 < b_df_idx and np.any(highs_array[x_df_idx+1:b_df_idx] > a_price):
                            continue
                    else:
                        if b_price >= x_price or b_price <= a_price:
                            continue
                        if x_df_idx + 1 < b_df_idx and np.any(lows_array[x_df_idx+1:b_df_idx] < a_price):
                            continue

                    # Find valid C points
                    c_candidates = [
                        (c_idx, c_time, c_price)
                        for c_idx, c_time, c_price in c_points
                        if c_idx > b_idx and (max_window is None or c_idx - x_idx <= max_window)
                    ]

                    for c_idx, c_time, c_price in c_candidates:
                        if c_time not in point_indices:
                            continue
                        c_df_idx = point_indices[c_time]

                        # Early termination for B-C segment
                        if is_bullish:
                            if c_price <= b_price or c_price >= a_price:
                                continue
                            if a_df_idx + 1 < c_df_idx and np.any(lows_array[a_df_idx+1:c_df_idx] < b_price):
                                continue
                        else:
                            if c_price >= b_price or c_price <= a_price:
                                continue
                            if a_df_idx + 1 < c_df_idx and np.any(highs_array[a_df_idx+1:c_df_idx] > b_price):
                                continue

                        # Find valid D points
                        d_candidates = [
                            (d_idx, d_time, d_price)
                            for d_idx, d_time, d_price in d_points
                            if d_idx > c_idx and (max_window is None or d_idx - x_idx <= max_window)
                        ]

                        for d_idx, d_time, d_price in d_candidates:
                            if d_time not in point_indices:
                                continue
                            d_df_idx = point_indices[d_time]

                            # Basic XABCD structure check
                            if is_bullish:
                                if d_price >= c_price or d_price <= x_price:
                                    continue
                            else:
                                if d_price <= c_price or d_price >= x_price:
                                    continue

                            # Final strict validation
                            if validate_price_containment_fast(
                                highs_array, lows_array,
                                x_df_idx, a_df_idx, b_df_idx, c_df_idx, d_df_idx,
                                x_price, a_price, b_price, c_price, d_price,
                                is_bullish
                            ):
                                # Calculate ratios for pattern identification
                                xa_move = abs(a_price - x_price)
                                ab_move = abs(b_price - a_price)
                                bc_move = abs(c_price - b_price)
                                cd_move = abs(d_price - c_price)
                                ad_move = abs(d_price - a_price)

                                # Calculate ratio percentages with epsilon protection
                                ab_xa_ratio = (ab_move / (xa_move + EPSILON) * 100)
                                bc_ab_ratio = (bc_move / (ab_move + EPSILON) * 100)
                                cd_bc_ratio = (cd_move / (bc_move + EPSILON) * 100)
                                ad_xa_ratio = (ad_move / (xa_move + EPSILON) * 100)

                                # Identify the specific pattern name based on ratios
                                pattern_name = identify_pattern_name(
                                    ab_xa_ratio, bc_ab_ratio, cd_bc_ratio, ad_xa_ratio, is_bullish
                                )

                                # Only add pattern if it matches a defined pattern exactly
                                if pattern_name:
                                    # Calculate d_lines for this pattern
                                    d_lines = calculate_horizontal_d_lines(
                                        x_price, a_price, b_price, c_price,
                                        pattern_name, is_bullish
                                    )

                                    pattern = {
                                        'type': 'strict_xabcd',
                                        'name': pattern_name,
                                        'bullish': is_bullish,
                                        'points': {
                                            'X': {'time': x_time, 'price': x_price},
                                            'A': {'time': a_time, 'price': a_price},
                                            'B': {'time': b_time, 'price': b_price},
                                            'C': {'time': c_time, 'price': c_price},
                                            'D': {'time': d_time, 'price': d_price},
                                            'D_projected': {'d_lines': d_lines}  # Add d_lines like unformed patterns
                                        },
                                        'ratios': {
                                            'ab_xa': ab_xa_ratio,
                                            'bc_ab': bc_ab_ratio,
                                            'cd_bc': cd_bc_ratio,
                                            'ad_xa': ad_xa_ratio
                                        },
                                        'start_time': x_time,
                                        'end_time': d_time,
                                        'confidence': 100.0  # Strict patterns have 100% confidence
                                    }
                                    patterns.append(pattern)

                                if max_patterns and len(patterns) >= max_patterns:
                                    return

    # Find both bullish and bearish patterns
    find_patterns(is_bullish=True)
    if not max_patterns or len(patterns) < max_patterns:
        find_patterns(is_bullish=False)

    if log_details:
        elapsed = time.time() - start_time
        print(f"Found {len(patterns)} strict XABCD patterns in {elapsed:.3f} seconds")
        if elapsed > 0:
            patterns_per_sec = len(patterns) / elapsed if patterns else 0
            points_per_sec = len(extremum_points) / elapsed
            print(f"Performance: {patterns_per_sec:.0f} patterns/sec, {points_per_sec:.0f} points/sec")

    return patterns[:max_patterns] if max_patterns else patterns