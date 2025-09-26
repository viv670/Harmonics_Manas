"""
Comprehensive ABCD Pattern Detection System
Combines both formed and unformed ABCD patterns with strict validation

This module provides:
1. Formed ABCD patterns (complete 4-point patterns with strict price containment)
2. Unformed ABCD patterns (3-point patterns with projected D points)
3. Optimized performance with O(n?) complexity
4. Strict price validation to ensure clean pattern formation
5. PRZ (Potential Reversal Zone) calculation for unformed patterns
"""

from typing import List, Tuple, Dict, Set, Optional
import pandas as pd
import numpy as np
import threading
from pattern_ratios_2_Final import ABCD_PATTERN_RATIOS

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
    Works for both formed (with D) and unformed (without D) patterns.

    Bullish: A(High) -> B(Low) -> C(High) -> D(Low)

    Rules:
    1. A->B: No candle between A and B has a high that exceeds A
    2. B->C: No candle between A and C has a low that breaks B
    3. C->D (if D exists): No candle between B and D has a high that exceeds C
    """
    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Check A to B: no high exceeds A
        if a_idx < b_idx:
            segment_ab = df.iloc[a_idx:b_idx+1]
            if any(segment_ab[high_col] > a_price):
                return False

        # Check A to C: no low breaks B
        if a_idx < c_idx:
            segment_ac = df.iloc[a_idx:c_idx+1]
            if any(segment_ac[low_col] < b_price):
                return False

        # Check B to C: no high exceeds C (C must be the highest from B to C)
        if b_idx < c_idx:
            segment_bc = df.iloc[b_idx:c_idx+1]
            if any(segment_bc[high_col] > c_price):
                return False

        # For unformed patterns: Check after C - no high should exceed C
        if d_idx is None:
            # Check candles after C (limited to MAX_FUTURE_CANDLES for performance)
            if c_idx < len(df) - 1:
                end_idx = min(c_idx + 1 + MAX_FUTURE_CANDLES, len(df))
                segment_after_c = df.iloc[c_idx+1:end_idx]
                if any(segment_after_c[high_col] > c_price):
                    return False

        # If D exists, validate additional segments
        if d_idx is not None and d_price is not None:
            # Check B to D: no high exceeds C
            if b_idx < d_idx:
                segment_bd = df.iloc[b_idx:d_idx+1]
                if any(segment_bd[high_col] > c_price):
                    return False

            # Check C to D: no low breaks D
            if c_idx < d_idx:
                segment_cd = df.iloc[c_idx:d_idx+1]
                if any(segment_cd[low_col] < d_price):
                    return False

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.debug(f"Validation error in validate_price_containment_bullish: {e}")
        return False


def validate_price_containment_bearish(df: pd.DataFrame,
                                      a_idx: int, b_idx: int,
                                      c_idx: int, d_idx: Optional[int],
                                      a_price: float, b_price: float,
                                      c_price: float, d_price: Optional[float] = None) -> bool:
    """
    Validate price containment for bearish patterns.
    Works for both formed (with D) and unformed (without D) patterns.

    Bearish: A(Low) -> B(High) -> C(Low) -> D(High)

    Rules:
    1. A->B: No candle between A and B has a low that breaks A
    2. B->C: No candle between A and C has a high that exceeds B
    3. C->D (if D exists): No candle between B and D has a low that breaks C
    """
    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Check A to B: no low breaks A
        if a_idx < b_idx:
            segment_ab = df.iloc[a_idx:b_idx+1]
            if any(segment_ab[low_col] < a_price):
                return False

        # Check A to C: no high exceeds B
        if a_idx < c_idx:
            segment_ac = df.iloc[a_idx:c_idx+1]
            if any(segment_ac[high_col] > b_price):
                return False

        # Check B to C: no low breaks C (C must be the lowest from B to C)
        if b_idx < c_idx:
            segment_bc = df.iloc[b_idx:c_idx+1]
            if any(segment_bc[low_col] < c_price):
                return False

        # For unformed patterns: Check after C - no low should break below C
        if d_idx is None:
            # Check candles after C (limited to MAX_FUTURE_CANDLES for performance)
            if c_idx < len(df) - 1:
                end_idx = min(c_idx + 1 + MAX_FUTURE_CANDLES, len(df))
                segment_after_c = df.iloc[c_idx+1:end_idx]
                if any(segment_after_c[low_col] < c_price):
                    return False

        # If D exists, validate additional segments
        if d_idx is not None and d_price is not None:
            # Check B to D: no low breaks C
            if b_idx < d_idx:
                segment_bd = df.iloc[b_idx:d_idx+1]
                if any(segment_bd[low_col] < c_price):
                    return False

            # Check C to D: no high exceeds D
            if c_idx < d_idx:
                segment_cd = df.iloc[c_idx:d_idx+1]
                if any(segment_cd[high_col] > d_price):
                    return False

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.debug(f"Validation error in validate_price_containment_bullish: {e}")
        return False


def find_candle_index(df: pd.DataFrame, timestamp, time_tolerance=pd.Timedelta(minutes=1)):
    """Helper function to find candle index in DataFrame

    Can handle both integer indices and timestamps.
    If timestamp is already an integer index, returns it directly.
    Otherwise, converts timestamp to index.
    """
    # If timestamp is already an integer index, return it directly
    if isinstance(timestamp, (int, np.integer)):
        # Validate it's within bounds
        if 0 <= timestamp < len(df):
            return timestamp
        return None

    # Otherwise, handle as timestamp
    if 'timestamp' not in df.columns:
        df_copy = df.copy()
        if isinstance(df.index, pd.DatetimeIndex):
            df_copy['timestamp'] = df.index
        elif 'Date' in df.columns:
            df_copy['timestamp'] = pd.to_datetime(df['Date'])
        elif 'Datetime' in df.columns:
            df_copy['timestamp'] = pd.to_datetime(df['Datetime'])
        else:
            return None
    else:
        df_copy = df

    try:
        time_diff = abs(df_copy['timestamp'] - pd.to_datetime(timestamp))
        if time_diff.min() <= time_tolerance:
            return time_diff.idxmin()
    except:
        return None
    return None


def detect_strict_abcd_patterns(extremum_points: List[Tuple],
                               df: pd.DataFrame,
                               log_details: bool = False,
                               max_patterns: int = 50,
                               max_search_window: int = 20) -> List[Dict]:
    """
    Detect complete ABCD patterns (4-point patterns) with strict validation.

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
        df: DataFrame with OHLC data for validation
        log_details: Whether to print detailed logs
        max_patterns: Maximum number of patterns to return
        max_search_window: Maximum distance between pattern points

    Returns:
        List of dictionaries containing formed ABCD patterns
    """
    patterns = []
    n = len(extremum_points)

    if n < 4:
        if log_details:
            print(f"Not enough extremum points for formed ABCD: {n} < 4")
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

    if log_details:
        print(f"\nDetecting Strict ABCD patterns with {n} extremum points")
        print(f"DataFrame has {len(df_copy)} candles for validation")
        print(f"Max patterns limit: {max_patterns}")
        print(f"Search window: {max_search_window}")

    # Separate highs and lows
    highs = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if ep[2]]
    lows = [(i, ep[0], ep[1]) for i, ep in enumerate(extremum_points) if not ep[2]]

    patterns_found = 0
    patterns_checked = 0
    patterns_rejected = 0

    for pattern_name, ratio_range in ABCD_PATTERN_RATIOS.items():
        if patterns_found >= max_patterns:
            break

        is_bullish = 'bull' in pattern_name

        # Select appropriate candidates
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

        # Search for valid patterns
        for i, (a_idx, a_time, a_price) in enumerate(a_candidates):
            if patterns_found >= max_patterns:
                break

            # Find valid B points
            valid_b = [b for b in b_candidates
                      if a_idx < b[0] <= min(a_idx + max_search_window, n-1)]

            for b_idx, b_time, b_price in valid_b:
                if patterns_found >= max_patterns:
                    break

                ab_move = abs(b_price - a_price)
                if ab_move == 0:
                    continue

                # Find valid C points
                valid_c = [c for c in c_candidates
                          if b_idx < c[0] <= min(b_idx + max_search_window, n-1)]

                for c_idx, c_time, c_price in valid_c:
                    if patterns_found >= max_patterns:
                        break

                    # Calculate BC retracement
                    bc_move = abs(c_price - b_price)
                    bc_retracement = (bc_move / ab_move) * 100

                    # Check if BC retracement is within range
                    if not (ratio_range['retr'][0] <= bc_retracement <= ratio_range['retr'][1]):
                        continue

                    # Find valid D points
                    valid_d = [d for d in d_candidates
                              if c_idx < d[0] <= min(c_idx + max_search_window, n-1)]

                    for d_idx, d_time, d_price in valid_d:
                        if patterns_found >= max_patterns:
                            break

                        patterns_checked += 1

                        # Log progress
                        if patterns_checked % 1000 == 0 and log_details:
                            print(f"  Checked {patterns_checked} combinations, found {patterns_found} valid patterns")

                        # Calculate CD projection with epsilon protection
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
                            # Find candle indices
                            a_candle_idx = find_candle_index(df_copy, a_time)
                            b_candle_idx = find_candle_index(df_copy, b_time)
                            c_candle_idx = find_candle_index(df_copy, c_time)
                            d_candle_idx = find_candle_index(df_copy, d_time)

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

                        # Pattern is valid!
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
                                  f"BC={bc_retracement:.1f}%, CD={cd_projection:.1f}%")

    if log_details:
        print(f"\nStrict ABCD Detection Summary:")
        print(f"  Checked: {patterns_checked} pattern combinations")
        print(f"  Found: {patterns_found} patterns with strict validation")
        print(f"  Rejected: {patterns_rejected} patterns due to price violations")

    return patterns


def detect_unformed_abcd_patterns_optimized(extremum_points: List[Tuple],
                                           df: Optional[pd.DataFrame] = None,
                                           log_details: bool = False,
                                           max_patterns: int = None,
                                           max_search_window: int = None,
                                           strict_validation: bool = False) -> List[Dict]:
    """
    Detect unformed ABCD patterns (3-point patterns with projected D).

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
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

    # NO LIMITS - Always search entire dataset for 100% certainty
    search_window_j = n  # Check ALL possible j points
    search_window_k = n  # Check ALL possible k points

    # Prepare DataFrame for validation if needed
    df_copy = None
    if strict_validation and df is not None and not df.empty:
        df_copy = df.copy()
        if 'timestamp' not in df_copy.columns:
            if isinstance(df_copy.index, pd.DatetimeIndex):
                df_copy.reset_index(inplace=True)
                df_copy['timestamp'] = pd.to_datetime(df_copy.iloc[:, 0])
            elif 'Date' in df_copy.columns:
                df_copy['timestamp'] = pd.to_datetime(df_copy['Date'])

    if log_details:
        print(f"\nDetecting Unformed ABCD patterns with {n} extremum points")
        print(f"Search window: J={search_window_j}, K={search_window_k}")
        print(f"Strict validation: {strict_validation}")

    patterns_checked = 0
    patterns_rejected = 0

    # Process ALL points - NO LIMITS
    for i in range(n - 3, -1, -1):
        # NO pattern limit check - process everything

        for j in range(i + 1, n - 1):  # Check ALL j points
            # NO pattern limit check - process everything

            for k in range(j + 1, n):  # Check ALL k points
                # NO pattern limit check - process everything

                A, B, C = extremum_points[i], extremum_points[j], extremum_points[k]

                # Check alternating pattern
                if not _is_valid_abc_pattern(A, B, C):
                    continue

                # Avoid duplicate processing
                signature = (i, j, k)
                if signature in processed_combinations:
                    continue
                processed_combinations.add(signature)

                patterns_checked += 1

                # Apply strict validation if enabled
                validation_type = "basic"
                if strict_validation and df_copy is not None:
                    try:
                        # Find candle indices
                        a_candle_idx = find_candle_index(df_copy, A[0])
                        b_candle_idx = find_candle_index(df_copy, B[0])
                        c_candle_idx = find_candle_index(df_copy, C[0])

                        if None not in [a_candle_idx, b_candle_idx, c_candle_idx]:
                            is_bullish = A[2]  # A is high for bullish

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
                                continue

                            validation_type = "strict"
                    except Exception:
                        pass

                # Process the valid ABC combination
                pattern_data = _process_abc_combination_optimized(A, B, C, signature, validation_type)
                if pattern_data:
                    patterns.append(pattern_data)

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
                                 backtest_mode: bool = False) -> List[Dict]:
    """
    Detect ALL unformed ABCD patterns - NO LIMITS, 100% CERTAINTY
    """
    # ALWAYS detect ALL patterns - NO LIMITS, NO COMPROMISES
    return detect_unformed_abcd_patterns_optimized(
        extremum_points,
        df=df,  # Pass the DataFrame for validation
        log_details=log_details,
        max_patterns=None,  # NO LIMIT - detect ALL patterns
        max_search_window=None,  # NO LIMIT - search entire history
        strict_validation=True  # ENABLE strict price containment validation
    )


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


def _process_abc_combination_optimized(A: Tuple, B: Tuple, C: Tuple, signature: Tuple, validation_type: str = "basic") -> Optional[Dict]:
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
    suffix = "_strict" if validation_type == "strict" else ""

    return {
        'name': f"{base_name}_unformed{suffix}",
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
            'A': signature[0],
            'B': signature[1],
            'C': signature[2]
        },
        'quality_score': len(matching_pattern_names),
        'validation': validation_type
    }


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

    print("\n" + "="*60)
    print("COMPREHENSIVE ABCD PATTERN DETECTION")
    print("="*60)

    # Detect strict formed patterns
    print("\nDetecting Strict ABCD Patterns...")
    strict_patterns = detect_strict_abcd_patterns(
        extremum_points, df, log_details=True, max_patterns=20
    )

    # Detect unformed patterns with strict validation
    print("\nDetecting Unformed ABCD Patterns with Strict Validation...")
    unformed_strict = detect_unformed_abcd_patterns_optimized(
        extremum_points, df, log_details=True, max_patterns=20, strict_validation=True
    )

    # Detect unformed patterns without strict validation
    print("\nDetecting Unformed ABCD Patterns (Basic)...")
    unformed_basic = detect_unformed_abcd_patterns(extremum_points, log_details=True)

    print("\n" + "="*60)
    print("DETECTION SUMMARY")
    print("="*60)
    print(f"Strict Formed Patterns: {len(strict_patterns)}")
    print(f"Unformed Patterns (Strict): {len(unformed_strict)}")
    print(f"Unformed Patterns (Basic): {len(unformed_basic)}")

    # Show example patterns
    if strict_patterns:
        print("\n" + "="*60)
        print("EXAMPLE STRICT FORMED PATTERN")
        print("="*60)
        p = strict_patterns[0]
        print(f"Name: {p['name']}")
        print(f"Type: {p['type']}")
        print(f"BC Retracement: {p['ratios']['bc_retracement']:.1f}%")
        print(f"CD Projection: {p['ratios']['cd_projection']:.1f}%")

    if unformed_strict:
        print("\n" + "="*60)
        print("EXAMPLE UNFORMED PATTERN (STRICT)")
        print("="*60)
        p = unformed_strict[0]
        print(f"Name: {p['name']}")
        print(f"Type: {p['type']}")
        print(f"BC Retracement: {p['ratios']['bc_retracement']:.1f}%")
        print(f"Matching Patterns: {', '.join(p['ratios']['matching_patterns'][:3])}")
        print(f"PRZ Zones: {len(p['ratios']['prz_zones'])}")