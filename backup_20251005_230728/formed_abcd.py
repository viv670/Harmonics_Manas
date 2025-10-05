"""
Formed ABCD Pattern Detection Module
Detects complete ABCD patterns (4-point patterns A-B-C-D)

This module provides:
1. Formed ABCD patterns with strict price containment validation
2. Optimized performance with pattern lookup
3. Comprehensive validation to ensure clean pattern formation
"""

from typing import List, Tuple, Dict, Optional
import pandas as pd
import numpy as np
from pattern_ratios_2_Final import ABCD_PATTERN_RATIOS
from pattern_data_standard import StandardPattern, PatternPoint, standardize_pattern_name, fix_unicode_issues

# Configuration constants
EPSILON = 1e-10
DEFAULT_MAX_PATTERNS = 50
DEFAULT_SEARCH_WINDOW = 20


def validate_price_containment_bullish(df: pd.DataFrame,
                                      a_idx: int, b_idx: int,
                                      c_idx: int, d_idx: int,
                                      a_price: float, b_price: float,
                                      c_price: float, d_price: float) -> bool:
    """
    Validate price containment for bullish formed ABCD patterns.

    Bullish: A(High) -> B(Low) -> C(High) -> D(Low)

    Rules:
    1. A->B: No candle between A and B has a high that exceeds A
    2. B->C: No candle between A and C has a low that breaks B
    3. C->D: No candle between B and D has a high that exceeds C
    4. C->D: No candle between C and D has a low that breaks D
    """
    # Assertions for 100% accuracy
    assert df is not None, "DataFrame cannot be None for validation"
    assert isinstance(a_idx, (int, np.integer)), f"a_idx must be integer, got {type(a_idx)}"
    assert isinstance(b_idx, (int, np.integer)), f"b_idx must be integer, got {type(b_idx)}"
    assert isinstance(c_idx, (int, np.integer)), f"c_idx must be integer, got {type(c_idx)}"
    assert isinstance(d_idx, (int, np.integer)), f"d_idx must be integer, got {type(d_idx)}"
    assert 0 <= a_idx < len(df), f"a_idx {a_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= b_idx < len(df), f"b_idx {b_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= c_idx < len(df), f"c_idx {c_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= d_idx < len(df), f"d_idx {d_idx} out of bounds (0-{len(df)-1})"
    assert a_idx <= b_idx <= c_idx <= d_idx, f"Invalid index order: A({a_idx}) <= B({b_idx}) <= C({c_idx}) <= D({d_idx})"

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

        # Check B to D: no high exceeds C (excluding C, D endpoints)
        if b_idx < d_idx:
            segment_bd = df.iloc[b_idx:d_idx]
            if any(segment_bd[high_col] > c_price):
                return False

        # Check C to D: no low breaks D (excluding D itself, as D IS the low)
        if c_idx < d_idx:
            segment_cd = df.iloc[c_idx:d_idx]
            if any(segment_cd[low_col] < d_price):
                return False

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.error(f"Validation error in validate_price_containment_bullish: {e}")
        # For 100% accuracy, treat errors as validation failures
        return False


def validate_price_containment_bearish(df: pd.DataFrame,
                                      a_idx: int, b_idx: int,
                                      c_idx: int, d_idx: int,
                                      a_price: float, b_price: float,
                                      c_price: float, d_price: float) -> bool:
    """
    Validate price containment for bearish formed ABCD patterns.

    Bearish: A(Low) -> B(High) -> C(Low) -> D(High)

    Rules:
    1. A->B: No candle between A and B has a low that breaks A
    2. B->C: No candle between A and C has a high that exceeds B
    3. C->D: No candle between B and D has a low that breaks C
    4. C->D: No candle between C and D has a high that exceeds D
    """
    # Assertions for 100% accuracy
    assert df is not None, "DataFrame cannot be None for validation"
    assert isinstance(a_idx, (int, np.integer)), f"a_idx must be integer, got {type(a_idx)}"
    assert isinstance(b_idx, (int, np.integer)), f"b_idx must be integer, got {type(b_idx)}"
    assert isinstance(c_idx, (int, np.integer)), f"c_idx must be integer, got {type(c_idx)}"
    assert isinstance(d_idx, (int, np.integer)), f"d_idx must be integer, got {type(d_idx)}"
    assert 0 <= a_idx < len(df), f"a_idx {a_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= b_idx < len(df), f"b_idx {b_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= c_idx < len(df), f"c_idx {c_idx} out of bounds (0-{len(df)-1})"
    assert 0 <= d_idx < len(df), f"d_idx {d_idx} out of bounds (0-{len(df)-1})"
    assert a_idx <= b_idx <= c_idx <= d_idx, f"Invalid index order: A({a_idx}) <= B({b_idx}) <= C({c_idx}) <= D({d_idx})"

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

        # Check B to D: no low breaks C (excluding C, D endpoints)
        if b_idx < d_idx:
            segment_bd = df.iloc[b_idx:d_idx]
            if any(segment_bd[low_col] < c_price):
                return False

        # Check C to D: no high exceeds D (excluding D itself, as D IS the high)
        if c_idx < d_idx:
            segment_cd = df.iloc[c_idx:d_idx]
            if any(segment_cd[high_col] > d_price):
                return False

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.error(f"Validation error in validate_price_containment_bearish: {e}")
        # For 100% accuracy, treat errors as validation failures
        return False


def detect_strict_abcd_patterns(extremum_points: List[Tuple],
                               df: pd.DataFrame,
                               log_details: bool = False,
                               max_patterns: int = 50,
                               max_search_window: int = 20,
                               validate_d_crossing: bool = True) -> List[Dict]:
    """
    Detect complete ABCD patterns (4-point patterns) with strict validation.

    Each ABCD pattern consists of exactly 4 points (A, B, C, D).
    From a list of many extremum points, this function finds all valid
    4-point combinations that form ABCD patterns according to the ratios.

    Args:
        extremum_points: List of extremum points to search for patterns within
                        Format: (timestamp, price, is_high, bar_index)
                        Must contain at least 4 points
        df: DataFrame with OHLC data for validation
        log_details: Whether to print detailed logs
        max_patterns: Maximum number of patterns to return
        max_search_window: Maximum distance between pattern points (None = unlimited)
        validate_d_crossing: If True, reject patterns where price crosses D after formation.
                           If False, allow patterns even if D is violated later.
                           Default=True for strict validation.

    Returns:
        List of dictionaries containing formed ABCD patterns
    """
    patterns = []
    n = len(extremum_points)

    if n < 4:
        if log_details:
            print(f"Insufficient extremum points for ABCD detection: need at least 4, found {n}")
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

    # Formed ABCD detection starting (verbose output removed for cleaner console)

    # OPTIMIZATION: Cache D point crossing checks to avoid redundant calculations
    high_col = 'High' if 'High' in df_copy.columns else 'high'
    low_col = 'Low' if 'Low' in df_copy.columns else 'low'

    # Cache for D point crossing checks: (d_idx, d_price, is_bullish) -> bool
    d_point_crossing_cache = {}

    # Separate highs and lows with bar indices
    highs = []
    lows = []

    for i, ep in enumerate(extremum_points):
        # Get bar index from 4th element
        bar_idx = ep[3] if len(ep) > 3 else i

        if ep[2]:  # Is high
            highs.append((bar_idx, ep[0], ep[1]))
        else:  # Is low
            lows.append((bar_idx, ep[0], ep[1]))

    # Highs and lows separated (debug output removed)

    patterns_found = 0
    patterns_checked = 0
    patterns_rejected = 0

    # Use all points in the dataset
    MAX_CANDIDATES = len(extremum_points)

    for pattern_name, ratio_range in ABCD_PATTERN_RATIOS.items():
        if max_patterns is not None and patterns_found >= max_patterns:
            break

        is_bullish = 'bull' in pattern_name

        # Select appropriate candidates
        if is_bullish:
            a_candidates = highs[-MAX_CANDIDATES:] if len(highs) > MAX_CANDIDATES else highs
            b_candidates = lows[-MAX_CANDIDATES:] if len(lows) > MAX_CANDIDATES else lows
            c_candidates = highs[-MAX_CANDIDATES:] if len(highs) > MAX_CANDIDATES else highs
            d_candidates = lows[-MAX_CANDIDATES:] if len(lows) > MAX_CANDIDATES else lows
        else:
            a_candidates = lows[-MAX_CANDIDATES:] if len(lows) > MAX_CANDIDATES else lows
            b_candidates = highs[-MAX_CANDIDATES:] if len(highs) > MAX_CANDIDATES else highs
            c_candidates = lows[-MAX_CANDIDATES:] if len(lows) > MAX_CANDIDATES else lows
            d_candidates = highs[-MAX_CANDIDATES:] if len(highs) > MAX_CANDIDATES else highs

        # Search for valid patterns
        for i, (a_idx, a_time, a_price) in enumerate(a_candidates):
            if max_patterns is not None and patterns_found >= max_patterns:
                break

            # Find valid B points
            if max_search_window is not None:
                valid_b = [b for b in b_candidates
                          if a_idx < b[0] <= min(a_idx + max_search_window, len(df)-1)]
            else:
                valid_b = [b for b in b_candidates if a_idx < b[0]]

            for b_idx, b_time, b_price in valid_b:
                if max_patterns is not None and patterns_found >= max_patterns:
                    break

                ab_move = abs(b_price - a_price)
                if ab_move == 0:
                    continue

                # Find valid C points
                if max_search_window is not None:
                    valid_c = [c for c in c_candidates
                              if b_idx < c[0] <= min(b_idx + max_search_window, len(df)-1)]
                else:
                    valid_c = [c for c in c_candidates if b_idx < c[0]]

                for c_idx, c_time, c_price in valid_c:
                    if max_patterns is not None and patterns_found >= max_patterns:
                        break

                    # Calculate BC retracement
                    bc_move = abs(c_price - b_price)
                    bc_retracement = (bc_move / ab_move) * 100

                    # Check if BC retracement is within range
                    if not (ratio_range['retr'][0] <= bc_retracement <= ratio_range['retr'][1]):
                        continue

                    # Find valid D points
                    if max_search_window is not None:
                        valid_d = [d for d in d_candidates
                                  if c_idx < d[0] <= min(c_idx + max_search_window, len(df)-1)]
                    else:
                        valid_d = [d for d in d_candidates if c_idx < d[0]]

                    for d_idx, d_time, d_price in valid_d:
                        if max_patterns is not None and patterns_found >= max_patterns:
                            break

                        patterns_checked += 1

                        # Calculate CD projection
                        cd_move = abs(d_price - c_price)
                        cd_projection = (cd_move / (bc_move + EPSILON)) * 100

                        # Check if CD projection is within range
                        if not (ratio_range['proj'][0] <= cd_projection <= ratio_range['proj'][1]):
                            continue

                        # Validate pattern structure
                        if is_bullish:
                            structure_valid = (
                                a_price > b_price and
                                c_price > b_price and
                                c_price > d_price and
                                c_price < a_price
                            )
                        else:
                            structure_valid = (
                                a_price < b_price and
                                c_price < b_price and
                                c_price < d_price and
                                c_price > a_price
                            )

                        if not structure_valid:
                            continue

                        # Apply strict validation
                        try:
                            # Use bar indices directly
                            a_candle_idx = a_idx
                            b_candle_idx = b_idx
                            c_candle_idx = c_idx
                            d_candle_idx = d_idx

                            if None in [a_candle_idx, b_candle_idx, c_candle_idx, d_candle_idx]:
                                patterns_rejected += 1
                                continue

                            # Validate price containment
                            if is_bullish:
                                containment_valid = validate_price_containment_bullish(
                                    df_copy, a_candle_idx, b_candle_idx, c_candle_idx, d_candle_idx,
                                    a_price, b_price, c_price, d_price
                                )
                            else:
                                containment_valid = validate_price_containment_bearish(
                                    df_copy, a_candle_idx, b_candle_idx, c_candle_idx, d_candle_idx,
                                    a_price, b_price, c_price, d_price
                                )

                            if not containment_valid:
                                patterns_rejected += 1
                                if log_details:
                                    print(f"  Rejected {pattern_name}: Failed strict price containment")
                                continue

                        except Exception as e:
                            if log_details:
                                print(f"  Error validating containment: {str(e)}")
                            patterns_rejected += 1
                            continue

                        # Calculate PRZ zones using the pattern's projection ratios
                        # This shows where D was expected based on BC move
                        proj_min = ratio_range['proj'][0]
                        proj_max = ratio_range['proj'][1]

                        if is_bullish:
                            # For bullish: D is below C
                            prz_min = c_price - (bc_move * proj_max / 100)
                            prz_max = c_price - (bc_move * proj_min / 100)
                        else:
                            # For bearish: D is above C
                            prz_min = c_price + (bc_move * proj_min / 100)
                            prz_max = c_price + (bc_move * proj_max / 100)

                        # Validate that D point is within PRZ zone
                        if not (prz_min <= d_price <= prz_max):
                            patterns_rejected += 1
                            if log_details:
                                print(f"  Rejected {pattern_name}: D point {d_price:.2f} not in PRZ [{prz_min:.2f}, {prz_max:.2f}]")
                            continue

                        # Validate that price doesn't cross D point after formation (OPTIONAL)
                        # OPTIMIZED: Cache results to avoid recalculating for same D point
                        if validate_d_crossing and d_idx < len(df_copy) - 1:
                            # Create cache key for this D point check
                            cache_key = (d_idx, d_price, is_bullish)

                            # Check if we've already validated this D point
                            if cache_key not in d_point_crossing_cache:
                                # Calculate and cache the result
                                d_point_crossed = False
                                if is_bullish:
                                    # For bullish: D is a low, check if any bar after D goes below D
                                    min_low_after = df_copy[low_col].iloc[d_idx+1:].min()
                                    if min_low_after < d_price:
                                        d_point_crossed = True
                                else:
                                    # For bearish: D is a high, check if any bar after D goes above D
                                    max_high_after = df_copy[high_col].iloc[d_idx+1:].max()
                                    if max_high_after > d_price:
                                        d_point_crossed = True

                                d_point_crossing_cache[cache_key] = d_point_crossed

                            # Use cached result
                            if d_point_crossing_cache[cache_key]:
                                patterns_rejected += 1
                                continue

                        # Create PRZ zone for this pattern
                        prz_zones = [{
                            'min': prz_min,
                            'max': prz_max,
                            'proj_min': proj_min,
                            'proj_max': proj_max,
                            'pattern_source': pattern_name
                        }]

                        # Create standardized pattern object
                        direction = 'bullish' if is_bullish else 'bearish'
                        pattern_name_std = standardize_pattern_name(pattern_name, 'formed', direction)
                        pattern_name_std = fix_unicode_issues(pattern_name_std)

                        # Create pattern points with proper indices
                        a_point = PatternPoint(timestamp=a_time, price=a_price, index=a_idx)
                        b_point = PatternPoint(timestamp=b_time, price=b_price, index=b_idx)
                        c_point = PatternPoint(timestamp=c_time, price=c_price, index=c_idx)
                        d_point = PatternPoint(timestamp=d_time, price=d_price, index=d_idx)

                        # Create standardized pattern
                        standard_pattern = StandardPattern(
                            name=pattern_name_std,
                            pattern_type='ABCD',
                            formation_status='formed',
                            direction=direction,
                            x_point=None,  # ABCD patterns don't have X point
                            a_point=a_point,
                            b_point=b_point,
                            c_point=c_point,
                            d_point=d_point,
                            ratios={
                                'bc_retracement': bc_retracement,
                                'cd_projection': cd_projection,
                                'prz_zones': prz_zones  # Add PRZ zones to ratios
                            },
                            validation_type='strict_containment'
                        )

                        # Convert to legacy dict format for backward compatibility
                        pattern = standard_pattern.to_legacy_dict()

                        patterns.append(pattern)
                        patterns_found += 1

    # Detection complete (verbose summary removed for cleaner console)

    return patterns


if __name__ == "__main__":
    # Test the formed detection
    print("Testing Formed ABCD Pattern Detection...")

    # Load test data
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

    extremum_points = find_pivot_points(df, window=5)
    print(f"Found {len(extremum_points)} extremum points")

    # Detect formed patterns
    print("\nDetecting Formed ABCD Patterns...")
    formed_patterns = detect_strict_abcd_patterns(
        extremum_points, df, log_details=True, max_patterns=20
    )

    print(f"\nTotal formed patterns found: {len(formed_patterns)}")

    # Show example patterns
    if formed_patterns:
        print("\n" + "="*60)
        print("EXAMPLE FORMED PATTERN")
        print("="*60)
        p = formed_patterns[0]
        print(f"Name: {p['name']}")
        print(f"Type: {p['type']}")
        print(f"BC Retracement: {p['ratios']['bc_retracement']:.1f}%")
        print(f"CD Projection: {p['ratios']['cd_projection']:.1f}%")