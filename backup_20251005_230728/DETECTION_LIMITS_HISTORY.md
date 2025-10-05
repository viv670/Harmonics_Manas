# Pattern Detection Limits - Historical Comparison

## Timeline of Changes

### 1. Original Implementation (backup_20250920_160043_before_removal)
**Approach**: Adaptive search windows based on dataset size
```python
# Adaptive search window sizing
if max_search_window is None:
    if n < 10:
        search_window_j = n
        search_window_k = n
    elif n < 50:
        search_window_j = min(30, n)
        search_window_k = min(20, n)
    else:
        search_window_j = min(50, n)  # Max 50 extremum points for j
        search_window_k = min(30, n)  # Max 30 extremum points for k
```
**Limits**:
- For large datasets (>50 extremums): 50 for B, 30 for C
- Had `max_patterns` parameter to limit total patterns
- Used `break` statements when max_patterns reached

### 2. After "Limits Removed" (backup_comprehensive_fix_20250925_171526)
**Approach**: NO LIMITS - Check ALL combinations
```python
# NO LIMITS - Always search entire dataset for 100% certainty
search_window_j = n  # Check ALL possible j points
search_window_k = n  # Check ALL possible k points

# Process ALL points - NO LIMITS
for i in range(n - 3, -1, -1):
    # NO pattern limit check - process everything
    for j in range(i + 1, n - 1):  # Check ALL j points
        for k in range(j + 1, n):  # Check ALL k points
```
**Limits**: NONE - Attempted to check all ~460 million combinations
**Result**: Timeouts, infeasible for GUI usage

### 3. Current Implementation (with temporary limits)
**Approach**: Temporary performance limits with clear documentation
```python
# ==================== TEMPORARY LIMITATION ====================
# TODO: REMOVE THIS LIMITATION IN FUTURE FOR 100% ACCURACY
search_window_j = min(20, n)  # TEMPORARY: Only look 20 extremum points ahead
search_window_k = min(20, n)  # TEMPORARY: Only look 20 extremum points ahead

start_point = max(0, n - 500)  # TEMPORARY: Only check last 500 extremum points
```
**Limits**:
- Only last 500 extremum points checked
- Window of 20 extremum points for B and C
- Clearly marked as TEMPORARY with TODOs

## Performance Comparison

| Version | Search Window | Points Checked | Time (1400 extremums) | Patterns Found |
|---------|--------------|----------------|----------------------|----------------|
| Original | 50/30 | All | ~15-30 seconds | ~100-200 |
| No Limits | All/All | All | Timeout (>30 min) | N/A |
| Current | 20/20 | Last 500 | ~5 seconds | ~50-100 |

## Key Findings

1. **Original had limits**: The original implementation DID have limits (50/30 extremum windows)
2. **"No Limits" was added later**: The complete removal of limits was done recently per user request
3. **Performance trade-off**: Without limits, detection becomes computationally infeasible

## Recommendation

The original approach with 50/30 windows was a good balance between:
- Coverage (finding most patterns)
- Performance (15-30 seconds is acceptable)
- Completeness (checking all starting points)

Consider reverting to original 50/30 windows instead of current 20/20 for better pattern coverage while maintaining reasonable performance.