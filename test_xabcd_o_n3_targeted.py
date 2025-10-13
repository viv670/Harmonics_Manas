"""
Targeted Test Suite for O(n³) XABCD Pattern Detection
=======================================================

Focused tests on manageable sizes (L=3 and L=4 only)
Multiple symbols and configurations
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
    """Validate pattern match"""
    print(f"\n--- Validation ---")

    if len(orig) != len(opt):
        print(f"❌ Count: {len(orig)} vs {len(opt)}")
        return False

    print(f"✅ Count: {len(orig)} patterns")

    if len(orig) == 0:
        return True

    # Check indices
    def get_key(p):
        idx = p['indices']
        return (idx['X'], idx['A'], idx['B'], idx['C'], idx['D'])

    orig_keys = set([get_key(p) for p in orig])
    opt_keys = set([get_key(p) for p in opt])

    if orig_keys != opt_keys:
        print(f"❌ Indices mismatch!")
        missing = orig_keys - opt_keys
        extra = opt_keys - orig_keys
        if missing:
            print(f"   Missing in optimized: {list(missing)[:2]}")
        if extra:
            print(f"   Extra in optimized: {list(extra)[:2]}")
        return False

    print(f"✅ All indices match!")
    return True


def run_test(name, df, extremum_len, timeout_estimate, **params):
    """Run single test with timeout estimate"""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print(f"{'='*80}")
    print(f"Data: {len(df)} rows, L={extremum_len}")
    print(f"Settings: strict={params.get('strict_validation', True)}, "
          f"d_cross={params.get('validate_d_crossing', True)}, "
          f"window={params.get('max_search_window', 'unlimited')}")
    print(f"Estimated time: {timeout_estimate}s")

    # Detect extremum
    extremum = detect_extremum_points(df, length=extremum_len)
    print(f"Extremum: {len(extremum)} points")

    if len(extremum) < 5:
        print("❌ Insufficient extremum points")
        return False, 0, 0

    test_params = {'df': df, 'log_details': False, **params}

    # Original
    print("\nOriginal...", end='', flush=True)
    start = time.time()
    orig = detect_xabcd_patterns(extremum, **test_params)
    orig_time = time.time() - start
    print(f" {len(orig)} patterns in {orig_time:.3f}s")

    # Optimized
    print("Optimized...", end='', flush=True)
    start = time.time()
    opt = detect_xabcd_patterns_o_n3(extremum, **test_params)
    opt_time = time.time() - start
    print(f" {len(opt)} patterns in {opt_time:.3f}s")

    # Validate
    match = validate_patterns(orig, opt, name)

    # Performance
    speedup = orig_time / opt_time if opt_time > 0 else 0
    print(f"\n{'✅' if match else '❌'} {name}")
    print(f"   Original: {orig_time:.3f}s | Optimized: {opt_time:.3f}s | Speedup: {speedup:.2f}x")

    return match, orig_time, opt_time


def main():
    print("\n" + "="*80)
    print("TARGETED O(n³) XABCD TEST SUITE")
    print("="*80)
    print("Testing L=3 and L=4 across multiple symbols and configurations")
    print("="*80)

    results = []

    # Test 1: BTCUSDT 1D, L=4
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "BTCUSDT 1D, L=4, Full",
            df, extremum_len=4, timeout_estimate=5,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("BTCUSDT 1D, L=4, Full", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("BTCUSDT 1D, L=4, Full", False, 0, 0))

    # Test 2: BTCUSDT 1D, L=3
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "BTCUSDT 1D, L=3, Full",
            df, extremum_len=3, timeout_estimate=20,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("BTCUSDT 1D, L=3, Full", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("BTCUSDT 1D, L=3, Full", False, 0, 0))

    # Test 3: ETHUSDT 1D, L=4
    try:
        df = load_csv('data/ethusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "ETHUSDT 1D, L=4, Full",
            df, extremum_len=4, timeout_estimate=5,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("ETHUSDT 1D, L=4, Full", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("ETHUSDT 1D, L=4, Full", False, 0, 0))

    # Test 4: ETHUSDT 1D, L=3
    try:
        df = load_csv('data/ethusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "ETHUSDT 1D, L=3, Full",
            df, extremum_len=3, timeout_estimate=20,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("ETHUSDT 1D, L=3, Full", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("ETHUSDT 1D, L=3, Full", False, 0, 0))

    # Test 5: BTCUSDT 1D, L=4, No D-crossing
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "BTCUSDT 1D, L=4, No D-cross",
            df, extremum_len=4, timeout_estimate=5,
            strict_validation=True,
            validate_d_crossing=False,
            max_search_window=None
        )
        results.append(("BTCUSDT 1D, L=4, No D-cross", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("BTCUSDT 1D, L=4, No D-cross", False, 0, 0))

    # Test 6: BTCUSDT 1D, L=3, No Strict
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "BTCUSDT 1D, L=3, No Strict",
            df, extremum_len=3, timeout_estimate=20,
            strict_validation=False,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("BTCUSDT 1D, L=3, No Strict", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("BTCUSDT 1D, L=3, No Strict", False, 0, 0))

    # Test 7: BTCUSDT 1D, L=3, Window=30
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "BTCUSDT 1D, L=3, Window=30",
            df, extremum_len=3, timeout_estimate=15,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=30
        )
        results.append(("BTCUSDT 1D, L=3, Window=30", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("BTCUSDT 1D, L=3, Window=30", False, 0, 0))

    # Test 8: XLMUSDT 1D, L=3
    try:
        df = load_csv('data/xlmusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "XLMUSDT 1D, L=3, Full",
            df, extremum_len=3, timeout_estimate=20,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        results.append(("XLMUSDT 1D, L=3, Full", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")
        results.append(("XLMUSDT 1D, L=3, Full", False, 0, 0))

    # Summary
    print("\n\n" + "="*80)
    print("TARGETED TEST SUMMARY")
    print("="*80)

    passed = sum(1 for _, match, _, _ in results if match)
    failed = len(results) - passed
    total_orig = sum(orig_t for _, _, orig_t, _ in results)
    total_opt = sum(opt_t for _, _, _, opt_t in results)

    print(f"\nResults: {passed}/{len(results)} passed, {failed} failed\n")

    for i, (name, match, orig_t, opt_t) in enumerate(results, 1):
        status = "✅" if match else "❌"
        speedup = f"{orig_t/opt_t:.2f}x" if opt_t > 0 else "N/A"
        print(f"{i}. {status} {name}")
        print(f"   {orig_t:.3f}s → {opt_t:.3f}s (speedup: {speedup})")

    if total_opt > 0:
        avg_speedup = total_orig / total_opt
        print(f"\n{'='*80}")
        print(f"Total time - Original: {total_orig:.3f}s")
        print(f"Total time - Optimized: {total_opt:.3f}s")
        print(f"Overall speedup: {avg_speedup:.2f}x")

    print("\n" + "="*80)
    if passed == len(results):
        print("🎉 ALL TESTS PASSED!")
        print("O(n³) validated across symbols and configurations!")
    else:
        print(f"⚠️  {failed} test(s) failed")
    print("="*80)

    return passed == len(results)


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
