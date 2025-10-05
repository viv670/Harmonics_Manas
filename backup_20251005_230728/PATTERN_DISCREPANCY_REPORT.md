# Pattern Detection Discrepancy Analysis Report

## Executive Summary
The discrepancy between GUI showing 4 patterns while the Excel backtesting report shows 15 successful ABCD patterns is caused by **different extremum detection settings**.

## Root Cause Identified

### 1. **Extremum Length Parameter Mismatch**
- **GUI Default**: `extremum_length = 2` (harmonic_patterns_qt.py:2425)
- **Backtester Default**: `extremum_length = 1` (backtesting_dialog.py:44)

### 2. **Impact of Extremum Length**
The extremum length determines how swing highs and lows are detected:
- `length = 1`: Detects local peaks/troughs with 1 bar on each side
- `length = 2`: Detects local peaks/troughs with 2 bars on each side (more selective)

#### With length = 1 (Backtester):
- More extremum points are detected
- More pattern combinations possible
- Results in ~15 ABCD patterns detected

#### With length = 2 (GUI):
- Fewer extremum points are detected (more strict filtering)
- Fewer pattern combinations possible
- Results in ~4 ABCD patterns detected

## Code Evidence

### GUI Setting (harmonic_patterns_qt.py)
```python
# Line 2422-2425
self.length_spinbox = QSpinBox()
self.length_spinbox.setMinimum(1)
self.length_spinbox.setMaximum(20)
self.length_spinbox.setValue(2)  # DEFAULT IS 2
```

### Backtester Setting (backtesting_dialog.py)
```python
# Line 44
extremum_length=self.params.get('extremum_length', 1)  # DEFAULT IS 1
```

## Solution

### Immediate Fix
Before running backtesting, ensure the extremum length in the backtesting dialog matches the GUI setting:
1. In the backtesting dialog, set extremum length to match what was used in the GUI
2. Or change both to use the same default value

### Permanent Fix Options

#### Option 1: Synchronize Settings (Recommended)
Make the backtester automatically use the same extremum_length as the main GUI:

```python
# In backtesting_dialog.py, get the value from main window
if hasattr(self.parent, 'length_spinbox'):
    default_extremum = self.parent.length_spinbox.value()
else:
    default_extremum = 2  # Match GUI default
```

#### Option 2: Standardize Defaults
Change both files to use the same default value (e.g., 2):

```python
# backtesting_dialog.py line 44
extremum_length=self.params.get('extremum_length', 2)  # Changed from 1 to 2
```

## Verification

To verify this is the issue:
1. Run the GUI with extremum_length = 1
2. Run backtesting with extremum_length = 1
3. Pattern counts should match more closely

Or:
1. Run the GUI with extremum_length = 2
2. Run backtesting with extremum_length = 2
3. Pattern counts should match more closely

## Technical Details

### Pattern Detection Flow
1. **Extremum Detection**: Identifies swing highs/lows based on `length` parameter
2. **Pattern Formation**: Combines extremum points to form ABCD patterns
3. **Pattern Validation**: Checks if patterns meet ratio requirements

### Why This Causes Large Discrepancies
- With length=1: If data has 100 extremum points
- With length=2: Same data might have only 40 extremum points
- Pattern combinations grow exponentially with extremum count
- Result: 2.5x difference in extremums can lead to 3-4x difference in patterns

## Recommendations

1. **Immediate Action**: Always verify extremum_length settings match between GUI and backtesting
2. **Code Update**: Implement Option 1 (Synchronize Settings) for automatic consistency
3. **User Interface**: Add clear labels showing current extremum_length in both GUI and backtesting
4. **Documentation**: Document this parameter's importance for users

## Conclusion

The discrepancy is not a bug in pattern detection logic but a configuration mismatch. Both the GUI and backtester are working correctly with their respective settings. The solution is to ensure consistent extremum_length parameters across all components of the system.