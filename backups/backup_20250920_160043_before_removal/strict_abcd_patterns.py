"""
Strict ABCD Pattern Detection with Price Containment Validation

This module implements ABCD pattern detection with additional strict conditions:
- No price violations during pattern formation
- Clean price movements between pattern points
- Validates using actual OHLC candle data, not just extremum points

For Bullish Patterns (High-Low-High-Low):
1. A→B: No candle high should exceed A
2. B→C: No candle low should break below B
3. C→D: No candle high should exceed C

For Bearish Patterns (Low-High-Low-High):
1. A→B: No candle low should break below A
2. B→C: No candle high should exceed B
3. C→D: No candle low should break below C
"""

from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from pattern_ratios_2_Final import ABCD_PATTERN_RATIOS


def validate_price_containment_bullish(df: pd.DataFrame,
                                      a_idx: int, b_idx: int,
                                      c_idx: int, d_idx: int,
                                      a_price: float, b_price: float,
                                      c_price: float, d_price: float) -> bool:
    """
    Validate price containment for bullish ABCD pattern.

    Bullish: A(High) -> B(Low) -> C(High) -> D(Low)

    Rules:
    1. A→B: No candle between A and B has a high that exceeds A
    2. B→C: No candle between A and C has a low that breaks B
    3. C→D: No candle between B and D has a high that exceeds C
    4. After D: No candle between C and end has a low that breaks D
    """
    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Check A to B: no high exceeds A
        if a_idx < b_idx:
            segment_ab = df.iloc[a_idx:b_idx+1]
            if any(segment_ab[high_col] > a_price):
                return False

        # Check A to C: no low breaks B (B must be the lowest from A to C)
        if a_idx < c_idx:
            segment_ac = df.iloc[a_idx:c_idx+1]
            if any(segment_ac[low_col] < b_price):
                return False

        # Check B to D: no high exceeds C (C must be the highest from B to D)
        if b_idx < d_idx:
            segment_bd = df.iloc[b_idx:d_idx+1]
            if any(segment_bd[high_col] > c_price):
                return False

        # Check C to D: no low breaks D (D must hold as support from C to D)
        if c_idx < d_idx:
            segment_cd = df.iloc[c_idx:d_idx+1]
            if any(segment_cd[low_col] < d_price):
                return False

        # All checks passed

        return True

    except Exception as e:
        # If we can't validate (missing data, etc), be conservative
        return False


def validate_price_containment_bearish(df: pd.DataFrame,
                                      a_idx: int, b_idx: int,
                                      c_idx: int, d_idx: int,
                                      a_price: float, b_price: float,
                                      c_price: float, d_price: float) -> bool:
    """
    Validate price containment for bearish ABCD pattern.

    Bearish: A(Low) -> B(High) -> C(Low) -> D(High)

    Rules:
    1. A→B: No candle between A and B has a low that breaks A
    2. B→C: No candle between A and C has a high that exceeds B
    3. C→D: No candle between B and D has a low that breaks C
    4. After D: No candle between C and end has a high that exceeds D
    """
    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Check A to B: no low breaks A
        if a_idx < b_idx:
            segment_ab = df.iloc[a_idx:b_idx+1]
            if any(segment_ab[low_col] < a_price):
                return False

        # Check A to C: no high exceeds B (B must be the highest from A to C)
        if a_idx < c_idx:
            segment_ac = df.iloc[a_idx:c_idx+1]
            if any(segment_ac[high_col] > b_price):
                return False

        # Check B to D: no low breaks C (C must be the lowest from B to D)
        if b_idx < d_idx:
            segment_bd = df.iloc[b_idx:d_idx+1]
            if any(segment_bd[low_col] < c_price):
                return False

        # Check C to D: no high exceeds D (D must hold as resistance from C to D)
        if c_idx < d_idx:
            segment_cd = df.iloc[c_idx:d_idx+1]
            if any(segment_cd[high_col] > d_price):
                return False

        # All checks passed

        return True

    except Exception as e:
        # If we can't validate (missing data, etc), be conservative
        return False


def detect_strict_abcd_patterns(extremum_points: List[Tuple],
                                df: pd.DataFrame,
                                log_details: bool = False,
                                max_patterns: int = 50,
                                max_search_window: int = 20) -> List[Dict]:
    """
    Detect ABCD patterns with strict price containment validation.

    This function finds ABCD patterns that not only meet the ratio requirements
    but also have clean price movements without any violations.

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
        df: DataFrame with OHLC data for validation
        log_details: Whether to print detailed logs

    Returns:
        List of dictionaries containing validated ABCD patterns
    """
    patterns = []
    n = len(extremum_points)

    if n < 4:
        if log_details:
            print(f"Not enough extremum points for strict ABCD: {n} < 4")
        return patterns

    if df is None or df.empty:
        if log_details:
            print("No DataFrame provided for strict validation")
        return patterns

    # Convert DataFrame index to timestamp for matching
    df_copy = df.copy()

    # Create timestamp column from index
    if isinstance(df_copy.index, pd.DatetimeIndex):
        df_copy.reset_index(inplace=True)
        # The datetime index becomes a column (usually named 'index' or 'Date')
        timestamp_col = df_copy.columns[0]  # First column after reset_index
        df_copy['timestamp'] = pd.to_datetime(df_copy[timestamp_col])
    else:
        # Try to find a date/time column
        if 'Date' in df_copy.columns:
            df_copy['timestamp'] = pd.to_datetime(df_copy['Date'])
        elif 'Datetime' in df_copy.columns:
            df_copy['timestamp'] = pd.to_datetime(df_copy['Datetime'])
        elif 'Time' in df_copy.columns:
            df_copy['timestamp'] = pd.to_datetime(df_copy['Time'])
        else:
            # Use the index as timestamp
            df_copy.reset_index(inplace=True)
            df_copy['timestamp'] = pd.to_datetime(df_copy['index'])

    if log_details:
        print(f"\nDetecting Strict ABCD patterns with {n} extremum points")
        print(f"DataFrame has {len(df_copy)} candles for validation")
        print(f"Max patterns limit: {max_patterns}")
        print(f"Search window: {max_search_window}")

    # Separate highs and lows with their indices
    highs = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if ep[2]]
    lows = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if not ep[2]]

    patterns_found = 0
    patterns_rejected = 0
    patterns_checked = 0

    # Early termination if we have enough patterns
    if patterns_found >= max_patterns:
        return patterns[:max_patterns]

    for pattern_name, ratio_range in ABCD_PATTERN_RATIOS.items():
        if patterns_found >= max_patterns:
            break
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

        # Iterate through all valid combinations with search window limit
        for i, (a_idx, a_time, a_price) in enumerate(a_candidates):
            if patterns_found >= max_patterns:
                break

            # Find valid B points (after A) with window limit
            valid_b = [b for b in b_candidates
                      if a_idx < b[0] <= min(a_idx + max_search_window, n-1)]

            for b_idx, b_time, b_price in valid_b:
                if patterns_found >= max_patterns:
                    break
                # Calculate AB move
                ab_move = abs(b_price - a_price)
                if ab_move == 0:
                    continue

                # Find valid C points (after B) with window limit
                valid_c = [c for c in c_candidates
                          if b_idx < c[0] <= min(b_idx + max_search_window, n-1)]

                for c_idx, c_time, c_price in valid_c:
                    if patterns_found >= max_patterns:
                        break
                    # Calculate BC retracement
                    bc_move = abs(c_price - b_price)
                    bc_retracement = (bc_move / ab_move) * 100

                    # Check if BC retracement is within pattern requirements
                    if not (ratio_range['retr'][0] <= bc_retracement <= ratio_range['retr'][1]):
                        continue

                    # Find valid D points (after C) with window limit
                    valid_d = [d for d in d_candidates
                              if c_idx < d[0] <= min(c_idx + max_search_window, n-1)]

                    for d_idx, d_time, d_price in valid_d:
                        if patterns_found >= max_patterns:
                            break

                        patterns_checked += 1

                        # Log progress every 1000 patterns
                        if patterns_checked % 1000 == 0 and log_details:
                            print(f"  Checked {patterns_checked} combinations, found {patterns_found} valid patterns")
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
                            structure_valid = (
                                a_price > b_price and  # A (high) > B (low)
                                c_price > b_price and  # C (high) > B (low)
                                c_price > d_price and  # C (high) > D (low)
                                c_price < a_price      # C makes a lower high than A
                            )
                        else:
                            # Bearish conditions
                            structure_valid = (
                                a_price < b_price and  # A (low) < B (high)
                                c_price < b_price and  # C (low) < B (high)
                                c_price < d_price and  # C (low) < D (high)
                                c_price > a_price      # C makes a higher low than A
                            )

                        if not structure_valid:
                            continue

                        # Now apply STRICT VALIDATION - find candle indices in DataFrame
                        try:
                            # Find the closest candle indices in the DataFrame (within 1 minute tolerance)
                            time_tolerance = pd.Timedelta(minutes=1)

                            # Find closest timestamp for each point
                            def find_closest_idx(target_time):
                                time_diff = abs(df_copy['timestamp'] - pd.to_datetime(target_time))
                                if time_diff.min() <= time_tolerance:
                                    return time_diff.idxmin()
                                return None

                            a_candle_idx = find_closest_idx(a_time)
                            b_candle_idx = find_closest_idx(b_time)
                            c_candle_idx = find_closest_idx(c_time)
                            d_candle_idx = find_closest_idx(d_time)

                            if None in [a_candle_idx, b_candle_idx, c_candle_idx, d_candle_idx]:
                                patterns_rejected += 1
                                if log_details:
                                    print(f"  Rejected: Could not find matching candles in DataFrame")
                                    print(f"    A: {a_time} -> {a_candle_idx}")
                                    print(f"    B: {b_time} -> {b_candle_idx}")
                                    print(f"    C: {c_time} -> {c_candle_idx}")
                                    print(f"    D: {d_time} -> {d_candle_idx}")
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

                        # Pattern is valid with strict conditions!
                        pattern = {
                            'name': f"{pattern_name}_strict",
                            'type': 'bullish' if is_bullish else 'bearish',
                            'points': {
                                'A': {'time': a_time, 'price': a_price},
                                'B': {'time': b_time, 'price': b_price},
                                'C': {'time': c_time, 'price': c_price},
                                'D': {'time': d_time, 'price': d_price}
                            },
                            'ratios': {
                                'bc_retracement': bc_retracement,
                                'cd_projection': cd_projection
                            },
                            'indices': {
                                'A': a_idx,
                                'B': b_idx,
                                'C': c_idx,
                                'D': d_idx
                            },
                            'validation': 'strict_containment'
                        }

                        patterns.append(pattern)
                        patterns_found += 1

                        if log_details:
                            print(f"Found STRICT {pattern_name} ({'bullish' if is_bullish else 'bearish'}): "
                                  f"A={a_price:.2f}, B={b_price:.2f}, C={c_price:.2f}, D={d_price:.2f} | "
                                  f"BC={bc_retracement:.1f}%, CD={cd_projection:.1f}%")

    if log_details:
        print(f"\nStrict ABCD Detection Summary:")
        print(f"  Checked: {patterns_checked} pattern combinations")
        print(f"  Found: {patterns_found} patterns with strict validation")
        print(f"  Rejected: {patterns_rejected} patterns due to price violations")
        print(f"  Total returned: {len(patterns)} strict ABCD patterns")

    return patterns


def compare_patterns(regular_patterns: List[Dict], strict_patterns: List[Dict], log_details: bool = False):
    """
    Compare regular ABCD patterns with strict validated patterns.

    Args:
        regular_patterns: List of regular ABCD patterns
        strict_patterns: List of strict ABCD patterns
        log_details: Whether to print comparison details
    """
    if log_details:
        print("\n" + "="*60)
        print("PATTERN COMPARISON: Regular vs Strict")
        print("="*60)

        print(f"\nRegular ABCD Patterns: {len(regular_patterns)}")
        print(f"Strict ABCD Patterns: {len(strict_patterns)}")

        # Find patterns that were filtered out
        regular_signatures = set()
        for p in regular_patterns:
            sig = (p['points']['A']['price'], p['points']['B']['price'],
                   p['points']['C']['price'], p['points']['D']['price'])
            regular_signatures.add(sig)

        strict_signatures = set()
        for p in strict_patterns:
            sig = (p['points']['A']['price'], p['points']['B']['price'],
                   p['points']['C']['price'], p['points']['D']['price'])
            strict_signatures.add(sig)

        filtered_out = regular_signatures - strict_signatures
        print(f"\nPatterns filtered by strict validation: {len(filtered_out)}")
        print(f"Success rate: {len(strict_patterns)/len(regular_patterns)*100:.1f}%" if regular_patterns else "N/A")

        # Show some examples of filtered patterns
        if filtered_out and log_details:
            print("\nExamples of patterns rejected by strict validation:")
            for i, sig in enumerate(list(filtered_out)[:3]):
                print(f"  {i+1}. A={sig[0]:.2f}, B={sig[1]:.2f}, C={sig[2]:.2f}, D={sig[3]:.2f}")


if __name__ == "__main__":
    # Test the strict ABCD detection
    import sys
    from formed_and_unformed_patterns import detect_abcd_patterns_fast

    print("Loading test data...")

    # Load the CSV data
    df = pd.read_csv('btcusdt_1d.csv')
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)

    print(f"Loaded {len(df)} candles")

    # Detect pivot points (simplified version for testing)
    def find_pivot_points(data, window=5):
        """Find local highs and lows in the data"""
        extremum_points = []

        # Detect column names (case-insensitive)
        high_col = 'High' if 'High' in data.columns else 'high'
        low_col = 'Low' if 'Low' in data.columns else 'low'

        # Find local highs
        for i in range(window, len(data) - window):
            if data[high_col].iloc[i] == data[high_col].iloc[i-window:i+window+1].max():
                extremum_points.append((data.index[i], data[high_col].iloc[i], True))

        # Find local lows
        for i in range(window, len(data) - window):
            if data[low_col].iloc[i] == data[low_col].iloc[i-window:i+window+1].min():
                extremum_points.append((data.index[i], data[low_col].iloc[i], False))

        # Sort by timestamp
        extremum_points.sort(key=lambda x: x[0])
        return extremum_points

    extremum_points = find_pivot_points(df, window=5)
    print(f"Found {len(extremum_points)} extremum points")

    # Detect regular ABCD patterns
    print("\n" + "="*60)
    print("Detecting REGULAR ABCD patterns...")
    regular_patterns = detect_abcd_patterns_fast(extremum_points, log_details=True)

    # Detect strict ABCD patterns
    print("\n" + "="*60)
    print("Detecting STRICT ABCD patterns...")
    strict_patterns = detect_strict_abcd_patterns(extremum_points, df, log_details=True)

    # Compare results
    compare_patterns(regular_patterns, strict_patterns, log_details=True)

    # Show detailed comparison for first few patterns
    if strict_patterns:
        print("\n" + "="*60)
        print("DETAILED VIEW OF STRICT PATTERNS:")
        print("="*60)
        for i, pattern in enumerate(strict_patterns[:3]):
            print(f"\nPattern {i+1}: {pattern['name']}")
            print(f"  Type: {pattern['type']}")
            print(f"  A: {pattern['points']['A']['price']:.2f} at {pattern['points']['A']['time']}")
            print(f"  B: {pattern['points']['B']['price']:.2f} at {pattern['points']['B']['time']}")
            print(f"  C: {pattern['points']['C']['price']:.2f} at {pattern['points']['C']['time']}")
            print(f"  D: {pattern['points']['D']['price']:.2f} at {pattern['points']['D']['time']}")
            print(f"  BC Retracement: {pattern['ratios']['bc_retracement']:.1f}%")
            print(f"  CD Projection: {pattern['ratios']['cd_projection']:.1f}%")
            print(f"  Validation: {pattern['validation']}")