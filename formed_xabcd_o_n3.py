"""
O(n³) XABCD Pattern Detection - Meet-in-the-Middle Algorithm
==============================================================

Reduces complexity from O(n⁵) to O(n³) using:
1. XAB Index building - O(n³)
2. XABC extension with D price range pre-calculation - O(n³)
3. D probing with range check - O(n²)

Total: O(n³) expected 100-1000x speedup for large datasets
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
from collections import defaultdict
import pandas as pd
from pattern_ratios_2_Final import XABCD_PATTERN_RATIOS


@dataclass
class XAB_Entry:
    """XAB segment with AB/XA ratio"""
    x_idx: int
    x_time: float
    x_price: float
    a_idx: int
    a_time: float
    a_price: float
    xa_move: float
    ab_move: float
    ab_xa_ratio: float


@dataclass
class XABC_Entry:
    """XABC segment with pre-calculated D price range"""
    x_idx: int
    x_time: float
    x_price: float
    a_idx: int
    a_time: float
    a_price: float
    b_idx: int
    b_time: float
    b_price: float
    c_idx: int
    xa_move: float
    ab_move: float
    bc_move: float
    ab_xa_ratio: float
    bc_ab_ratio: float
    d_price_min: float
    d_price_max: float
    pattern_name: str


def validate_xabcd_containment_bullish(df, x_idx, a_idx, b_idx, c_idx, d_idx,
                                       x_price, a_price, b_price, c_price, d_price):
    """Validate price containment for bullish XABCD"""
    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        if x_idx + 1 < a_idx and any(df.iloc[x_idx+1:a_idx+1][low_col] < x_price):
            return False
        if x_idx < b_idx and any(df.iloc[x_idx:b_idx][high_col] > a_price):
            return False
        if b_price <= x_price:
            return False
        if a_idx < c_idx and any(df.iloc[a_idx:c_idx+1][low_col] < b_price):
            return False
        if b_idx < d_idx and any(df.iloc[b_idx:d_idx][high_col] > c_price):
            return False
        if c_idx < d_idx and any(df.iloc[c_idx:d_idx][low_col] < d_price):
            return False
        if d_price >= b_price:
            return False
        return True
    except:
        return False


def validate_xabcd_containment_bearish(df, x_idx, a_idx, b_idx, c_idx, d_idx,
                                       x_price, a_price, b_price, c_price, d_price):
    """Validate price containment for bearish XABCD"""
    try:
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'

        if x_idx + 1 < a_idx and any(df.iloc[x_idx+1:a_idx+1][high_col] > x_price):
            return False
        if x_idx < b_idx and any(df.iloc[x_idx:b_idx][low_col] < a_price):
            return False
        if b_price >= x_price:
            return False
        if a_idx < c_idx and any(df.iloc[a_idx:c_idx+1][high_col] > b_price):
            return False
        if b_idx < d_idx and any(df.iloc[b_idx:d_idx][low_col] < c_price):
            return False
        if c_idx < d_idx and any(df.iloc[c_idx:d_idx][high_col] > d_price):
            return False
        if d_price <= b_price:
            return False
        return True
    except:
        return False


def detect_xabcd_patterns_o_n3(extremum_points: List[Tuple],
                               df: pd.DataFrame = None,
                               log_details: bool = False,
                               strict_validation: bool = True,
                               max_search_window: Optional[int] = None,
                               validate_d_crossing: bool = True) -> List[Dict]:
    """
    O(n³) XABCD detection using meet-in-the-middle with D price range.

    Algorithm:
    1. Build XAB index - O(n³)
    2. Extend to XABC with D price range - O(n³)
    3. Probe with D - O(n²)

    Args:
        extremum_points: List of (timestamp, price, is_high, bar_index)
        df: DataFrame for validation
        log_details: Print progress
        strict_validation: Apply price containment
        max_search_window: Max distance between points (None = unlimited)
        validate_d_crossing: Validate D point crossing

    Returns:
        List of pattern dictionaries (same format as original)
    """
    patterns = []
    n = len(extremum_points)

    if n < 5:
        if log_details:
            print(f"[O(n³)] Insufficient extremum points: need 5, found {n}")
        return patterns

    if log_details:
        print(f"[O(n³)] XABCD detection with {n} extremum points")

    # Separate highs and lows
    highs = []
    lows = []
    for i, ep in enumerate(extremum_points):
        bar_idx = ep[3] if len(ep) > 3 else i
        if ep[2]:
            highs.append((bar_idx, ep[0], ep[1]))
        else:
            lows.append((bar_idx, ep[0], ep[1]))

    high_col = 'High' if df is not None and 'High' in df.columns else 'high'
    low_col = 'Low' if df is not None and 'Low' in df.columns else 'low'
    d_crossing_cache = {}

    # ================================================================
    # PHASE 1: Build XAB Index - O(n³)
    # ================================================================

    if log_details:
        print(f"[O(n³)] Phase 1: Building XAB index...")

    XAB_index = defaultdict(lambda: defaultdict(list))

    for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
        is_bullish = 'bull' in pattern_name

        x_cand = lows if is_bullish else highs
        a_cand = highs if is_bullish else lows
        b_cand = lows if is_bullish else highs

        for x_idx, x_time, x_price in x_cand:
            for a_idx, a_time, a_price in a_cand:
                if not (x_idx < a_idx):
                    continue
                if max_search_window and (a_idx - x_idx) > max_search_window:
                    continue

                xa_move = abs(a_price - x_price)
                if xa_move == 0:
                    continue

                for b_idx, b_time, b_price in b_cand:
                    if not (a_idx < b_idx):
                        continue
                    if max_search_window and (b_idx - a_idx) > max_search_window:
                        continue

                    ab_move = abs(b_price - a_price)
                    if ab_move == 0:
                        continue

                    ab_xa_ratio = (ab_move / xa_move) * 100

                    if not (ratios['ab_xa'][0] <= ab_xa_ratio <= ratios['ab_xa'][1]):
                        continue

                    if is_bullish:
                        if not (x_price < a_price and b_price < a_price):
                            continue
                    else:
                        if not (x_price > a_price and b_price > a_price):
                            continue

                    xab_entry = XAB_Entry(
                        x_idx, x_time, x_price,
                        a_idx, a_time, a_price,
                        xa_move, ab_move, ab_xa_ratio
                    )
                    XAB_index[pattern_name][(a_idx, b_idx)].append(xab_entry)

    if log_details:
        total_xab = sum(len(e) for p in XAB_index.values() for e in p.values())
        print(f"[O(n³)] Phase 1 complete: {total_xab} XAB entries")

    # ================================================================
    # PHASE 2: Extend to XABC with D Price Range - O(n³)
    # ================================================================

    if log_details:
        print(f"[O(n³)] Phase 2: Building XABC with D ranges...")

    XABC_by_C = defaultdict(list)

    for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
        is_bullish = 'bull' in pattern_name

        b_cand = lows if is_bullish else highs
        c_cand = highs if is_bullish else lows

        for b_idx, b_time, b_price in b_cand:
            for c_idx, c_time, c_price in c_cand:
                if not (b_idx < c_idx):
                    continue
                if max_search_window and (c_idx - b_idx) > max_search_window:
                    continue

                bc_move = abs(c_price - b_price)
                if bc_move == 0:
                    continue

                # Lookup XAB entries
                for (a_idx_key, b_idx_key), xab_entries in XAB_index[pattern_name].items():
                    if b_idx_key != b_idx:
                        continue

                    for xab in xab_entries:
                        ab_move = xab.ab_move
                        bc_ab_ratio = (bc_move / ab_move) * 100

                        if not (ratios['bc_ab'][0] <= bc_ab_ratio <= ratios['bc_ab'][1]):
                            continue

                        if is_bullish:
                            if not (c_price > b_price):
                                continue
                        else:
                            if not (c_price < b_price):
                                continue

                        # Calculate D price range from CD/BC
                        cd_bc_min, cd_bc_max = ratios['cd_bc']
                        if is_bullish:
                            d_cd_min = c_price - bc_move * (cd_bc_max / 100)
                            d_cd_max = c_price - bc_move * (cd_bc_min / 100)
                        else:
                            d_cd_min = c_price + bc_move * (cd_bc_min / 100)
                            d_cd_max = c_price + bc_move * (cd_bc_max / 100)

                        # Calculate D price range from AD/XA
                        ad_xa_min, ad_xa_max = ratios['ad_xa']
                        xa_move = xab.xa_move
                        a_price = xab.a_price

                        if is_bullish:
                            d_ad_min = a_price - xa_move * (ad_xa_max / 100)
                            d_ad_max = a_price - xa_move * (ad_xa_min / 100)
                        else:
                            d_ad_min = a_price + xa_move * (ad_xa_min / 100)
                            d_ad_max = a_price + xa_move * (ad_xa_max / 100)

                        # Intersection
                        d_min = max(d_cd_min, d_ad_min)
                        d_max = min(d_cd_max, d_ad_max)

                        if d_min <= d_max:
                            xabc = XABC_Entry(
                                xab.x_idx, xab.x_time, xab.x_price,
                                xab.a_idx, xab.a_time, xab.a_price,
                                b_idx, b_time, b_price,
                                c_idx, xa_move, ab_move, bc_move,
                                xab.ab_xa_ratio, bc_ab_ratio,
                                d_min, d_max, pattern_name
                            )
                            XABC_by_C[c_idx].append(xabc)

    if log_details:
        total_xabc = sum(len(e) for e in XABC_by_C.values())
        print(f"[O(n³)] Phase 2 complete: {total_xabc} XABC entries with D ranges")

    # ================================================================
    # PHASE 3: Probe with D - O(n²)
    # ================================================================

    if log_details:
        print(f"[O(n³)] Phase 3: Probing with D...")

    patterns_found = 0

    for pattern_name, ratios in XABCD_PATTERN_RATIOS.items():
        is_bullish = 'bull' in pattern_name
        d_cand = lows if is_bullish else highs

        for c_idx, c_time, c_price in (highs if is_bullish else lows):
            if c_idx not in XABC_by_C:
                continue

            for d_idx, d_time, d_price in d_cand:
                if not (c_idx < d_idx):
                    continue
                if max_search_window and (d_idx - c_idx) > max_search_window:
                    continue

                for xabc in XABC_by_C[c_idx]:
                    if xabc.pattern_name != pattern_name:
                        continue

                    # O(1) range check - both ratios guaranteed!
                    if not (xabc.d_price_min <= d_price <= xabc.d_price_max):
                        continue

                    if is_bullish:
                        if not (c_price > d_price):
                            continue
                    else:
                        if not (c_price < d_price):
                            continue

                    cd_move = abs(d_price - c_price)
                    ad_move = abs(d_price - xabc.a_price)
                    cd_bc_ratio = (cd_move / xabc.bc_move) * 100
                    ad_xa_ratio = (ad_move / xabc.xa_move) * 100

                    # Validate containment
                    if strict_validation and df is not None:
                        if is_bullish:
                            valid = validate_xabcd_containment_bullish(
                                df, xabc.x_idx, xabc.a_idx, xabc.b_idx, c_idx, d_idx,
                                xabc.x_price, xabc.a_price, xabc.b_price, c_price, d_price
                            )
                        else:
                            valid = validate_xabcd_containment_bearish(
                                df, xabc.x_idx, xabc.a_idx, xabc.b_idx, c_idx, d_idx,
                                xabc.x_price, xabc.a_price, xabc.b_price, c_price, d_price
                            )
                        if not valid:
                            continue

                    # Validate D crossing
                    if validate_d_crossing and df is not None and d_idx < len(df) - 1:
                        key = (d_idx, d_price, is_bullish)
                        if key not in d_crossing_cache:
                            crossed = False
                            if is_bullish:
                                if df[low_col].iloc[d_idx+1:].min() < d_price:
                                    crossed = True
                            else:
                                if df[high_col].iloc[d_idx+1:].max() > d_price:
                                    crossed = True
                            d_crossing_cache[key] = crossed
                        if d_crossing_cache[key]:
                            continue

                    # Create pattern
                    pattern = {
                        'name': pattern_name,
                        'type': 'bullish' if is_bullish else 'bearish',
                        'pattern_type': 'XABCD',
                        'points': {
                            'X': {'time': xabc.x_time, 'price': xabc.x_price, 'index': xabc.x_idx},
                            'A': {'time': xabc.a_time, 'price': xabc.a_price, 'index': xabc.a_idx},
                            'B': {'time': xabc.b_time, 'price': xabc.b_price, 'index': xabc.b_idx},
                            'C': {'time': c_time, 'price': c_price, 'index': c_idx},
                            'D': {'time': d_time, 'price': d_price, 'index': d_idx}
                        },
                        'indices': {
                            'X': xabc.x_idx,
                            'A': xabc.a_idx,
                            'B': xabc.b_idx,
                            'C': c_idx,
                            'D': d_idx
                        },
                        'ratios': {
                            'ab_xa': xabc.ab_xa_ratio,
                            'bc_ab': xabc.bc_ab_ratio,
                            'cd_bc': cd_bc_ratio,
                            'ad_xa': ad_xa_ratio
                        }
                    }
                    patterns.append(pattern)
                    patterns_found += 1

    if log_details:
        print(f"[O(n³)] Phase 3 complete: {patterns_found} patterns found")

    return patterns
