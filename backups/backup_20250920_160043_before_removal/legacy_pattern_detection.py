"""
Pattern detection algorithms for harmonic patterns
Migrated from the original implementation
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


def detect_abcd_patterns(extremum_points: List[Tuple], log_details: bool = False) -> List[Dict]:
    """
    Detect AB=CD harmonic patterns from extremum points.

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
        log_details: Whether to print detailed logs

    Returns:
        List of dictionaries containing pattern information
    """
    patterns = []
    n = len(extremum_points)

    if n < 4:
        return patterns

    # Debug: print extremum points structure
    if log_details:
        print(f"\nDetecting ABCD with {n} extremum points:")
        for i, ep in enumerate(extremum_points[:10]):  # Show first 10
            point_type = "High" if ep[2] else "Low"
            print(f"  [{i}] {ep[0].date() if hasattr(ep[0], 'date') else ep[0]}: {ep[1]:.2f} ({point_type})")

    for i in range(n - 3):
        for j in range(i + 1, n - 2):  # Allow full range
            for k in range(j + 1, n - 1):
                for l in range(k + 1, n):
                    # Get points
                    A = extremum_points[i]
                    B = extremum_points[j]
                    C = extremum_points[k]
                    D = extremum_points[l]

                    # New approach: No alternation requirement, use value-based conditions
                    # Extract prices for easier comparison
                    a_price = A[1]
                    b_price = B[1]
                    c_price = C[1]
                    d_price = D[1]

                    # Check for bullish pattern conditions:
                    # Bullish ABCD: A(High) > B(Low), C(High) > B, C > D(Low), and C < A (lower high)
                    # Pattern shape: High -> Low -> Lower High -> Lower Low
                    bullish_conditions = (
                        A[2] == True and       # A must be a High
                        B[2] == False and      # B must be a Low
                        C[2] == True and       # C must be a High
                        D[2] == False and      # D must be a Low
                        a_price > b_price and  # A (high) > B (low)
                        c_price > b_price and  # C (high) > B (low)
                        c_price > d_price and  # C (high) > D (low)
                        c_price < a_price      # C makes a lower high than A
                    )

                    # Check for bearish pattern conditions:
                    # Bearish ABCD: A(Low) < B(High), C(Low) < B, C < D(High), and C > A (higher low)
                    # Pattern shape: Low -> High -> Higher Low -> Higher High
                    bearish_conditions = (
                        A[2] == False and      # A must be a Low
                        B[2] == True and       # B must be a High
                        C[2] == False and      # C must be a Low
                        D[2] == True and       # D must be a High
                        a_price < b_price and  # A (low) < B (high)
                        c_price < b_price and  # C (low) < B (high)
                        c_price < d_price and  # C (low) < D (high)
                        c_price > a_price      # C makes a higher low than A
                    )

                    # Skip if neither pattern type is satisfied
                    if not bullish_conditions and not bearish_conditions:
                        continue

                    # Determine pattern type based on conditions
                    is_bullish = bullish_conditions

                    # Calculate ratios
                    AB = abs(B[1] - A[1])
                    BC = abs(C[1] - B[1])
                    CD = abs(D[1] - C[1])

                    if AB == 0:
                        continue

                    # BC retracement of AB
                    bc_retracement = (BC / AB) * 100

                    # CD projection of BC
                    if BC == 0:
                        continue
                    cd_projection = (CD / BC) * 100

                    # Check against pattern ratios
                    for pattern_name, ratios in ABCD_PATTERN_RATIOS.items():
                        # Check if pattern type matches (bullish/bearish)
                        if is_bullish and 'bull' not in pattern_name:
                            continue
                        if not is_bullish and 'bear' not in pattern_name:
                            continue

                        # Check if ratios match
                        retr_min, retr_max = ratios['retr']
                        proj_min, proj_max = ratios['proj']

                        if retr_min <= bc_retracement <= retr_max and \
                           proj_min <= cd_projection <= proj_max:

                            pattern = {
                                'name': pattern_name,
                                'type': 'bullish' if is_bullish else 'bearish',
                                'points': {
                                    'A': {'time': A[0], 'price': A[1]},
                                    'B': {'time': B[0], 'price': B[1]},
                                    'C': {'time': C[0], 'price': C[1]},
                                    'D': {'time': D[0], 'price': D[1]}
                                },
                                'ratios': {
                                    'bc_retracement': bc_retracement,
                                    'cd_projection': cd_projection
                                },
                                'indices': [i, j, k, l]
                            }
                            patterns.append(pattern)

                            if log_details:
                                print(f"Found {pattern_name} ({pattern['type']}): "
                                      f"A={a_price:.2f}, B={b_price:.2f}, C={c_price:.2f}, D={d_price:.2f} | "
                                      f"BC={bc_retracement:.1f}%, CD={cd_projection:.1f}%")

    return patterns


def detect_xabcd_patterns(extremum_points: List[Tuple], log_details: bool = False) -> List[Dict]:
    """
    Detect XABCD harmonic patterns (Bat, Butterfly, Gartley, etc.) from extremum points.

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
        print(f"Searching for XABCD patterns with {n} extremum points...")

    # Use ALL extremum points (no artificial limits)
    patterns_checked = 0
    for x_idx in range(n - 4):
        for a_idx in range(x_idx + 1, n - 3):
            for b_idx in range(a_idx + 1, n - 2):
                for c_idx in range(b_idx + 1, n - 1):
                    for d_idx in range(c_idx + 1, n):

                        # Get points
                        X = extremum_points[x_idx]
                        A = extremum_points[a_idx]
                        B = extremum_points[b_idx]
                        C = extremum_points[c_idx]
                        D = extremum_points[d_idx]

                        patterns_checked += 1
                        if patterns_checked % 10000 == 0 and log_details:
                            print(f"Checked {patterns_checked} combinations...")

                        # Check alternating pattern
                        # Bullish: Low-High-Low-High-Low (X=Low, A=High, B=Low, C=High, D=Low)
                        # Bearish: High-Low-High-Low-High (X=High, A=Low, B=High, C=Low, D=High)

                        # Check that consecutive points alternate
                        if X[2] == A[2]:  # X and A must be opposite
                            continue
                        if A[2] == B[2]:  # A and B must be opposite
                            continue
                        if B[2] == C[2]:  # B and C must be opposite
                            continue
                        if C[2] == D[2]:  # C and D must be opposite
                            continue

                        # Check that points at same positions match
                        if X[2] != B[2]:  # X and B must be same type (both lows or both highs)
                            continue
                        if X[2] != D[2]:  # X and D must be same type
                            continue
                        if A[2] != C[2]:  # A and C must be same type
                            continue

                        is_bullish = not X[2]  # X is low for bullish

                        # Calculate legs
                        XA = abs(A[1] - X[1])
                        AB = abs(B[1] - A[1])
                        BC = abs(C[1] - B[1])
                        CD = abs(D[1] - C[1])
                        AD = abs(D[1] - A[1])

                        if XA == 0 or AB == 0 or BC == 0:
                            continue

                        # Calculate ratios
                        ab_xa = (AB / XA) * 100
                        bc_ab = (BC / AB) * 100
                        cd_bc = (CD / BC) * 100
                        ad_xa = (AD / XA) * 100

                        # Check against XABCD pattern ratios
                        for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
                            # Check pattern type
                            if is_bullish and 'bull' not in pattern_name:
                                continue
                            if not is_bullish and 'bear' not in pattern_name:
                                continue

                            # Check all ratio requirements
                            if ratios['ab_xa'][0] <= ab_xa <= ratios['ab_xa'][1] and \
                               ratios['bc_ab'][0] <= bc_ab <= ratios['bc_ab'][1] and \
                               ratios['cd_bc'][0] <= cd_bc <= ratios['cd_bc'][1] and \
                               ratios['ad_xa'][0] <= ad_xa <= ratios['ad_xa'][1]:

                                pattern = {
                                    'name': pattern_name,
                                    'type': 'bullish' if is_bullish else 'bearish',
                                    'points': {
                                        'X': {'time': X[0], 'price': X[1]},
                                        'A': {'time': A[0], 'price': A[1]},
                                        'B': {'time': B[0], 'price': B[1]},
                                        'C': {'time': C[0], 'price': C[1]},
                                        'D': {'time': D[0], 'price': D[1]}
                                    },
                                    'ratios': {
                                        'ab_xa': ab_xa,
                                        'bc_ab': bc_ab,
                                        'cd_bc': cd_bc,
                                        'ad_xa': ad_xa
                                    },
                                    'indices': [x_idx, a_idx, b_idx, c_idx, d_idx]
                                }
                                patterns.append(pattern)

                                if log_details:
                                    print(f"Found {pattern_name}: AB/XA={ab_xa:.1f}%, BC/AB={bc_ab:.1f}%, "
                                          f"CD/BC={cd_bc:.1f}%, AD/XA={ad_xa:.1f}%")

    return patterns


def detect_unformed_abcd_patterns(extremum_points: List[Tuple], log_details: bool = False) -> List[Dict]:
    """
    Detect unformed/incomplete AB=CD patterns (only A, B, C points).
    These patterns project potential D point.

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
        log_details: Whether to print detailed logs

    Returns:
        List of dictionaries containing pattern information with projected D point
    """
    patterns = []
    n = len(extremum_points)

    if n < 3:
        return patterns

    for i in range(n - 2):
        for j in range(i + 1, n - 1):
            for k in range(j + 1, n):
                # Get points
                A = extremum_points[i]
                B = extremum_points[j]
                C = extremum_points[k]

                # Check alternating pattern for A, B, C
                # For bearish: A(Low)-B(High)-C(Low) - expecting D(High)
                # For bullish: A(High)-B(Low)-C(High) - expecting D(Low)

                # A and C should be same type (both highs or both lows)
                if A[2] != C[2]:
                    continue

                # A and B should be opposite types
                if A[2] == B[2]:
                    continue

                # B and C should be opposite types
                if B[2] == C[2]:
                    continue

                is_bullish = A[2]  # A is high for bullish pattern

                # Add value validation for pattern structure
                a_price = A[1]
                b_price = B[1]
                c_price = C[1]

                if is_bullish:
                    # Bullish: A(High) > B(Low) and C(High) > B(Low)
                    if not (a_price > b_price and c_price > b_price):
                        continue
                else:
                    # Bearish: A(Low) < B(High) and C(Low) < B(High)
                    if not (a_price < b_price and c_price < b_price):
                        continue

                # Calculate existing ratios
                AB = abs(B[1] - A[1])
                BC = abs(C[1] - B[1])

                if AB == 0 or BC == 0:
                    continue

                bc_retracement = (BC / AB) * 100

                # Enhanced logic: Find ALL matching patterns for this BC retracement
                matching_patterns = []
                comprehensive_prz_zones = []

                # First pass: collect all matching patterns
                for pattern_name, ratios in ABCD_PATTERN_RATIOS.items():
                    if is_bullish and 'bull' not in pattern_name:
                        continue
                    if not is_bullish and 'bear' not in pattern_name:
                        continue

                    retr_min, retr_max = ratios['retr']
                    if retr_min <= bc_retracement <= retr_max:
                        matching_patterns.append(pattern_name)

                        # Calculate PRZ zone for this pattern
                        proj_min, proj_max = ratios['proj']

                        if is_bullish:
                            # Bullish: A(High)-B(Low)-C(High)-D(Low)
                            prz_min = C[1] - (BC * proj_max / 100)  # D is lower than C
                            prz_max = C[1] - (BC * proj_min / 100)
                        else:
                            # Bearish: A(Low)-B(High)-C(Low)-D(High)
                            prz_min = C[1] + (BC * proj_min / 100)  # D is higher than C
                            prz_max = C[1] + (BC * proj_max / 100)

                        comprehensive_prz_zones.append({
                            'min': prz_min,
                            'max': prz_max,
                            'proj_min': proj_min,
                            'proj_max': proj_max,
                            'pattern_source': pattern_name
                        })

                # If we found matching patterns, create ONE comprehensive pattern
                if matching_patterns:
                    # Sort PRZ zones by price for better visualization
                    comprehensive_prz_zones.sort(key=lambda x: x['min'])

                    # Use the first matching pattern as the base name
                    base_name = matching_patterns[0]

                    pattern = {
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
                            'matching_patterns': matching_patterns,  # THIS IS THE KEY FIELD!
                            'prz_zones': comprehensive_prz_zones
                        },
                        'indices': [i, j, k]
                    }
                    patterns.append(pattern)

                    if log_details:
                        prz_str = ", ".join([f"PRZ{i+1}: {z['min']:.2f}-{z['max']:.2f}" for i, z in enumerate(comprehensive_prz_zones)])
                        print(f"Found comprehensive unformed pattern with {len(matching_patterns)} matches: {prz_str}")

    return patterns


def detect_unformed_xabcd_patterns(extremum_points: List[Tuple], log_details: bool = False) -> List[Dict]:
    """
    Detect unformed/incomplete XABCD patterns (only X, A, B, C points).
    These patterns project potential D point.

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
        log_details: Whether to print detailed logs

    Returns:
        List of dictionaries containing pattern information with projected D point
    """
    patterns = []
    n = len(extremum_points)

    if n < 4:
        return patterns

    # Use ALL extremum points (no artificial limits)
    for x_idx in range(n - 3):
        for a_idx in range(x_idx + 1, n - 2):
            for b_idx in range(a_idx + 1, n - 1):
                for c_idx in range(b_idx + 1, n):

                    X = extremum_points[x_idx]
                    A = extremum_points[a_idx]
                    B = extremum_points[b_idx]
                    C = extremum_points[c_idx]

                    # Check alternating pattern for X, A, B, C
                    if X[2] == A[2] or A[2] == B[2] or B[2] == C[2]:
                        continue
                    if X[2] != C[2]:
                        continue

                    is_bullish = not X[2]

                    # Add value validation for unformed XABCD
                    x_price = X[1]
                    a_price = A[1]
                    b_price = B[1]
                    c_price = C[1]

                    if is_bullish:
                        # Bullish: X < A, B < A, C > B
                        if not (x_price < a_price and b_price < a_price and c_price > b_price):
                            continue
                    else:
                        # Bearish: X > A, B > A, C < B
                        if not (x_price > a_price and b_price > a_price and c_price < b_price):
                            continue

                    # Calculate existing legs
                    XA = abs(A[1] - X[1])
                    AB = abs(B[1] - A[1])
                    BC = abs(C[1] - B[1])

                    if XA == 0 or AB == 0 or BC == 0:
                        continue

                    # Calculate existing ratios
                    ab_xa = (AB / XA) * 100
                    bc_ab = (BC / AB) * 100

                    # Check against XABCD patterns
                    for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
                        if is_bullish and 'bull' not in pattern_name:
                            continue
                        if not is_bullish and 'bear' not in pattern_name:
                            continue

                        # Check if existing ratios match
                        if ratios['ab_xa'][0] <= ab_xa <= ratios['ab_xa'][1] and \
                           ratios['bc_ab'][0] <= bc_ab <= ratios['bc_ab'][1]:

                            # Generate 6-line tolerance system
                            d_lines = []

                            # Get ranges
                            ad_min, ad_max = ratios['ad_xa']
                            cd_min, cd_max = ratios['cd_bc']

                            # Calculate averages
                            ad_avg = (ad_min + ad_max) / 2
                            cd_avg = (cd_min + cd_max) / 2

                            # Method 1: Fix AD ratios, calculate D
                            for ad_ratio in [ad_avg, ad_max, ad_min]:
                                projected_ad = XA * (ad_ratio / 100)
                                if is_bullish:
                                    d_from_ad = A[1] - projected_ad  # D below A
                                else:
                                    d_from_ad = A[1] + projected_ad  # D above A
                                d_lines.append(d_from_ad)

                            # Method 2: Fix CD ratios, calculate D
                            for cd_ratio in [cd_avg, cd_max, cd_min]:
                                projected_cd = BC * (cd_ratio / 100)
                                if is_bullish:
                                    d_from_cd = C[1] - projected_cd  # D below C
                                else:
                                    d_from_cd = C[1] + projected_cd  # D above C
                                d_lines.append(d_from_cd)

                            # Remove duplicates (within 0.1 tolerance)
                            unique_d_lines = []
                            for d_price in d_lines:
                                is_duplicate = any(abs(d_price - existing) < 0.1 for existing in unique_d_lines)
                                if not is_duplicate:
                                    unique_d_lines.append(d_price)

                            unique_d_lines.sort()

                            pattern = {
                                'name': f"{pattern_name}_unformed",
                                'type': 'bullish' if is_bullish else 'bearish',
                                'points': {
                                    'X': {'time': X[0], 'price': X[1]},
                                    'A': {'time': A[0], 'price': A[1]},
                                    'B': {'time': B[0], 'price': B[1]},
                                    'C': {'time': C[0], 'price': C[1]},
                                    'D_projected': {'d_lines': unique_d_lines}
                                },
                                'ratios': {
                                    'ab_xa': ab_xa,
                                    'bc_ab': bc_ab,
                                    'total_d_lines': len(unique_d_lines),
                                    'ad_xa_range': ratios['ad_xa'],
                                    'cd_bc_range': ratios['cd_bc']
                                },
                                'indices': [x_idx, a_idx, b_idx, c_idx]
                            }
                            patterns.append(pattern)

                            if log_details:
                                print(f"Found unformed {pattern_name}: D projected at {projected_d:.2f}")

    return patterns


def calculate_prz(pattern: Dict) -> Dict:
    """
    Calculate Potential Reversal Zone (PRZ) for a pattern.

    Args:
        pattern: Dictionary containing pattern information

    Returns:
        Dictionary with PRZ information
    """
    prz = {
        'zones': [],
        'levels': [],
        'range': [float('inf'), float('-inf')]
    }

    if 'D_projected' in pattern['points']:
        # For unformed patterns with PRZ zones
        if 'prz_zones' in pattern['points']['D_projected']:
            prz_zones = pattern['points']['D_projected']['prz_zones']
            prz['zones'] = prz_zones

            # Calculate overall range
            all_mins = [z['min'] for z in prz_zones]
            all_maxs = [z['max'] for z in prz_zones]
            prz['range'] = [min(all_mins), max(all_maxs)]

            # Add individual levels
            for zone in prz_zones:
                prz['levels'].extend([zone['min'], zone['max']])
        elif 'price' in pattern['points']['D_projected']:
            # Old format with single D price (backward compatibility)
            d_price = pattern['points']['D_projected']['price']
            tolerance = d_price * 0.01  # 1% tolerance
            prz['range'] = [d_price - tolerance, d_price + tolerance]
            prz['levels'] = [d_price]
            prz['zones'] = [{'min': d_price - tolerance, 'max': d_price + tolerance}]
    elif 'D' in pattern['points']:
        # For completed patterns, PRZ is at D
        d_price = pattern['points']['D']['price']
        prz['range'] = [d_price * 0.99, d_price * 1.01]
        prz['levels'] = [d_price]
        prz['zones'] = [{'min': d_price * 0.99, 'max': d_price * 1.01}]

    return prz