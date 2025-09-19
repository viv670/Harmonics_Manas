"""
Fast pattern detection algorithms that match the original implementation's efficiency
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
from pattern_ratios_2_Final import (
    ABCD_PATTERN_RATIOS,
    XABCD_PATTERN_RATIOS,
    PATTERN_COLORS,
    PRZ_PROJECTION_PAIRS
)


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

    # Separate highs and lows with their indices
    highs = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if ep[2]]
    lows = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if not ep[2]]

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


def detect_xabcd_patterns_fast(extremum_points: List[Tuple], log_details: bool = False) -> List[Dict]:
    """
    Fast XABCD pattern detection using the original algorithm's approach.
    This version uses candidate pruning for better performance.

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
        log_details: Whether to print detailed logs

    Returns:
        List of dictionaries containing pattern information
    """
    patterns = []
    n = len(extremum_points)

    if n < 5:
        if log_details:
            print(f"Not enough extremum points for XABCD: {n} < 5")
        return patterns

    if log_details:
        print(f"Fast XABCD detection with {n} extremum points...")

    # Separate highs and lows with their indices
    highs = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if ep[2]]
    lows = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if not ep[2]]

    if log_details:
        print(f"Found {len(highs)} highs and {len(lows)} lows")

    patterns_found = 0

    for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
        is_bullish = 'bull' in pattern_name

        # For bullish: X=Low, A=High, B=Low, C=High, D=Low
        # For bearish: X=High, A=Low, B=High, C=Low, D=High
        if is_bullish:
            x_candidates = lows
            a_candidates = highs
            b_candidates = lows
            c_candidates = highs
            d_candidates = lows
        else:
            x_candidates = highs
            a_candidates = lows
            b_candidates = highs
            c_candidates = lows
            d_candidates = highs

        # Iterate through A candidates (this is the anchor point)
        for a_idx, a_time, a_price in a_candidates:

            # Find all valid X points (before A)
            valid_x = [x for x in x_candidates if x[0] < a_idx]

            for x_idx, x_time, x_price in valid_x:
                # Calculate XA move
                xa_move = abs(a_price - x_price)
                if xa_move == 0:
                    continue

                # Find valid B points (after A)
                valid_b = [b for b in b_candidates if b[0] > a_idx]

                for b_idx, b_time, b_price in valid_b:
                    # Calculate AB move and ratio
                    ab_move = abs(b_price - a_price)
                    if ab_move == 0:
                        continue

                    ab_xa_ratio = (ab_move / xa_move) * 100

                    # Check if AB/XA ratio is within pattern requirements
                    if not (ratios['ab_xa'][0] <= ab_xa_ratio <= ratios['ab_xa'][1]):
                        continue

                    # Find valid C points (after B)
                    valid_c = [c for c in c_candidates if c[0] > b_idx]

                    for c_idx, c_time, c_price in valid_c:
                        # Calculate BC move and ratio
                        bc_move = abs(c_price - b_price)
                        if bc_move == 0:
                            continue

                        bc_ab_ratio = (bc_move / ab_move) * 100

                        # Check if BC/AB ratio is within pattern requirements
                        if not (ratios['bc_ab'][0] <= bc_ab_ratio <= ratios['bc_ab'][1]):
                            continue

                        # Find valid D points (after C)
                        valid_d = [d for d in d_candidates if d[0] > c_idx]

                        for d_idx, d_time, d_price in valid_d:
                            # Calculate CD and AD moves
                            cd_move = abs(d_price - c_price)
                            ad_move = abs(d_price - a_price)

                            if bc_move == 0 or xa_move == 0:
                                continue

                            cd_bc_ratio = (cd_move / bc_move) * 100
                            ad_xa_ratio = (ad_move / xa_move) * 100

                            # Check if CD/BC and AD/XA ratios are within requirements
                            if (ratios['cd_bc'][0] <= cd_bc_ratio <= ratios['cd_bc'][1] and
                                ratios['ad_xa'][0] <= ad_xa_ratio <= ratios['ad_xa'][1]):

                                # Basic value checks to ensure proper pattern direction
                                # Let Fibonacci ratios define the pattern, not rigid C vs A rules
                                if is_bullish:
                                    # Bullish: X(Low) < A(High), B(Low) < A, C(High) > B, D(Low) < C
                                    value_checks = (
                                        x_price < a_price and  # X < A (initial upward move)
                                        b_price < a_price and  # B < A (retracement)
                                        c_price > b_price and  # C > B (C must be higher than B for bullish)
                                        d_price < c_price      # D < C (D must be lower than C for bullish)
                                        # C can be higher or lower than A - ratios will determine validity
                                    )
                                else:
                                    # Bearish: X(High) > A(Low), B(High) > A, C(Low) < B, D(High) > C
                                    value_checks = (
                                        x_price > a_price and  # X > A (initial downward move)
                                        b_price > a_price and  # B > A (retracement)
                                        c_price < b_price and  # C < B (C must be lower than B for bearish)
                                        d_price > c_price      # D > C (D must be higher than C for bearish)
                                        # C can be higher or lower than A - ratios will determine validity
                                    )

                                # Skip if basic value checks fail
                                if not value_checks:
                                    continue

                                pattern = {
                                    'name': pattern_name,
                                    'type': 'bullish' if is_bullish else 'bearish',
                                    'points': {
                                        'X': {'time': x_time, 'price': x_price},
                                        'A': {'time': a_time, 'price': a_price},
                                        'B': {'time': b_time, 'price': b_price},
                                        'C': {'time': c_time, 'price': c_price},
                                        'D': {'time': d_time, 'price': d_price}
                                    },
                                    'ratios': {
                                        'ab_xa': ab_xa_ratio,
                                        'bc_ab': bc_ab_ratio,
                                        'cd_bc': cd_bc_ratio,
                                        'ad_xa': ad_xa_ratio
                                    },
                                    'indices': [x_idx, a_idx, b_idx, c_idx, d_idx]
                                }
                                patterns.append(pattern)
                                patterns_found += 1

                                if log_details:
                                    print(f"Found {pattern_name}: AB/XA={ab_xa_ratio:.1f}%, "
                                          f"BC/AB={bc_ab_ratio:.1f}%, CD/BC={cd_bc_ratio:.1f}%, "
                                          f"AD/XA={ad_xa_ratio:.1f}%")
                                    print(f"  Indices: X={x_idx}, A={a_idx}, B={b_idx}, C={c_idx}, D={d_idx}")
                                    print(f"  Prices: X={x_price:.2f}, A={a_price:.2f}, B={b_price:.2f}, "
                                          f"C={c_price:.2f}, D={d_price:.2f}")
                                    print(f"  Index gaps: X->A={a_idx-x_idx}, A->B={b_idx-a_idx}, "
                                          f"B->C={c_idx-b_idx}, C->D={d_idx-c_idx}")

                                # Continue checking for more D points
                                # Removed break to find all valid patterns

    if log_details:
        print(f"XABCD search complete. Found {patterns_found} patterns.")

    return patterns


def detect_unformed_xabcd_patterns_fast(extremum_points: List[Tuple], df: pd.DataFrame = None, log_details: bool = False, max_patterns: int = 100) -> List[Dict]:
    """
    Fast detection of unformed XABCD patterns (missing D point).

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
        log_details: Whether to print detailed logs
        max_patterns: Maximum number of patterns to return (default 100)

    Returns:
        List of dictionaries containing pattern information with projected D point
    """
    import time
    start_time = time.time()
    TIMEOUT_SECONDS = 30  # Maximum time to spend on detection

    patterns = []
    n = len(extremum_points)

    if n < 4:
        if log_details:
            print(f"Not enough extremum points for unformed XABCD: {n} < 4")
        return patterns

    if log_details:
        print(f"Fast unformed XABCD detection with {n} extremum points...")

    # Separate highs and lows
    highs = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if ep[2]]
    lows = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if not ep[2]]

    patterns_found = 0
    MAX_PATTERNS_PER_TYPE = 3  # Reduced from 5 to 3 for better performance
    combinations_checked = 0
    MAX_COMBINATIONS = 50000  # Hard limit on combinations to check

    for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
        patterns_for_this_type = 0  # Track patterns for this specific type
        is_bullish = 'bull' in pattern_name
        pattern_completed = False  # Flag to break out of nested loops

        if is_bullish:
            x_candidates = lows[-100:]  # Limit to last 100 lows for performance
            a_candidates = highs[-100:]  # Limit to last 100 highs for performance
            b_candidates = lows[-100:]
            c_candidates = highs[-100:]
        else:
            x_candidates = highs[-100:]  # Limit to last 100 highs for performance
            a_candidates = lows[-100:]  # Limit to last 100 lows for performance
            b_candidates = highs[-100:]
            c_candidates = lows[-100:]

        # Iterate through A candidates
        for a_idx, a_time, a_price in a_candidates:
            if pattern_completed:
                break

            # Check timeout
            if time.time() - start_time > TIMEOUT_SECONDS:
                if log_details:
                    print(f"Timeout reached after {TIMEOUT_SECONDS} seconds")
                return patterns

            # Find valid X points (before A)
            valid_x = [x for x in x_candidates if x[0] < a_idx]

            for x_idx, x_time, x_price in valid_x:
                if pattern_completed:
                    break

                # Check combination limits
                combinations_checked += 1
                if combinations_checked > MAX_COMBINATIONS:
                    if log_details:
                        print(f"Maximum combinations limit {MAX_COMBINATIONS} reached")
                    return patterns

                xa_move = abs(a_price - x_price)
                if xa_move == 0:
                    continue

                # Find valid B points (after A)
                valid_b = [b for b in b_candidates if b[0] > a_idx]

                for b_idx, b_time, b_price in valid_b:
                    if pattern_completed:
                        break

                    # Check timeout every 1000 combinations
                    if combinations_checked % 1000 == 0:
                        if time.time() - start_time > TIMEOUT_SECONDS:
                            if log_details:
                                print(f"Timeout reached after {TIMEOUT_SECONDS} seconds")
                            return patterns

                    ab_move = abs(b_price - a_price)
                    if ab_move == 0:
                        continue

                    ab_xa_ratio = (ab_move / xa_move) * 100

                    if not (ratios['ab_xa'][0] <= ab_xa_ratio <= ratios['ab_xa'][1]):
                        continue

                    # Find valid C points (after B)
                    valid_c = [c for c in c_candidates if c[0] > b_idx]

                    for c_idx, c_time, c_price in valid_c:
                        if pattern_completed:
                            break
                        bc_move = abs(c_price - b_price)
                        if bc_move == 0:
                            continue

                        bc_ab_ratio = (bc_move / ab_move) * 100

                        if not (ratios['bc_ab'][0] <= bc_ab_ratio <= ratios['bc_ab'][1]):
                            continue

                        # Add value validation for unformed patterns
                        if is_bullish:
                            # Bullish: X < A, B < A, C > B
                            if not (x_price < a_price and b_price < a_price and c_price > b_price):
                                continue
                        else:
                            # Bearish: X > A, B > A, C < B
                            if not (x_price > a_price and b_price > a_price and c_price < b_price):
                                continue

                        # Early termination check before complex calculations
                        if patterns_for_this_type >= MAX_PATTERNS_PER_TYPE:
                            pattern_completed = True
                            break

                        # Check overall pattern limit before expensive calculations
                        if len(patterns) >= max_patterns:
                            if log_details:
                                print(f"Reached maximum pattern limit of {max_patterns}")
                            return patterns

                        # Generate 6-line tolerance system with proper clamping
                        d_lines = []

                        # Get ranges
                        ad_min, ad_max = ratios['ad_xa']
                        cd_min, cd_max = ratios['cd_bc']

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

                        unique_d_lines.sort()

                        # Validate that D lines haven't been touched after point C
                        if df is not None and len(df) > 0:
                            # Use C index to find subsequent candles
                            c_index = c_idx

                            # Find all candles after point C index
                            if c_index + 1 < len(df):
                                candles_after_c = df.iloc[c_index + 1:]

                                if len(candles_after_c) > 0:
                                    # Check if any D line has been touched by subsequent price action
                                    pattern_is_formed = False
                                    high_col = 'High' if 'High' in df.columns else 'high'
                                    low_col = 'Low' if 'Low' in df.columns else 'low'

                                    for d_price in unique_d_lines:
                                        if is_bullish:
                                            # For bullish patterns, D is below current price
                                            # Pattern is formed if low price touches or goes below D line
                                            if (candles_after_c[low_col] <= d_price).any():
                                                pattern_is_formed = True
                                                if log_details:
                                                    print(f"Pattern {pattern_name} formed: Low {candles_after_c[low_col].min():.2f} touched D line {d_price:.2f}")
                                                break
                                        else:
                                            # For bearish patterns, D is above current price
                                            # Pattern is formed if high price touches or goes above D line
                                            if (candles_after_c[high_col] >= d_price).any():
                                                pattern_is_formed = True
                                                if log_details:
                                                    print(f"Pattern {pattern_name} formed: High {candles_after_c[high_col].max():.2f} touched D line {d_price:.2f}")
                                                break

                                    # Skip this pattern if it's already formed
                                    if pattern_is_formed:
                                        continue


                        pattern = {
                            'name': f"{pattern_name}_unformed",
                            'type': 'bullish' if is_bullish else 'bearish',
                            'points': {
                                'X': {'time': x_time, 'price': x_price},
                                'A': {'time': a_time, 'price': a_price},
                                'B': {'time': b_time, 'price': b_price},
                                'C': {'time': c_time, 'price': c_price},
                                'D_projected': {'d_lines': unique_d_lines}
                            },
                            'ratios': {
                                'ab_xa': ab_xa_ratio,
                                'bc_ab': bc_ab_ratio,
                                'total_d_lines': len(unique_d_lines),
                                'ad_xa_range': ratios['ad_xa'],
                                'cd_bc_range': ratios['cd_bc']
                            },
                            'indices': [x_idx, a_idx, b_idx, c_idx]
                        }
                        patterns.append(pattern)
                        patterns_found += 1
                        patterns_for_this_type += 1

                        if log_details:
                            print(f"Found unformed {pattern_name}: {len(unique_d_lines)} D projections")

                        # Set completion flag if we've found enough patterns of this type
                        if patterns_for_this_type >= MAX_PATTERNS_PER_TYPE:
                            pattern_completed = True
                            break

    if log_details:
        print(f"Unformed XABCD search complete. Found {patterns_found} patterns.")

    return patterns