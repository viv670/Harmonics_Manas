"""
Extended Test Suite for O(n³) XABCD Pattern Detection
=======================================================

Additional tests with different configurations:
- Different symbols (ETH, XLM)
- Different validation settings
- Edge cases
"""

import pandas as pd
import time
from extremum import detect_extremum_points
from formed_xabcd import detect_xabcd_patterns
from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3


def load_csv(file_path):
    """Load and normalize CSV columns"""
    df = pd.read_csv(file_path)
    if 'Time' not in df.columns and 'time' in df.columns:
        df['Time'] = df['time']
    if 'High' not in df.columns and 'high' in df.columns:
        df['High'] = df['high']
    if 'Low' not in df.columns and 'low' in df.columns:
        df['Low'] = df['low']
    if 'Close' not in df.columns and 'close' in df.columns:
        df['Close'] = df['close']
    return df


def validate_patterns(orig, opt, test_name):
    """Validate pattern match between implementations"""
    print(f"\n--- Validation: {test_name} ---")

    if len(orig) != len(opt):
        print(f"❌ Count mismatch: {len(orig)} vs {len(opt)}")
        return False

    print(f"✅ Count match: {len(orig)} patterns")

    if len(orig) == 0:
        return True

    # Check indices match
    def get_key(p):
        idx = p['indices']
        return (idx['X'], idx['A'], idx['B'], idx['C'], idx['D'])

    orig_keys = sorted([get_key(p) for p in orig])
    opt_keys = sorted([get_key(p) for p in opt])

    if orig_keys != opt_keys:
        print(f"❌ Indices mismatch!")
        print(f"   Original: {orig_keys[:3]}...")
        print(f"   Optimized: {opt_keys[:3]}...")
        return False

    print(f"✅ All indices match!")

    # Check pattern names
    orig_names = sorted([p['name'] for p in orig])
    opt_names = sorted([p['name'] for p in opt])

    if orig_names != opt_names:
        print(f"❌ Pattern names mismatch!")
        return False

    print(f"✅ All pattern names match!")

    # Sample ratio validation
    orig_sorted = sorted(orig, key=get_key)
    opt_sorted = sorted(opt, key=get_key)

    ratio_errors = 0
    for o, p in zip(orig_sorted, opt_sorted):
        for ratio_name in ['ab_xa', 'bc_ab', 'cd_bc', 'ad_xa']:
            diff = abs(o['ratios'][ratio_name] - p['ratios'][ratio_name])
            if diff > 0.01:
                ratio_errors += 1
                if ratio_errors <= 3:  # Show first 3 errors
                    print(f"⚠️  Ratio {ratio_name} diff: {diff:.3f}%")

    if ratio_errors > 0:
        print(f"❌ {ratio_errors} ratio mismatches!")
        return False

    print(f"✅ All ratios match!")
    return True


def run_test(name, df, extremum_len, **params):
    """Run single test configuration"""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"{'='*80}")
    print(f"Data: {len(df)} rows")
    print(f"Extremum length: {extremum_len}")
    print(f"Strict validation: {params.get('strict_validation', True)}")
    print(f"D-crossing: {params.get('validate_d_crossing', True)}")
    print(f"Window: {params.get('max_search_window', 'Unlimited')}")

    # Detect extremum
    extremum = detect_extremum_points(df, length=extremum_len)
    print(f"\nExtremum points: {len(extremum)}")

    if len(extremum) < 5:
        print("❌ Insufficient extremum points")
        return False, 0, 0

    test_params = {'df': df, 'log_details': False, **params}

    # Original
    print("\nRunning ORIGINAL...")
    start = time.time()
    orig = detect_xabcd_patterns(extremum, **test_params)
    orig_time = time.time() - start
    print(f"   {len(orig)} patterns in {orig_time:.3f}s")

    # Optimized
    print("Running OPTIMIZED...")
    start = time.time()
    opt = detect_xabcd_patterns_o_n3(extremum, **test_params)
    opt_time = time.time() - start
    print(f"   {len(opt)} patterns in {opt_time:.3f}s")

    # Validate
    match = validate_patterns(orig, opt, name)

    # Performance
    print(f"\nPerformance:")
    print(f"   Original:  {orig_time:.3f}s")
    print(f"   Optimized: {opt_time:.3f}s")
    if opt_time > 0:
        speedup = orig_time / opt_time
        print(f"   Speedup:   {speedup:.2f}x {'🚀' if speedup > 1 else ''}")

    return match, orig_time, opt_time


def main():
    print("\n" + "="*80)
    print("EXTENDED O(n³) XABCD TEST SUITE")
    print("="*80)

    results = []

    # Test 1: ETHUSDT 1D, L=4
    print("\n### TEST 1: ETHUSDT 1D, L=4 ###")
    try:
        df = load_csv('data/ethusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "ETHUSDT 1D, L=4, Full validation",
            df, extremum_len=4,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("ETHUSDT 1D, L=4", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("ETHUSDT 1D, L=4", False, 0, 0))

    # Test 2: ETHUSDT 1D, L=3
    print("\n\n### TEST 2: ETHUSDT 1D, L=3 ###")
    try:
        df = load_csv('data/ethusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "ETHUSDT 1D, L=3, Full validation",
            df, extremum_len=3,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("ETHUSDT 1D, L=3", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("ETHUSDT 1D, L=3", False, 0, 0))

    # Test 3: BTCUSDT 1D, L=4, No D-crossing
    print("\n\n### TEST 3: BTCUSDT 1D, L=4, No D-crossing ###")
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "BTCUSDT 1D, L=4, D-crossing OFF",
            df, extremum_len=4,
            strict_validation=True,
            validate_d_crossing=False,
            max_search_window=None
        )
        results.append(("BTCUSDT 1D, L=4, No D-cross", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("BTCUSDT 1D, L=4, No D-cross", False, 0, 0))

    # Test 4: BTCUSDT 1D, L=3, No strict validation
    print("\n\n### TEST 4: BTCUSDT 1D, L=3, No strict validation ###")
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "BTCUSDT 1D, L=3, Strict OFF",
            df, extremum_len=3,
            strict_validation=False,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("BTCUSDT 1D, L=3, Strict OFF", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("BTCUSDT 1D, L=3, Strict OFF", False, 0, 0))

    # Test 5: BTCUSDT 1D, L=3, Window=30
    print("\n\n### TEST 5: BTCUSDT 1D, L=3, Window=30 ###")
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "BTCUSDT 1D, L=3, Window=30",
            df, extremum_len=3,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=30
        )
        results.append(("BTCUSDT 1D, L=3, Window=30", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("BTCUSDT 1D, L=3, Window=30", False, 0, 0))

    # Test 6: XLMUSDT 1D, L=3
    print("\n\n### TEST 6: XLMUSDT 1D, L=3 ###")
    try:
        df = load_csv('data/xlmusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "XLMUSDT 1D, L=3, Full validation",
            df, extremum_len=3,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("XLMUSDT 1D, L=3", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("XLMUSDT 1D, L=3", False, 0, 0))

    # Test 7: BTCUSDT 1D, L=2 (larger extremum set)
    print("\n\n### TEST 7: BTCUSDT 1D, L=2 (Larger set) ###")
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "BTCUSDT 1D, L=2, Full validation",
            df, extremum_len=2,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("BTCUSDT 1D, L=2", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("BTCUSDT 1D, L=2", False, 0, 0))

    # Final Summary
    print("\n\n" + "="*80)
    print("EXTENDED TEST SUMMARY")
    print("="*80)

    passed = 0
    failed = 0
    total_orig_time = 0
    total_opt_time = 0

    for i, (name, match, orig_t, opt_t) in enumerate(results, 1):
        status = "✅ PASS" if match else "❌ FAIL"
        speedup = orig_t / opt_t if opt_t > 0 else 0

        print(f"\n{i}. {name}")
        print(f"   Status:    {status}")
        print(f"   Original:  {orig_t:.3f}s")
        print(f"   Optimized: {opt_t:.3f}s")
        if speedup > 0:
            print(f"   Speedup:   {speedup:.2f}x")

        if match:
            passed += 1
            total_orig_time += orig_t
            total_opt_time += opt_t
        else:
            failed += 1

    # Overall stats
    print("\n" + "="*80)
    print(f"OVERALL RESULTS: {passed} passed, {failed} failed")

    if total_opt_time > 0:
        avg_speedup = total_orig_time / total_opt_time
        print(f"Total time - Original: {total_orig_time:.3f}s")
        print(f"Total time - Optimized: {total_opt_time:.3f}s")
        print(f"Average speedup: {avg_speedup:.2f}x")

    if passed == len(results):
        print("\n🎉 ALL EXTENDED TESTS PASSED!")
        print("O(n³) implementation validated across multiple configurations!")
    else:
        print(f"\n⚠️  {failed} test(s) failed")

    print("="*80)

    return passed == len(results)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
