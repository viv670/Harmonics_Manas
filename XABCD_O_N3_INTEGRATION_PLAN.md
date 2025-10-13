# O(n³) XABCD Integration Plan

## 📋 Files Using Old `detect_xabcd_patterns`

### Active Production Files (Need Replacement)

1. **harmonic_patterns_qt.py** (Main GUI)
   - Line 104: `from formed_xabcd import detect_xabcd_patterns as detect_formed_xabcd_func`
   - Line 364: `results['xabcd'] = self.detect_xabcd_patterns()`
   - Line 684: Method definition `def detect_xabcd_patterns(self):`
   - **Usage**: GUI pattern detection with extremum_length from settings

2. **gui_compatible_detection.py** (Detection Interface)
   - Line 11: `from formed_xabcd import detect_xabcd_patterns as detect_strict_xabcd_patterns`
   - Line 123: `patterns = detect_strict_xabcd_patterns(extremums, df, ...)`
   - **Usage**: Wrapper for GUI-compatible pattern detection

3. **pattern_monitor_service.py** (Background Monitoring)
   - Line 22: `from formed_xabcd import detect_xabcd_patterns`
   - Line 356: `formed_xabcd = detect_xabcd_patterns(extremums_indexed, df=data_with_date, ...)`
   - **Usage**: Background pattern monitoring and alerts

### Test Files (Keep for Comparison)

- test_xabcd_o_n3_minimal.py
- test_xabcd_o_n3_final.py
- test_xabcd_o_n3_targeted.py
- test_xabcd_o_n3_extended.py
- test_xabcd_o_n3_quick.py
- test_xabcd_o_n3.py

### Backup/Archive Files (No Changes Needed)

- All files in `backup_*/`, `backups/`, `archive_unused/`
- Documentation files (.md)

---

## 🎯 Integration Strategy

### Option 1: Adaptive Selection (RECOMMENDED)

Add smart selection logic that automatically chooses the best implementation based on extremum count:

```python
def detect_xabcd_patterns_smart(extremum_points, df, **kwargs):
    """
    Automatically select best XABCD implementation based on dataset size.

    - Small datasets (n < 60): Use original (optimized for small n)
    - Large datasets (n >= 60): Use O(n³) (much faster for large n)
    """
    n = len(extremum_points)

    if n >= 60:
        from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3
        return detect_xabcd_patterns_o_n3(extremum_points, df, **kwargs)
    else:
        from formed_xabcd import detect_xabcd_patterns
        return detect_xabcd_patterns(extremum_points, df, **kwargs)
```

**Advantages:**
- ✅ Best performance for all cases
- ✅ No user configuration needed
- ✅ Backward compatible
- ✅ Automatically benefits from O(n³) for large datasets

**Implementation:**
1. Add `detect_xabcd_patterns_smart()` to a new file: `xabcd_detection.py`
2. Replace imports in production files to use smart function
3. No changes to function calls needed

### Option 2: Direct Replacement

Replace all usage with O(n³) implementation directly:

```python
# OLD
from formed_xabcd import detect_xabcd_patterns

# NEW
from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3 as detect_xabcd_patterns
```

**Advantages:**
- ✅ Simple one-line change
- ✅ Always uses optimized version

**Disadvantages:**
- ⚠️ Slightly slower for very small n (< 50)

### Option 3: Configuration Setting

Add a setting in the GUI to choose implementation:

```python
# In config or settings
USE_OPTIMIZED_XABCD = True  # Default to optimized

if USE_OPTIMIZED_XABCD:
    from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3 as detect_xabcd_patterns
else:
    from formed_xabcd import detect_xabcd_patterns
```

**Advantages:**
- ✅ User control
- ✅ Easy to switch back if issues

**Disadvantages:**
- ⚠️ Requires user decision
- ⚠️ More complex configuration

---

## 📝 Recommended Implementation Plan

### Step 1: Create Smart Wrapper (NEW FILE)

Create `xabcd_detection.py`:

```python
"""
Smart XABCD Detection - Adaptive Algorithm Selection
=====================================================

Automatically selects the best XABCD implementation based on dataset size:
- Small datasets (n < 60): Original O(n⁵) with early optimizations
- Large datasets (n >= 60): O(n³) meet-in-the-middle algorithm
"""

from typing import List, Tuple, Dict, Optional
import pandas as pd


def detect_xabcd_patterns_smart(extremum_points: List[Tuple],
                                 df: pd.DataFrame = None,
                                 log_details: bool = False,
                                 strict_validation: bool = True,
                                 max_search_window: Optional[int] = None,
                                 validate_d_crossing: bool = True) -> List[Dict]:
    """
    Smart XABCD detection with automatic algorithm selection.

    Args:
        extremum_points: List of (timestamp, price, is_high, bar_index)
        df: DataFrame for validation
        log_details: Print progress
        strict_validation: Apply price containment
        max_search_window: Max distance between points (None = unlimited)
        validate_d_crossing: Validate D point crossing

    Returns:
        List of pattern dictionaries
    """
    n = len(extremum_points)

    # Adaptive selection
    if n >= 60:
        # Use O(n³) for large datasets
        from formed_xabcd_o_n3 import detect_xabcd_patterns_o_n3

        if log_details:
            print(f"[Smart] Using O(n³) implementation for n={n}")

        return detect_xabcd_patterns_o_n3(
            extremum_points, df, log_details,
            strict_validation, max_search_window, validate_d_crossing
        )
    else:
        # Use original for small datasets
        from formed_xabcd import detect_xabcd_patterns

        if log_details:
            print(f"[Smart] Using original implementation for n={n}")

        return detect_xabcd_patterns(
            extremum_points, df, log_details,
            strict_validation, max_search_window, validate_d_crossing
        )


# Alias for backward compatibility
detect_xabcd_patterns = detect_xabcd_patterns_smart
```

### Step 2: Update Production Files

#### A. harmonic_patterns_qt.py

**Change import (line 104):**
```python
# OLD
from formed_xabcd import detect_xabcd_patterns as detect_formed_xabcd_func

# NEW
from xabcd_detection import detect_xabcd_patterns_smart as detect_formed_xabcd_func
```

**No changes needed to function calls** - signature is identical!

#### B. gui_compatible_detection.py

**Change import (line 11):**
```python
# OLD
from formed_xabcd import detect_xabcd_patterns as detect_strict_xabcd_patterns

# NEW
from xabcd_detection import detect_xabcd_patterns_smart as detect_strict_xabcd_patterns
```

#### C. pattern_monitor_service.py

**Change import (line 22):**
```python
# OLD
from formed_xabcd import detect_xabcd_patterns

# NEW
from xabcd_detection import detect_xabcd_patterns_smart as detect_xabcd_patterns
```

### Step 3: Test Integration

**Test scenarios:**
1. ✅ GUI detection with L=3 (typically ~72 points) → Should use O(n³)
2. ✅ GUI detection with L=5 (typically ~48 points) → Should use original
3. ✅ Background monitoring → Adaptive based on extremum count
4. ✅ Verify patterns match previous results
5. ✅ Verify performance improvement for large datasets

### Step 4: Add Logging (Optional)

Add optional logging to track which algorithm is used:

```python
# In xabcd_detection.py
import logging
logger = logging.getLogger(__name__)

if n >= 60:
    logger.info(f"XABCD: Using O(n³) for {n} extremum points")
    # ... use O(n³)
else:
    logger.debug(f"XABCD: Using original for {n} extremum points")
    # ... use original
```

---

## 🧪 Testing Checklist

### Functional Tests

- [ ] GUI pattern detection works correctly
- [ ] Pattern counts match previous results
- [ ] Pattern details (X, A, B, C, D) match
- [ ] Background monitoring continues to work
- [ ] No crashes or errors in GUI

### Performance Tests

- [ ] L=3 (n~72) is faster than before
- [ ] L=4 (n~54) has similar or better performance
- [ ] L=5 (n~48) has similar performance
- [ ] No noticeable delay in GUI

### Edge Cases

- [ ] Small extremum sets (n < 5) handled gracefully
- [ ] Large extremum sets (n > 100) work correctly
- [ ] Empty results handled correctly
- [ ] Different validation settings work

---

## 📊 Expected Results

### Before Integration (Current)

| Extremum Length | Typical n | Detection Time |
|----------------|-----------|----------------|
| L=5 | 48 | ~2.5s |
| L=4 | 54 | ~5s |
| L=3 | 72 | ~17s |
| L=2 | 98 | ~60s+ |
| L=1 | 168 | Timeout (minutes) |

### After Integration (With Smart Selection)

| Extremum Length | Typical n | Algorithm | Detection Time | Speedup |
|----------------|-----------|-----------|----------------|---------|
| L=5 | 48 | Original | ~2.5s | 1x (no change) |
| L=4 | 54 | Original | ~5s | 1x (no change) |
| L=3 | 72 | **O(n³)** | **~4s** | **4.2x faster** ✅ |
| L=2 | 98 | **O(n³)** | **~10-15s** | **4-6x faster** ✅ |
| L=1 | 168 | **O(n³)** | **~30-60s** | **100x+ faster** ✅ |

### Impact

- **Most users (L=3-5)**: Will see 4x speedup for L=3, same speed for L=4-5
- **Power users (L=1-2)**: Can now use exhaustive search practically
- **Background monitoring**: Automatically benefits for all symbols

---

## 🚀 Rollout Plan

### Phase 1: Create Smart Wrapper ✅
- Create `xabcd_detection.py` with adaptive selection
- Add comprehensive docstrings
- Include logging

### Phase 2: Update Production Files
- Update imports in 3 files
- No changes to function calls needed
- Add comments explaining adaptive selection

### Phase 3: Testing
- Test with GUI (various extremum lengths)
- Test background monitoring
- Verify pattern consistency
- Measure performance improvements

### Phase 4: Monitoring
- Monitor for any issues in first few days
- Check logs for algorithm selection distribution
- Collect performance metrics

### Phase 5: Documentation
- Update user documentation
- Add performance notes
- Document adaptive threshold (n=60)

---

## 🔄 Rollback Plan

If any issues arise:

```python
# In xabcd_detection.py - Emergency rollback
USE_ORIGINAL_ONLY = True  # Set to True to disable O(n³)

if USE_ORIGINAL_ONLY or n >= 60:  # Change condition
    from formed_xabcd import detect_xabcd_patterns
    return detect_xabcd_patterns(...)
```

Or simply revert imports to original:
```python
from formed_xabcd import detect_xabcd_patterns
```

---

## 📚 Files Summary

### New Files to Create
- `xabcd_detection.py` - Smart wrapper with adaptive selection

### Files to Modify (3 files)
- `harmonic_patterns_qt.py` - Line 104 import
- `gui_compatible_detection.py` - Line 11 import
- `pattern_monitor_service.py` - Line 22 import

### Files to Keep Unchanged
- `formed_xabcd.py` - Original implementation (still used for n < 60)
- `formed_xabcd_o_n3.py` - O(n³) implementation (used for n >= 60)
- All test files
- All backup files

---

**Ready to proceed with integration!**
