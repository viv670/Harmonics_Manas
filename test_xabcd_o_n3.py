"""
Test Suite for O(n³) XABCD Pattern Detection
=============================================

Compares original detect_xabcd_patterns() vs optimized detect_xabcd_patterns_o_n3()

Tests:
1. Correctness - exact pattern matching
2. Performance - time comparison
3. Multiple configurations with varying parameters
"""

import pandas as pd
import time
from typing import List, Dict, Tuple
from extremum import detect_extremum_points
from formed_xabcd import detect_xabcd_patterns
from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3


def load_test_data(symbol: str, timeframe: str) -> pd.DataFrame:
    """Load CSV data for testing"""
    file_paths = {
        'BTCUSDT_1D': 'btcusdt_1d.csv',
        'BTCUSDT_1D_data': 'data/btcusdt_1d.csv',
        'ETHUSDT_1D': 'data/ethusdt_1d.csv',
    }

    key = f"{symbol}_{timeframe}"
    if key not in file_paths:
        key = f"{symbol}_{timeframe}_data"

    df = pd.read_csv(file_paths.get(key, file_paths['BTCUSDT_1D']))

    # Ensure required columns
    if 'Time' not in df.columns and 'time' in df.columns:
        df['Time'] = df['time']
    if 'Open' not in df.columns and 'open' in df.columns:
        df['Open'] = df['open']
    if 'High' not in df.columns and 'high' in df.columns:
        df['High'] = df['high']
    if 'Low' not in df.columns and 'low' in df.columns:
        df['Low'] = df['low']
    if 'Close' not in df.columns and 'close' in df.columns:
        df['Close'] = df['close']

    return df


def compare_patterns(original: List[Dict], optimized: List[Dict], config_name: str) -> bool:
    """Compare two pattern lists for exact match"""

    print(f"\n{'='*80}")
    print(f"Configuration: {config_name}")
    print(f"{'='*80}")

    if len(original) != len(optimized):
        print(f"❌ PATTERN COUNT MISMATCH!")
        print(f"   Original: {len(original)} patterns")
        print(f"   Optimized: {len(optimized)} patterns")
        return False

    print(f"✅ Pattern count matches: {len(original)} patterns")

    if len(original) == 0:
        print("   (No patterns found in either implementation)")
        return True

    # Sort both lists by pattern structure for comparison
    def pattern_key(p):
        indices = p['indices']
        return (indices['X'], indices['A'], indices['B'], indices['C'], indices['D'])

    original_sorted = sorted(original, key=pattern_key)
    optimized_sorted = sorted(optimized, key=pattern_key)

    all_match = True

    for i, (orig, opt) in enumerate(zip(original_sorted, optimized_sorted)):
        # Compare pattern name
        if orig['name'] != opt['name']:
            print(f"❌ Pattern {i+1}: Name mismatch")
            print(f"   Original: {orig['name']}")
            print(f"   Optimized: {opt['name']}")
            all_match = False
            continue

        # Compare indices
        orig_idx = orig['indices']
        opt_idx = opt['indices']

        if orig_idx != opt_idx:
            print(f"❌ Pattern {i+1}: Index mismatch for {orig['name']}")
            print(f"   Original: X={orig_idx['X']}, A={orig_idx['A']}, B={orig_idx['B']}, C={orig_idx['C']}, D={orig_idx['D']}")
            print(f"   Optimized: X={opt_idx['X']}, A={opt_idx['A']}, B={opt_idx['B']}, C={opt_idx['C']}, D={opt_idx['D']}")
            all_match = False
            continue

        # Compare prices (with small tolerance for floating point)
        orig_points = orig['points']
        opt_points = opt['points']

        price_match = True
        for point in ['X', 'A', 'B', 'C', 'D']:
            orig_price = orig_points[point]['price']
            opt_price = opt_points[point]['price']
            if abs(orig_price - opt_price) > 1e-6:
                print(f"❌ Pattern {i+1}: Price mismatch at {point}")
                print(f"   Original: {orig_price}")
                print(f"   Optimized: {opt_price}")
                price_match = False

        if not price_match:
            all_match = False
            continue

        # Compare ratios (with tolerance)
        orig_ratios = orig['ratios']
        opt_ratios = opt['ratios']

        ratio_match = True
        for ratio_name in ['ab_xa', 'bc_ab', 'cd_bc', 'ad_xa']:
            orig_ratio = orig_ratios[ratio_name]
            opt_ratio = opt_ratios[ratio_name]
            if abs(orig_ratio - opt_ratio) > 0.01:  # 0.01% tolerance
                print(f"❌ Pattern {i+1}: Ratio mismatch for {ratio_name}")
                print(f"   Original: {orig_ratio:.2f}%")
                print(f"   Optimized: {opt_ratio:.2f}%")
                ratio_match = False

        if not ratio_match:
            all_match = False
            continue

    if all_match:
        print(f"✅ ALL {len(original)} PATTERNS MATCH EXACTLY!")
        print(f"   - Pattern names match")
        print(f"   - X, A, B, C, D indices match")
        print(f"   - Prices match")
        print(f"   - AB/XA, BC/AB, CD/BC, AD/XA ratios match")
    else:
        print(f"❌ SOME PATTERNS DON'T MATCH")

    return all_match


def run_test_config(config: Dict) -> Tuple[bool, float, float]:
    """Run a single test configuration"""

    print(f"\n{'='*80}")
    print(f"Loading data: {config['symbol']} {config['timeframe']}")
    print(f"{'='*80}")

    df = load_test_data(config['symbol'], config['timeframe'])
    print(f"DataFrame loaded: {len(df)} rows")

    # Detect extremum points
    print(f"\nDetecting extremum points (length={config['extremum_length']})...")
    extremum_points = detect_extremum_points(
        df,
        length=config['extremum_length']
    )
    print(f"Found {len(extremum_points)} extremum points")

    if len(extremum_points) < 5:
        print(f"❌ Insufficient extremum points for XABCD (need 5, found {len(extremum_points)})")
        return False, 0.0, 0.0

    # Test parameters
    test_params = {
        'df': df,
        'log_details': config.get('log_details', False),
        'strict_validation': config.get('strict_validation', True),
        'max_search_window': config.get('max_search_window', None),
        'validate_d_crossing': config.get('validate_d_crossing', True)
    }

    # Run original implementation
    print(f"\n{'='*80}")
    print(f"Running ORIGINAL implementation...")
    print(f"{'='*80}")

    start_time = time.time()
    original_patterns = detect_xabcd_patterns(extremum_points, **test_params)
    original_time = time.time() - start_time

    print(f"✅ Original complete: {len(original_patterns)} patterns in {original_time:.3f}s")

    # Run optimized implementation
    print(f"\n{'='*80}")
    print(f"Running OPTIMIZED O(n³) implementation...")
    print(f"{'='*80}")

    start_time = time.time()
    optimized_patterns = detect_xabcd_patterns_o_n3(extremum_points, **test_params)
    optimized_time = time.time() - start_time

    print(f"✅ Optimized complete: {len(optimized_patterns)} patterns in {optimized_time:.3f}s")

    # Compare results
    match = compare_patterns(original_patterns, optimized_patterns, config['name'])

    # Performance summary
    print(f"\n{'='*80}")
    print(f"Performance Summary")
    print(f"{'='*80}")
    print(f"Original time:  {original_time:.3f}s")
    print(f"Optimized time: {optimized_time:.3f}s")

    if optimized_time > 0:
        speedup = original_time / optimized_time
        print(f"Speedup: {speedup:.2f}x {'🚀' if speedup > 1 else '⚠️'}")
    else:
        print(f"Speedup: N/A (optimized too fast to measure)")

    return match, original_time, optimized_time


def main():
    """Run all test configurations"""

    print("\n" + "="*80)
    print("XABCD O(n³) OPTIMIZATION TEST SUITE")
    print("="*80)
    print("Testing: formed_xabcd_o_n3.py vs formed_xabcd.py")
    print("="*80)

    # Test configurations - using unlimited window as specified
    configs = [
        {
            'name': 'Config 1: BTCUSDT 1D, L=1, D-Crossing ON',
            'symbol': 'BTCUSDT',
            'timeframe': '1D',
            'extremum_length': 1,
            'strict_validation': True,
            'max_search_window': None,  # Unlimited
            'validate_d_crossing': True,
            'log_details': False
        },
        {
            'name': 'Config 2: BTCUSDT 1D, L=2, D-Crossing OFF',
            'symbol': 'BTCUSDT',
            'timeframe': '1D',
            'extremum_length': 2,
            'strict_validation': True,
            'max_search_window': None,  # Unlimited
            'validate_d_crossing': False,
            'log_details': False
        },
        {
            'name': 'Config 3: ETHUSDT 1D, L=1, D-Crossing ON',
            'symbol': 'ETHUSDT',
            'timeframe': '1D',
            'extremum_length': 1,
            'strict_validation': True,
            'max_search_window': None,  # Unlimited
            'validate_d_crossing': True,
            'log_details': False
        },
        {
            'name': 'Config 4: BTCUSDT 1D, L=3, Strict OFF',
            'symbol': 'BTCUSDT',
            'timeframe': '1D',
            'extremum_length': 3,
            'strict_validation': False,
            'max_search_window': None,  # Unlimited
            'validate_d_crossing': True,
            'log_details': False
        }
    ]

    # Run all tests
    results = []

    for config in configs:
        match, orig_time, opt_time = run_test_config(config)
        results.append({
            'config': config['name'],
            'match': match,
            'original_time': orig_time,
            'optimized_time': opt_time
        })

    # Final summary
    print("\n" + "="*80)
    print("FINAL TEST SUMMARY")
    print("="*80)

    all_passed = True

    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result['match'] else "❌ FAIL"
        print(f"\n{i}. {result['config']}")
        print(f"   Status: {status}")
        print(f"   Original: {result['original_time']:.3f}s")
        print(f"   Optimized: {result['optimized_time']:.3f}s")

        if result['optimized_time'] > 0:
            speedup = result['original_time'] / result['optimized_time']
            print(f"   Speedup: {speedup:.2f}x")

        if not result['match']:
            all_passed = False

    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED! O(n³) implementation is correct!")
    else:
        print("❌ SOME TESTS FAILED - Review differences above")
    print("="*80)

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
