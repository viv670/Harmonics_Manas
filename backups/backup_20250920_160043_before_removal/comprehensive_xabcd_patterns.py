"""
Comprehensive XABCD Pattern Detection System
Detects strict unformed XABCD patterns with comprehensive price containment validation

This module provides:
1. Unformed XABCD patterns (4-point patterns X-A-B-C with projected D)
2. Strict price containment validation between all segments
3. Horizontal line calculation for projected D points (not PRZ zones)
4. Optimized performance with pattern lookup
5. Validation that price doesn't violate C after formation
"""

from typing import List, Tuple, Dict, Set, Optional
import pandas as pd
import numpy as np
import threading
from pattern_ratios_2_Final import XABCD_PATTERN_RATIOS

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
    Validate price containment for bullish XABCD patterns.

    Bullish: X(Low) -> A(High) -> B(Low) -> C(High)

    Rules:
    1. X→A: No low breaks X
    2. X→B: No high exceeds A
    3. A→C: No low breaks B (B must be lowest from A to C)
    4. B→C: No high exceeds C (C must be highest from B to C)
    5. After C: No high exceeds C (for unformed patterns)
    """
    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Check X to A: no low breaks X
        if x_idx < a_idx:
            segment_xa = df.iloc[x_idx:a_idx+1]
            if any(segment_xa[low_col] < x_price):
                return False

        # Check X to B: no high exceeds A
        if x_idx < b_idx:
            segment_xb = df.iloc[x_idx:b_idx+1]
            if any(segment_xb[high_col] > a_price):
                return False

        # Check A to C: no low breaks B (B must be lowest from A to C)
        if a_idx < c_idx:
            segment_ac = df.iloc[a_idx:c_idx+1]
            if any(segment_ac[low_col] < b_price):
                return False

        # Check B to C: no high exceeds C (C must be highest from B to C)
        if b_idx < c_idx:
            segment_bc = df.iloc[b_idx:c_idx+1]
            if any(segment_bc[high_col] > c_price):
                return False

        # For unformed patterns: Check after C - no high should exceed C
        if c_idx < len(df) - 1:
            end_idx = min(c_idx + 1 + MAX_FUTURE_CANDLES, len(df))
            segment_after_c = df.iloc[c_idx+1:end_idx]
            if any(segment_after_c[high_col] > c_price):
                return False

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.debug(f"Validation error in validate_price_containment_bullish_xabcd: {e}")
        return False


def validate_price_containment_bearish_xabcd(df: pd.DataFrame,
                                           x_idx: int, a_idx: int, b_idx: int, c_idx: int,
                                           x_price: float, a_price: float,
                                           b_price: float, c_price: float) -> bool:
    """
    Validate price containment for bearish XABCD patterns.

    Bearish: X(High) -> A(Low) -> B(High) -> C(Low)

    Rules:
    1. X→A: No high exceeds X
    2. X→B: No low breaks A
    3. A→C: No high exceeds B (B must be highest from A to C)
    4. B→C: No low breaks C (C must be lowest from B to C)
    5. After C: No low breaks below C (for unformed patterns)
    """
    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        # Check X to A: no high exceeds X
        if x_idx < a_idx:
            segment_xa = df.iloc[x_idx:a_idx+1]
            if any(segment_xa[high_col] > x_price):
                return False

        # Check X to B: no low breaks A
        if x_idx < b_idx:
            segment_xb = df.iloc[x_idx:b_idx+1]
            if any(segment_xb[low_col] < a_price):
                return False

        # Check A to C: no high exceeds B (B must be highest from A to C)
        if a_idx < c_idx:
            segment_ac = df.iloc[a_idx:c_idx+1]
            if any(segment_ac[high_col] > b_price):
                return False

        # Check B to C: no low breaks C (C must be lowest from B to C)
        if b_idx < c_idx:
            segment_bc = df.iloc[b_idx:c_idx+1]
            if any(segment_bc[low_col] < c_price):
                return False

        # For unformed patterns: Check after C - no low should break below C
        if c_idx < len(df) - 1:
            end_idx = min(c_idx + 1 + MAX_FUTURE_CANDLES, len(df))
            segment_after_c = df.iloc[c_idx+1:end_idx]
            if any(segment_after_c[low_col] < c_price):
                return False

        return True

    except (KeyError, IndexError, TypeError, AttributeError) as e:
        import logging
        logging.debug(f"Validation error in validate_price_containment_bearish_xabcd: {e}")
        return False


def find_candle_index_xabcd(df: pd.DataFrame, timestamp, time_tolerance=pd.Timedelta(minutes=1)):
    """Helper function to find candle index in DataFrame"""
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

    time_diff = abs(df_copy['timestamp'] - pd.to_datetime(timestamp))
    if time_diff.min() <= time_tolerance:
        return time_diff.idxmin()
    return None


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
        # More specific error handling
        import logging
        logging.warning(f"Error in validate_d_lines_no_candlestick_crossing: {e}")
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
                                         max_patterns: int = 50,
                                         max_search_window: int = 30) -> List[Dict]:
    """
    Detect strict unformed XABCD patterns (4-point patterns X-A-B-C with projected D).

    Args:
        extremum_points: List of tuples (timestamp, price, is_high)
        df: DataFrame with OHLC data for validation
        log_details: Whether to print detailed logs
        max_patterns: Maximum number of patterns to return
        max_search_window: Maximum distance between pattern points

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

    if log_details:
        print(f"\nDetecting Strict Unformed XABCD patterns with {n} extremum points")
        print(f"DataFrame has {len(df_copy)} candles for validation")
        print(f"Max patterns limit: {max_patterns}")
        print(f"Search window: {max_search_window}")

    patterns_found = 0
    patterns_checked = 0
    patterns_rejected = 0

    # Process points in reverse chronological order for recent patterns
    for i in range(n - 4, -1, -1):
        if patterns_found >= max_patterns:
            break

        for j in range(i + 1, min(i + max_search_window, n - 2)):
            if patterns_found >= max_patterns:
                break

            for k in range(j + 1, min(j + max_search_window, n - 1)):
                if patterns_found >= max_patterns:
                    break

                for l in range(k + 1, min(k + max_search_window, n)):
                    if patterns_found >= max_patterns:
                        break

                    X, A, B, C = extremum_points[i], extremum_points[j], extremum_points[k], extremum_points[l]

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

                    if not matching_patterns_data:
                        continue

                    # Apply strict validation
                    try:
                        # Find candle indices
                        x_candle_idx = find_candle_index_xabcd(df_copy, X[0])
                        a_candle_idx = find_candle_index_xabcd(df_copy, A[0])
                        b_candle_idx = find_candle_index_xabcd(df_copy, B[0])
                        c_candle_idx = find_candle_index_xabcd(df_copy, C[0])

                        if None in [x_candle_idx, a_candle_idx, b_candle_idx, c_candle_idx]:
                            patterns_rejected += 1
                            continue

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
                            continue

                    except Exception:
                        patterns_rejected += 1
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

                    # Create pattern object
                    pattern = {
                        'name': f"{first_pattern['name']}_unformed_strict",
                        'type': 'bullish' if is_bullish else 'bearish',
                        'formation': 'unformed',
                        'points': {
                            'X': {'time': X[0], 'price': x_price},
                            'A': {'time': A[0], 'price': a_price},
                            'B': {'time': B[0], 'price': b_price},
                            'C': {'time': C[0], 'price': c_price},
                            'D_projected': {'d_lines': d_lines}
                        },
                        'ratios': {
                            'ab_xa_retracement': ab_xa_retracement,
                            'bc_ab_projection': bc_ab_projection,
                            'matching_patterns': [p['name'] for p in matching_patterns_data]
                        },
                        'indices': {
                            'X': i,
                            'A': j,
                            'B': k,
                            'C': l
                        },
                        'validation': 'strict_containment'
                    }

                    patterns.append(pattern)
                    patterns_found += 1

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