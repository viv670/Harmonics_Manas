# Debug Instructions for 30% Hang

## Current Debug Setup

The code has been modified to help identify where the hang occurs:

1. **Debug messages added** at key points in PatternDetectionWorker
2. **comprehensive_abcd is TEMPORARILY DISABLED** to isolate the issue

## When You Run the GUI

You should see console output like:
```
DEBUG: Starting strict_abcd at [timestamp]
DEBUG: Finished strict_abcd at [timestamp], found X patterns
DEBUG: About to emit 30% progress
DEBUG: Emitted 30% progress
DEBUG: TEMPORARILY SKIPPING comprehensive_abcd to test if it's the bottleneck
```

## Possible Outcomes

### Outcome 1: GUI completes quickly
- **Means**: comprehensive_abcd was the bottleneck
- **Next step**: Re-enable it and investigate why it's slow with GUI but fast in tests

### Outcome 2: GUI still hangs at 30%
- **Means**: The issue is NOT comprehensive_abcd
- **Possibilities**:
  - Qt threading issue with progress.emit()
  - The GUI is using different data than our tests
  - Memory issue with large datasets

### Outcome 3: GUI hangs but shows different progress %
- **Means**: Different function is the bottleneck
- **Check**: Which function corresponds to that progress percentage

## To Re-enable comprehensive_abcd

In harmonic_patterns_qt.py, lines 278-287, change:
```python
# FROM:
print(f"DEBUG: TEMPORARILY SKIPPING comprehensive_abcd to test if it's the bottleneck", flush=True)
results['comprehensive_abcd'] = []  # TEMPORARY: Skip this to test
# results['comprehensive_abcd'] = self.detect_comprehensive_abcd_patterns()

# TO:
results['comprehensive_abcd'] = self.detect_comprehensive_abcd_patterns()
```

## Additional Checks

1. **Check memory usage** when GUI hangs - might be running out of memory
2. **Check if console shows debug messages** - if not, output might be buffered
3. **Try with smaller dataset** - load only last 1000 candles to test

## Key Question

Are you seeing ANY of the DEBUG messages in the console when running the GUI?
- If YES: Check which is the last message before hang
- If NO: The output is being buffered or redirected somewhere