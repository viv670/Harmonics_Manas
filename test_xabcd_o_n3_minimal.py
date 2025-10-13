"""
Minimal Test for O(n³) XABCD Pattern Detection
================================================

Tests with very small dataset first to verify correctness quickly
"""

import pandas as pd
import time
from extremum import detect_extremum_points
from formed_xabcd import detect_xabcd_patterns
from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3


def test_minimal():
    """Test with smallest possible dataset"""

    print("="*80)
    print("MINIMAL XABCD O(n³) TEST")
    print("="*80)

    # Load data and take only last 100 rows for speed
    print("\n1. Loading minimal dataset...")
    df = pd.read_csv('btcusdt_1d.csv')
    df = df.tail(100).reset_index(drop=True)  # Only last 100 rows
    print(f"   Dataset: {len(df)} rows")

    # Detect extremum with L=5 (very small extremum set)
    print("\n2. Detecting extremum points (L=5)...")
    extremum_points = detect_extremum_points(df, length=5)
    print(f"   Found: {len(extremum_points)} extremum points")

    if len(extremum_points) < 5:
        print(f"   ❌ Not enough extremum points (need 5)")
        return False

    # Test parameters - simplest case
    test_params = {
        'df': df,
        'log_details': False,  # Disable logging for cleaner output
        'strict_validation': False,  # Disable strict validation for speed
        'max_search_window': 20,  # Small window for speed
        'validate_d_crossing': False  # Disable D-crossing for speed
    }

    # Run original
    print("\n3. Running ORIGINAL implementation...")
    start = time.time()
    original = detect_xabcd_patterns(extremum_points, **test_params)
    orig_time = time.time() - start
    print(f"   Found: {len(original)} patterns in {orig_time:.3f}s")

    # Run optimized
    print("\n4. Running OPTIMIZED O(n³) implementation...")
    start = time.time()
    optimized = detect_xabcd_patterns_o_n3(extremum_points, **test_params)
    opt_time = time.time() - start
    print(f"   Found: {len(optimized)} patterns in {opt_time:.3f}s")

    # Compare counts
    print("\n5. Comparing results...")
    if len(original) != len(optimized):
        print(f"   ❌ Pattern count mismatch!")
        print(f"      Original: {len(original)}")
        print(f"      Optimized: {len(optimized)}")
        return False

    print(f"   ✅ Pattern count matches: {len(original)} patterns")

    if len(original) == 0:
        print(f"   (No patterns found - this is OK for minimal test)")
        return True

    # Compare first few patterns in detail
    def pattern_key(p):
        return (p['indices']['X'], p['indices']['A'], p['indices']['B'],
                p['indices']['C'], p['indices']['D'])

    orig_sorted = sorted(original, key=pattern_key)
    opt_sorted = sorted(optimized, key=pattern_key)

    mismatches = 0
    for i, (o, p) in enumerate(zip(orig_sorted[:5], opt_sorted[:5])):  # Check first 5
        if o['name'] != p['name'] or o['indices'] != p['indices']:
            print(f"   ❌ Pattern {i+1} mismatch:")
            print(f"      Original: {o['name']} @ {o['indices']}")
            print(f"      Optimized: {p['name']} @ {p['indices']}")
            mismatches += 1

    if mismatches == 0:
        print(f"   ✅ All patterns match!")
    else:
        print(f"   ❌ {mismatches} patterns don't match")
        return False

    # Performance
    print("\n6. Performance:")
    print(f"   Original:  {orig_time:.3f}s")
    print(f"   Optimized: {opt_time:.3f}s")
    if opt_time > 0:
        speedup = orig_time / opt_time
        print(f"   Speedup:   {speedup:.2f}x")

    print("\n" + "="*80)
    print("✅ MINIMAL TEST PASSED!")
    print("="*80)
    return True


def test_small():
    """Test with small extremum set (L=4)"""

    print("\n\n" + "="*80)
    print("SMALL XABCD O(n³) TEST")
    print("="*80)

    # Load full dataset
    print("\n1. Loading dataset...")
    df = pd.read_csv('btcusdt_1d.csv')
    print(f"   Dataset: {len(df)} rows")

    # Detect extremum with L=4
    print("\n2. Detecting extremum points (L=4)...")
    extremum_points = detect_extremum_points(df, length=4)
    print(f"   Found: {len(extremum_points)} extremum points")

    # Test parameters
    test_params = {
        'df': df,
        'log_details': False,
        'strict_validation': True,
        'max_search_window': None,  # Unlimited
        'validate_d_crossing': True
    }

    # Run original
    print("\n3. Running ORIGINAL implementation...")
    start = time.time()
    original = detect_xabcd_patterns(extremum_points, **test_params)
    orig_time = time.time() - start
    print(f"   Found: {len(original)} patterns in {orig_time:.3f}s")

    # Run optimized
    print("\n4. Running OPTIMIZED O(n³) implementation...")
    start = time.time()
    optimized = detect_xabcd_patterns_o_n3(extremum_points, **test_params)
    opt_time = time.time() - start
    print(f"   Found: {len(optimized)} patterns in {opt_time:.3f}s")

    # Compare
    print("\n5. Comparing results...")
    if len(original) != len(optimized):
        print(f"   ❌ Pattern count mismatch: {len(original)} vs {len(optimized)}")
        return False

    print(f"   ✅ Pattern count matches: {len(original)} patterns")

    if len(original) > 0:
        # Quick validation of indices
        def pattern_key(p):
            return (p['indices']['X'], p['indices']['A'], p['indices']['B'],
                    p['indices']['C'], p['indices']['D'])

        orig_keys = {pattern_key(p) for p in original}
        opt_keys = {pattern_key(p) for p in optimized}

        if orig_keys == opt_keys:
            print(f"   ✅ All pattern indices match!")
        else:
            print(f"   ❌ Pattern indices don't match")
            print(f"      Missing in optimized: {orig_keys - opt_keys}")
            print(f"      Extra in optimized: {opt_keys - orig_keys}")
            return False

    # Performance
    print("\n6. Performance:")
    print(f"   Original:  {orig_time:.3f}s")
    print(f"   Optimized: {opt_time:.3f}s")
    if opt_time > 0:
        speedup = orig_time / opt_time
        print(f"   Speedup:   {speedup:.2f}x")

    print("\n" + "="*80)
    print("✅ SMALL TEST PASSED!")
    print("="*80)
    return True


def test_medium():
    """Test with medium extremum set (L=3)"""

    print("\n\n" + "="*80)
    print("MEDIUM XABCD O(n³) TEST")
    print("="*80)

    print("\n1. Loading dataset...")
    df = pd.read_csv('btcusdt_1d.csv')
    print(f"   Dataset: {len(df)} rows")

    print("\n2. Detecting extremum points (L=3)...")
    extremum_points = detect_extremum_points(df, length=3)
    print(f"   Found: {len(extremum_points)} extremum points")

    test_params = {
        'df': df,
        'log_details': False,
        'strict_validation': True,
        'max_search_window': None,
        'validate_d_crossing': True
    }

    print("\n3. Running ORIGINAL implementation...")
    print("   (This may take 30-60 seconds...)")
    start = time.time()
    original = detect_xabcd_patterns(extremum_points, **test_params)
    orig_time = time.time() - start
    print(f"   Found: {len(original)} patterns in {orig_time:.3f}s")

    print("\n4. Running OPTIMIZED O(n³) implementation...")
    start = time.time()
    optimized = detect_xabcd_patterns_o_n3(extremum_points, **test_params)
    opt_time = time.time() - start
    print(f"   Found: {len(optimized)} patterns in {opt_time:.3f}s")

    print("\n5. Comparing results...")
    if len(original) != len(optimized):
        print(f"   ❌ Pattern count mismatch: {len(original)} vs {len(optimized)}")
        return False

    print(f"   ✅ Pattern count matches: {len(original)} patterns")

    if len(original) > 0:
        def pattern_key(p):
            return (p['indices']['X'], p['indices']['A'], p['indices']['B'],
                    p['indices']['C'], p['indices']['D'])

        orig_keys = {pattern_key(p) for p in original}
        opt_keys = {pattern_key(p) for p in optimized}

        if orig_keys == opt_keys:
            print(f"   ✅ All pattern indices match!")
        else:
            print(f"   ❌ Pattern indices mismatch")
            return False

    print("\n6. Performance:")
    print(f"   Original:  {orig_time:.3f}s")
    print(f"   Optimized: {opt_time:.3f}s")
    if opt_time > 0:
        speedup = orig_time / opt_time
        print(f"   Speedup:   {speedup:.2f}x {'🚀' if speedup > 1 else ''}")

    print("\n" + "="*80)
    print("✅ MEDIUM TEST PASSED!")
    print("="*80)
    return True


if __name__ == "__main__":
    # Run progressively harder tests
    results = []

    # Test 1: Minimal
    try:
        success = test_minimal()
        results.append(("Minimal (100 rows, L=5, window=20)", success))
        if not success:
            print("\n❌ Minimal test failed - stopping")
            exit(1)
    except Exception as e:
        print(f"\n❌ Minimal test error: {e}")
        exit(1)

    # Test 2: Small
    try:
        success = test_small()
        results.append(("Small (Full data, L=4)", success))
        if not success:
            print("\n❌ Small test failed - stopping")
            exit(1)
    except Exception as e:
        print(f"\n❌ Small test error: {e}")
        exit(1)

    # Test 3: Medium (only if small passed)
    try:
        success = test_medium()
        results.append(("Medium (Full data, L=3)", success))
    except Exception as e:
        print(f"\n❌ Medium test error: {e}")
        results.append(("Medium (Full data, L=3)", False))

    # Final summary
    print("\n\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)

    for i, (name, success) in enumerate(results, 1):
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{i}. {name}: {status}")

    all_passed = all(r[1] for r in results)

    print("\n" + "="*80)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("O(n³) implementation is correct!")
    else:
        print("❌ SOME TESTS FAILED")
    print("="*80)

    exit(0 if all_passed else 1)
