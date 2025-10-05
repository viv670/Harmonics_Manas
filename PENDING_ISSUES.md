# Pending Issues to Resolve

## 1. XABCD Patterns with Empty D-Lines Appearing in Pending Section

**Status**: NOT RESOLVED - Waiting for investigation

**Description**:
Two XABCD patterns are appearing in the pending section even though their d_lines have failed/are empty:
- Pattern ID: ABCD_e13109118b515e43 (AB=CD_bear_3_unformed)
- Pattern ID: XABCD_756cfcd8600b9580 (MaxBat1_bear_unformed)

**Console Output Reference**:
```
REJECTED XABCD - MaxBat1_bear_unformed - bar 5 - REASON: No valid D-lines
...
Debug output for pending patterns:
  Pattern ABCD_e13109118b515e43 has d_lines: []
  Pattern XABCD_756cfcd8600b9580 has d_lines: []
```

**Current Partial Fix**:
- Added filtering in `backtesting_dialog.py` lines 1317-1320 to skip XABCD patterns with empty d_lines from chart display
- Added dismissal logic in `pattern_tracking_utils.py` lines 669-682 to dismiss pending XABCD patterns with empty d_lines during backtesting

**Root Cause to Investigate**:
Why are XABCD patterns with failed/invalidated d_lines remaining in the pending section instead of being dismissed immediately?

**Next Steps**:
1. Investigate pattern detection and validation flow
2. Check when and why d_lines get invalidated/emptied
3. Ensure patterns are dismissed at the right point in the workflow
4. Distinguish between ABCD patterns (which use prz_zones) and XABCD patterns (which use d_lines)

**User Comment**: "Lets wait for this one. First fix this - next and previous button" (navigation has been fixed)

---

**Date Created**: 2025-10-05
**DO NOT REMOVE THIS NOTE UNTIL THE ISSUE IS FULLY RESOLVED**

---

## 2. Backtesting Dialog X-Axis Date Format Not Updating

**Status**: NOT RESOLVED - Low priority

**Description**:
The x-axis (time axis) in backtesting dialog charts shows dates in full format (e.g., "2025-05-17") instead of the GUI's TradingView-style format (e.g., "17 May").

**Investigation Done**:
- DateAxisItem class is correctly created and installed
- `isinstance(bottom_axis, DateAxisItem)` returns True
- However, `tickStrings()` method is never called by PyQtGraph
- Implementation matches GUI exactly: PlotWidget created once with DateAxisItem, dates updated on each chart display

**Attempted Fixes**:
1. Tried creating PlotWidget with `axisItems={'bottom': self.date_axis}` parameter
2. Tried `setAxisItems()` method
3. Tried forcing axis updates with `.update()` calls
4. Tried recreating widget each time vs. clearing and reusing (GUI approach)
5. All approaches confirm DateAxisItem is installed but tickStrings never gets called

**Current Theory**:
PyQtGraph may be caching tick labels or rendering them before DateAxisItem is ready, or there's a version-specific bug with custom axis items in PlotWidget.

**Workaround**:
The crosshair labels (x-label at bottom and OHLC info box) show correct date formatting, so users can still see proper dates when hovering.

**Files Modified**:
- backtesting_dialog.py: Added DateAxisItem class (lines 29-57), chart setup (lines 335-341)

**Next Steps** (when prioritized):
1. Test with different PyQtGraph versions
2. Try manually setting ticks with `setTicks()` method
3. Check if PyQtGraph documentation has updated custom axis API

**Date Created**: 2025-10-05
**Priority**: Low - does not affect functionality, only visual formatting

---

## 3. Redefine Failed PRZ vs Invalid PRZ Logic

**Status**: TEMPORARILY RESOLVED - Awaiting future definition

**Temporary Solution Implemented**:
All PRZ violations (both single-candle and multi-candle) are now combined under "Invalid PRZ" category.

**Changes Made**:
1. **pattern_tracking_utils.py**:
   - Changed all 'failed' status to 'invalid_prz' throughout the file
   - Updated dataclass comments: `status: str = 'pending'  # pending, success, invalid_prz, dismissed`
   - Updated all statistics tracking to use 'invalid_prz' instead of 'failed'
   - Fixed all variable references (failed → invalid_prz)

2. **backtesting_dialog.py**:
   - Removed "Failed PRZ" button from UI
   - Updated status_map to remove 'failed' entry
   - Updated category_names dictionaries to use only 'invalid_prz'
   - Kept single "Invalid PRZ" button with combined count

**Future Consideration**:
If later needed, "Failed PRZ" can be redefined for patterns that show reversal behavior but ultimately fail to reach target. For now, all PRZ violations are treated as "Invalid PRZ".

**Date Created**: 2025-10-05
**Priority**: Medium - affects pattern categorization and analysis

---

## 4. Remove "Pending" Patterns from Backtesting Completion Analysis

**Status**: NOT DECIDED - Awaiting user decision

**Question**:
Should "Pending" patterns be shown in the backtesting completion analysis section?

**Current Behavior**:
The backtesting dialog shows 6 buttons:
- ✓ Completed Successfully
- ⚠ Invalid PRZ
- ✗ Failed PRZ
- ◉ In PRZ Zone
- ⊘ Dismissed
- ⧗ Pending

**Issue**:
Backtesting analyzes historical data, so technically "Pending" patterns (that haven't reached PRZ yet) shouldn't be part of the completion analysis since:
- They haven't had a chance to succeed or fail
- The backtest has ended, so they won't get a resolution
- They're incomplete by definition

**Options**:
1. **Remove "Pending" button** - Only show patterns that reached some conclusion
2. **Keep "Pending" button** - Shows patterns that were detected but never reached PRZ during the backtest period
3. **Rename to "Incomplete"** - Better reflects that these are patterns that ran out of data

**Next Steps**:
User to decide whether to keep, remove, or rename the "Pending" category in backtesting results.

**Date Created**: 2025-10-05
**Priority**: Low - cosmetic/organizational, doesn't affect functionality

---

## 5. Check if Fibonacci and Harmonic Points are Applied to ABCD Patterns

**Status**: NOT CHECKED - Needs investigation

**Question**:
Are Fibonacci levels and harmonic analysis points being applied correctly to ABCD patterns, or only to XABCD patterns?

**Current Implementation**:
- Fibonacci toggle checkbox added in backtesting dialog for successful patterns
- Fibonacci levels calculated from Point A/C to Point D (using zone_entry_price for unformed patterns)
- Need to verify this works correctly for both ABCD and XABCD pattern types

**Next Steps**:
1. Test Fibonacci display on ABCD patterns
2. Test Fibonacci display on XABCD patterns
3. Verify harmonic analysis points are correctly tracked for both pattern types
4. Check if any special handling is needed for ABCD vs XABCD

**Date Created**: 2025-10-05
**Priority**: Medium - affects accuracy of Fibonacci visualization

---

## 6. Fibonacci Analysis - Define Range and Review Calculation Logic

**Status**: NEEDS REVIEW - Current behavior produces large candle counts (2500+)

**Issue**:
The Fibonacci analysis counts from reversal bar until each Fibonacci level is touched, resulting in very large candle numbers because price may trend for thousands of candles before retracing.

**Current Behavior**:
- Fibonacci levels calculated from max/min(A,C) to D
- Analysis starts from reversal_bar (when pattern succeeded)
- Counts candles until each level (0%, 23.6%, 50%, 61.8%, etc.) is touched
- Checks from reversal bar to end of all available data
- Tracks exact touches (low ≤ level ≤ high) up to 161.8% Fibonacci level

**Example from Console:**
- Pattern reversed at bar 132
- 0% level touched at candle 2522 (2522 candles after reversal!)
- 50% level touched at candle 2582 (2582 candles after reversal!)

**Questions to Answer:**
1. Should we limit the analysis window? (e.g., only next 50, 100, or 200 candles after reversal)
2. Should we calculate retracement FROM D back toward A/C instead of current method?
3. Should we track both retracement AND extension levels separately?
4. What time window makes sense for practical trading analysis?
5. Until structure break? Until next pattern? Until 161.8% touched?

**Considerations**:
- Too short: May miss important Fibonacci interactions
- Too long: Includes irrelevant price action thousands of candles later
- Current approach (until end of data) gives impractical numbers for trading decisions

**Code Location**:
- backtesting_dialog.py lines 2133-2172 (Fibonacci level touch detection)

**Next Steps**:
User to decide the optimal range and calculation method for Fibonacci touch analysis.

**Date Created**: 2025-10-05
**Priority**: High - affects usefulness of Fibonacci statistics for trading decisions

---

## 7. Harmonic Pattern Points Analysis - Review Results and Define Analysis Window

**Status**: IMPLEMENTED BUT NEEDS REVIEW - Same issues as Fibonacci analysis

**Implementation Completed**:
- ✅ Added "🎯 Harmonic Points Analysis" button (teal color #20B2AA)
- ✅ Created `runHarmonicPointsAnalysis()` function in backtesting_dialog.py
- ✅ Created `showHarmonicPointsAnalysisResults()` with table display
- ✅ Tracks touches of Point A, B, C price levels after reversal
- ✅ Two tabs: Combined Analysis (aggregated stats) and Individual Patterns (per-pattern details)
- ✅ Only works on "Completed Successfully" patterns (same validation as Fibonacci)

**Current Issue**:
Same problem as Fibonacci analysis - all candle counts are greater than 2500 because analysis continues until end of available data.

**Questions to Answer** (Same as Issue #6):
1. **When should harmonic points analysis stop?**
   - Until structure break?
   - Until next pattern formation?
   - Fixed window (50, 100, 200 candles after reversal)?
   - Until all points (A, B, C) touched once?
   - Until end of data (current behavior)?

2. **What defines "pattern finished" for analysis purposes?**
   - Pattern target reached?
   - Structure break occurs?
   - New pattern detected?
   - Fixed time/candle limit?

3. **Should we limit analysis window for practical trading decisions?**
   - Current behavior: checks thousands of candles later (impractical)
   - Suggested: limit to next 100-200 candles for realistic trading window

**Code Location**:
- backtesting_dialog.py lines 2342-2615 (Harmonic Points Analysis implementation)

**Related To:**
- Issue #6 (Fibonacci Analysis) - **IDENTICAL analysis window problem**
- Both features need same solution for defining when analysis should stop

**Next Steps**:
1. Review results from both Fibonacci and Harmonic Points analysis
2. Decide on practical analysis window (e.g., 100-200 candles after reversal)
3. Define what "pattern finished" means for analysis purposes
4. Apply same solution to both Fibonacci and Harmonic Points analysis

**Date Created**: 2025-10-05
**Priority**: High - affects usefulness of both Fibonacci and Harmonic Points statistics for trading decisions

---

## 8. Verify All Formed Patterns from GUI Appear in Backtesting "Completed Successfully"

**Status**: NOT VERIFIED - Needs testing

**Question**:
When a pattern transitions from unformed to formed, does it correctly appear in the backtesting dialog's "✓ Completed Successfully" category?

**Verification Needed**:
1. **Compare counts**: Check if GUI shows the same number of formed patterns as backtesting "Completed Successfully"
2. **Pattern transition tracking**: Verify that patterns initially detected as unformed and later becoming formed are properly tracked
3. **Status update logic**: Confirm that `pattern_tracking_utils.py` correctly updates pattern status from 'pending' to 'success' when formation conditions are met

**What to Check**:
- Run backtest on a symbol/timeframe that has known formed patterns in GUI
- Compare GUI formed pattern count with backtesting "Completed Successfully" count
- Check if all pattern IDs from GUI formed patterns exist in backtesting results
- Verify that patterns aren't being dismissed or lost during unformed → formed transition

**Potential Issues**:
- Patterns might be dismissed before they have a chance to form
- Status update might not trigger correctly when D point is reached
- Pattern tracking might lose reference during transition from unformed to formed

**Code Locations to Review**:
- `pattern_tracking_utils.py`: Status update logic for pattern formation
- `backtesting_dialog.py`: "Completed Successfully" filtering and display logic
- Pattern detection files: `formed_abcd.py`, `formed_xabcd.py`

**Next Steps**:
1. Run backtest and compare with GUI pattern counts
2. If counts don't match, investigate which patterns are missing
3. Review pattern transition logic in tracking utilities

**Date Created**: 2025-10-05
**Priority**: High - affects accuracy and reliability of backtesting results
