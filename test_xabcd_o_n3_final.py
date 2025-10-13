"""
Final Quick Test for O(n³) XABCD - Reasonable Dataset Sizes Only
==================================================================

Only test on manageable extremum counts (< 100 points)
"""

import pandas as pd
import time
from extremum import detect_extremum_points
from formed_xabcd import detect_xabcd_patterns
from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3


def load_csv(file_path):
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


def run_test(name, df, extremum_len, **params):
    print(f"\n{'='*70}")
    print(f"{name}")
    print(f"{'='*70}")

    # Detect extremum
    extremum = detect_extremum_points(df, length=extremum_len)
    print(f"Extremum: {len(extremum)} points (L={extremum_len})")

    if len(extremum) < 5:
        print("❌ Insufficient points")
        return False, 0, 0

    if len(extremum) > 100:
        print(f"⚠️  Skipping - too many points ({len(extremum)} > 100)")
        return None, 0, 0

    test_params = {'df': df, 'log_details': False, **params}

    # Original
    print("Original...", end='', flush=True)
    start = time.time()
    orig = detect_xabcd_patterns(extremum, **test_params)
    orig_t = time.time() - start
    print(f" {len(orig)} patterns, {orig_t:.3f}s")

    # Optimized
    print("Optimized...", end='', flush=True)
    start = time.time()
    opt = detect_xabcd_patterns_o_n3(extremum, **test_params)
    opt_t = time.time() - start
    print(f" {len(opt)} patterns, {opt_t:.3f}s")

    # Validate
    if len(orig) != len(opt):
        print(f"❌ MISMATCH: {len(orig)} vs {len(opt)}")
        return False, orig_t, opt_t

    # Check indices
    if len(orig) > 0:
        get_key = lambda p: (p['indices']['X'], p['indices']['A'],
                            p['indices']['B'], p['indices']['C'], p['indices']['D'])
        orig_keys = set(get_key(p) for p in orig)
        opt_keys = set(get_key(p) for p in opt)

        if orig_keys != opt_keys:
            print(f"❌ Indices mismatch!")
            return False, orig_t, opt_t

    speedup = orig_t / opt_t if opt_t > 0 else 0
    print(f"✅ PASS - Speedup: {speedup:.2f}x")

    return True, orig_t, opt_t


def main():
    print("\n" + "="*70)
    print("FINAL O(n³) XABCD TEST - Reasonable Sizes Only")
    print("="*70)

    results = []

    # Test 1: BTCUSDT 1D, L=4 (54 points)
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "1. BTCUSDT 1D, L=4",
            df, extremum_len=4,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        if match is not None:
            results.append(("BTCUSDT 1D L=4", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 2: BTCUSDT 1D, L=3 (72 points)
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "2. BTCUSDT 1D, L=3",
            df, extremum_len=3,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        if match is not None:
            results.append(("BTCUSDT 1D L=3", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 3: BTCUSDT 1D, L=5 (smaller)
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "3. BTCUSDT 1D, L=5",
            df, extremum_len=5,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        if match is not None:
            results.append(("BTCUSDT 1D L=5", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 4: BTCUSDT 1D, L=4, No D-crossing
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "4. BTCUSDT 1D, L=4, No D-crossing",
            df, extremum_len=4,
            strict_validation=True,
            validate_d_crossing=False,
            max_search_window=None
        )
        if match is not None:
            results.append(("BTCUSDT L=4 No-D", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 5: BTCUSDT 1D, L=3, No strict
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "5. BTCUSDT 1D, L=3, No strict validation",
            df, extremum_len=3,
            strict_validation=False,
            validate_d_crossing=True,
            max_search_window=None
        )
        if match is not None:
            results.append(("BTCUSDT L=3 No-strict", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 6: BTCUSDT 1D, L=3, Window=30
    try:
        df = load_csv('btcusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "6. BTCUSDT 1D, L=3, Window=30",
            df, extremum_len=3,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=30
        )
        if match is not None:
            results.append(("BTCUSDT L=3 W=30", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 7: XLMUSDT 1D, L=4 (check if reasonable size)
    try:
        df = load_csv('data/xlmusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "7. XLMUSDT 1D, L=4",
            df, extremum_len=4,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        if match is not None:
            results.append(("XLMUSDT 1D L=4", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")

    # Test 8: XLMUSDT 1D, L=3 (check if reasonable size)
    try:
        df = load_csv('data/xlmusdt_1d.csv')
        match, orig_t, opt_t = run_test(
            "8. XLMUSDT 1D, L=3",
            df, extremum_len=3,
            strict_validation=True,
            validate_d_crossing=True,
            max_search_window=None
        )
        if match is not None:
            results.append(("XLMUSDT 1D L=3", match, orig_t, opt_t))
    except Exception as e:
        print(f"❌ Error: {e}")

    # Summary
    print("\n\n" + "="*70)
    print("FINAL TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, match, _, _ in results if match)
    total_orig = sum(orig_t for _, _, orig_t, _ in results)
    total_opt = sum(opt_t for _, _, _, opt_t in results)

    print(f"\nTests run: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {len(results) - passed}\n")

    for i, (name, match, orig_t, opt_t) in enumerate(results, 1):
        status = "✅" if match else "❌"
        speedup = f"{orig_t/opt_t:.2f}x" if opt_t > 0 else "N/A"
        print(f"{i}. {status} {name:<25} {orig_t:6.3f}s → {opt_t:6.3f}s ({speedup})")

    if total_opt > 0:
        avg_speedup = total_orig / total_opt
        print(f"\n{'='*70}")
        print(f"Total Original:  {total_orig:6.3f}s")
        print(f"Total Optimized: {total_opt:6.3f}s")
        print(f"Overall Speedup: {avg_speedup:.2f}x")

    print("\n" + "="*70)
    if passed == len(results) and len(results) > 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {len(results) - passed} test(s) failed")
    print("="*70)

    return passed == len(results) and len(results) > 0


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
