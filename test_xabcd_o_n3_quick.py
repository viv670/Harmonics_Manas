"""
Quick Test for O(n³) XABCD Pattern Detection
==============================================

Starts with smaller, faster configurations
"""

import pandas as pd
import time
from typing import List, Dict, Tuple
from extremum import detect_extremum_points
from formed_xabcd import detect_xabcd_patterns
from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3


def load_test_data(file_path: str) -> pd.DataFrame:
    """Load CSV data for testing"""
    df = pd.read_csv(file_path)

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


def compare_patterns(original: List[Dict], optimized: List[Dict]) -> bool:
    """Compare two pattern lists for exact match"""

    if len(original) != len(optimized):
        print(f"❌ PATTERN COUNT MISMATCH!")
        print(f"   Original: {len(original)} patterns")
        print(f"   Optimized: {len(optimized)} patterns")
        return False

    print(f"✅ Pattern count matches: {len(original)} patterns")

    if len(original) == 0:
        print("   (No patterns found)")
        return True

    # Sort both lists by indices
    def pattern_key(p):
        indices = p['indices']
        return (indices['X'], indices['A'], indices['B'], indices['C'], indices['D'])

    original_sorted = sorted(original, key=pattern_key)
    optimized_sorted = sorted(optimized, key=pattern_key)

    mismatches = 0

    for i, (orig, opt) in enumerate(zip(original_sorted, optimized_sorted)):
        # Compare name
        if orig['name'] != opt['name']:
            print(f"❌ Pattern {i+1}: Name mismatch ({orig['name']} vs {opt['name']})")
            mismatches += 1
            continue

        # Compare indices
        if orig['indices'] != opt['indices']:
            print(f"❌ Pattern {i+1}: Index mismatch")
            print(f"   Original: {orig['indices']}")
            print(f"   Optimized: {opt['indices']}")
            mismatches += 1
            continue

        # Compare ratios (with small tolerance)
        orig_ratios = orig['ratios']
        opt_ratios = opt['ratios']

        ratio_ok = True
        for ratio_name in ['ab_xa', 'bc_ab', 'cd_bc', 'ad_xa']:
            if abs(orig_ratios[ratio_name] - opt_ratios[ratio_name]) > 0.01:
                print(f"❌ Pattern {i+1}: Ratio {ratio_name} mismatch")
                print(f"   Original: {orig_ratios[ratio_name]:.2f}%")
                print(f"   Optimized: {opt_ratios[ratio_name]:.2f}%")
                ratio_ok = False

        if not ratio_ok:
            mismatches += 1

    if mismatches == 0:
        print(f"✅ ALL {len(original)} PATTERNS MATCH EXACTLY!")
        return True
    else:
        print(f"❌ {mismatches} PATTERNS DON'T MATCH")
        return False


def run_single_test(config_name: str, df: pd.DataFrame, extremum_length: int,
                    validate_d_crossing: bool = True, strict_validation: bool = True):
    """Run a single test configuration"""

    print(f"\n{'='*80}")
    print(f"{config_name}")
    print(f"{'='*80}")
    print(f"DataFrame: {len(df)} rows")
    print(f"Extremum length: {extremum_length}")
    print(f"D-crossing validation: {validate_d_crossing}")
    print(f"Strict validation: {strict_validation}")

    # Detect extremum points
    print(f"\nDetecting extremum points...")
    extremum_points = detect_extremum_points(df, length=extremum_length)
    print(f"Found {len(extremum_points)} extremum points")

    if len(extremum_points) < 5:
        print(f"❌ Insufficient extremum points (need 5)")
        return False, 0.0, 0.0

    test_params = {
        'df': df,
        'log_details': True,
        'strict_validation': strict_validation,
        'max_search_window': None,
        'validate_d_crossing': validate_d_crossing
    }

    # Run original
    print(f"\n--- Running ORIGINAL O(n⁵) implementation ---")
    start = time.time()
    original_patterns = detect_xabcd_patterns(extremum_points, **test_params)
    original_time = time.time() - start
    print(f"✅ Original: {len(original_patterns)} patterns in {original_time:.3f}s")

    # Run optimized
    print(f"\n--- Running OPTIMIZED O(n³) implementation ---")
    start = time.time()
    optimized_patterns = detect_xabcd_patterns_o_n3(extremum_points, **test_params)
    optimized_time = time.time() - start
    print(f"✅ Optimized: {len(optimized_patterns)} patterns in {optimized_time:.3f}s")

    # Compare
    print(f"\n--- Comparing Results ---")
    match = compare_patterns(original_patterns, optimized_patterns)

    # Performance
    print(f"\n--- Performance Summary ---")
    print(f"Original:  {original_time:.3f}s")
    print(f"Optimized: {optimized_time:.3f}s")
    if optimized_time > 0:
        speedup = original_time / optimized_time
        print(f"Speedup:   {speedup:.2f}x {'🚀' if speedup > 1 else ''}")

    return match, original_time, optimized_time


def main():
    """Run progressive tests from easiest to hardest"""

    print("\n" + "="*80)
    print("XABCD O(n³) OPTIMIZATION - QUICK TEST")
    print("="*80)

    results = []

    # Test 1: BTCUSDT 1D with L=3 (smallest extremum set)
    print("\n\n### TEST 1: BTCUSDT 1D, L=3 (Fast) ###")
    df = load_test_data('btcusdt_1d.csv')
    match, orig_time, opt_time = run_single_test(
        "Config 1: BTCUSDT 1D, L=3",
        df, extremum_length=3,
        validate_d_crossing=True,
        strict_validation=True
    )
    results.append(('Config 1: BTCUSDT 1D, L=3', match, orig_time, opt_time))

    # Test 2: BTCUSDT 1D with L=2 (medium)
    print("\n\n### TEST 2: BTCUSDT 1D, L=2 (Medium) ###")
    match, orig_time, opt_time = run_single_test(
        "Config 2: BTCUSDT 1D, L=2",
        df, extremum_length=2,
        validate_d_crossing=False,
        strict_validation=True
    )
    results.append(('Config 2: BTCUSDT 1D, L=2', match, orig_time, opt_time))

    # Test 3: ETHUSDT 1D with L=2
    print("\n\n### TEST 3: ETHUSDT 1D, L=2 (Medium) ###")
    df_eth = load_test_data('data/ethusdt_1d.csv')
    match, orig_time, opt_time = run_single_test(
        "Config 3: ETHUSDT 1D, L=2",
        df_eth, extremum_length=2,
        validate_d_crossing=True,
        strict_validation=True
    )
    results.append(('Config 3: ETHUSDT 1D, L=2', match, orig_time, opt_time))

    # Only run L=1 if previous tests passed and were reasonably fast
    if all(r[1] for r in results) and max(r[2] for r in results) < 30:
        print("\n\n### TEST 4: BTCUSDT 1D, L=1 (SLOW - Large extremum set) ###")
        print("⚠️  Warning: This may take several minutes with O(n⁵)...")
        match, orig_time, opt_time = run_single_test(
            "Config 4: BTCUSDT 1D, L=1 (FULL TEST)",
            df, extremum_length=1,
            validate_d_crossing=True,
            strict_validation=True
        )
        results.append(('Config 4: BTCUSDT 1D, L=1', match, orig_time, opt_time))
    else:
        print("\n\n### TEST 4: SKIPPED (Previous tests too slow or failed) ###")

    # Final summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)

    all_passed = True
    for i, (name, match, orig_time, opt_time) in enumerate(results, 1):
        status = "✅ PASS" if match else "❌ FAIL"
        speedup = orig_time / opt_time if opt_time > 0 else 0
        print(f"\n{i}. {name}")
        print(f"   Status:    {status}")
        print(f"   Original:  {orig_time:.3f}s")
        print(f"   Optimized: {opt_time:.3f}s")
        print(f"   Speedup:   {speedup:.2f}x")

        if not match:
            all_passed = False

    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("O(n³) implementation matches original exactly!")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*80)

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
