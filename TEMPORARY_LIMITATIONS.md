# TEMPORARY PERFORMANCE LIMITATIONS

## Current Status: BALANCED LIMITS ACTIVE
**Date Added**: 2025-09-28
**Last Updated**: 2025-09-28 (Adjusted to Balanced Limits)
**Reason**: Pattern detection was taking 120+ seconds. Ultra-limits were too restrictive (finding 0-5 patterns). Now using balanced limits for good performance AND pattern discovery.

## Limitations Applied

### 1. ABCD Pattern Detection (`comprehensive_abcd_patterns.py` and GUI)
- **Code File Limits**: Lines 566-574, 595-603
  - Only checks last 500 extremum points
  - Only looks 20 extremum points ahead for B and C

- **GUI BALANCED LIMITS** (`harmonic_patterns_qt.py`):
  - Only checks last **200 extremum points** for ABCD (instead of all 1400+)
  - Only looks **20 extremum points** ahead for pattern detection
  - Maximum **100 patterns** returned
  - Uses normal mode for better pattern discovery

- **Impact**: May miss patterns that:
  - Occur before the last 30 extremum points
  - Have points separated by more than 5 extremum points
  - Only returns the first 5 patterns found
- **Original Values**: Should check ALL extremum points with NO limits

### 2. XABCD Pattern Detection (`comprehensive_xabcd_patterns.py` and GUI)
- **Code File Limits**: Lines 451-459
  - Only checks last 300 extremum points
  - Only looks 20 extremum points ahead for each point

- **GUI BALANCED LIMITS** (`harmonic_patterns_qt.py`):
  - Only checks last **150 extremum points** for XABCD (instead of all)
  - Only looks **15 extremum points** ahead for pattern detection
  - Maximum **50 patterns** returned

- **Impact**: May miss patterns that:
  - Occur before the last 20 extremum points
  - Have points separated by more than 3 extremum points
  - Only returns the first 3 patterns found
- **Original Values**: Should check ALL combinations with NO limits

## Performance Impact
- **With BALANCED Limitations (GUI)**: ~5 seconds total for all detections, finds 80+ patterns
- **With ULTRA Limitations (previous)**: ~0.03 seconds but found only 10 patterns
- **Without Limitations**: ~30+ minutes (infeasible for GUI)
- **Combinations Reduced**:
  - ABCD: From ~460 million to ~80,000 combinations (200 points × 20 window × 20 window)
  - XABCD: From billions to ~675,000 combinations (150 points × 15^3)

## How to Remove Limitations

### Step 1: Remove ABCD Limitations
```python
# In comprehensive_abcd_patterns.py, change:
search_window_j = min(20, n)  # TEMPORARY
search_window_k = min(20, n)  # TEMPORARY
# To:
search_window_j = n  # Check ALL points
search_window_k = n  # Check ALL points

# And change:
start_point = max(0, n - 500)  # TEMPORARY
# To:
start_point = 0  # Check from beginning

# And change loop:
for i in range(min(n - 3, start_point + 497), start_point - 1, -1):
# To:
for i in range(n - 3, -1, -1):  # Check ALL points
```

### Step 2: Remove XABCD Limitations
```python
# In comprehensive_xabcd_patterns.py, change:
search_window = 20  # TEMPORARY
# To:
search_window = n  # Check ALL points

# And change:
start_point = max(0, n - 300)  # TEMPORARY
for i in range(start_point, min(n - 3, start_point + 300)):
# To:
for i in range(n - 3):  # Check ALL points
```

## Future Solutions for 100% Accuracy

1. **GPU Acceleration**: Use CUDA/OpenCL for parallel processing
2. **Background Workers**: Process patterns in background threads
3. **Incremental Processing**: Process in chunks and update UI progressively
4. **C++ Extension**: Implement core validation in compiled C++ for 100x speedup
5. **Distributed Processing**: Split work across multiple CPU cores more efficiently

## Notes
- These limitations are TEMPORARY for GUI responsiveness
- Backtesting and batch processing can use unlimited detection
- User has been informed about these limitations
- Priority is to implement proper optimization before removing limits