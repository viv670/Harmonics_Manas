# Pending Issues to Resolve

## 1. Backtesting Dialog X-Axis Date Format Not Updating

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

## 3. Remove "Pending" Patterns from Backtesting Completion Analysis

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

## 4. Check if Fibonacci and Harmonic Points are Applied to ABCD Patterns

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

## 5. Fibonacci Analysis - Define Range and Review Calculation Logic

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

## 6. Harmonic Pattern Points Analysis - Review Results and Define Analysis Window

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
- Issue #5 (Fibonacci Analysis) - **IDENTICAL analysis window problem**
- Both features need same solution for defining when analysis should stop

**Next Steps**:
1. Review results from both Fibonacci and Harmonic Points analysis
2. Decide on practical analysis window (e.g., 100-200 candles after reversal)
3. Define what "pattern finished" means for analysis purposes
4. Apply same solution to both Fibonacci and Harmonic Points analysis

**Date Created**: 2025-10-05
**Priority**: High - affects usefulness of both Fibonacci and Harmonic Points statistics for trading decisions

---

## 7. Display Historical Fibonacci/Harmonic Statistics in Active Trading Signals

**Status**: PLANNED - Future enhancement idea

**Description**:
Integrate historical backtesting statistics into the live Active Trading Signals window to provide real-time decision support. When a pattern appears in Active Signals, display historical performance data from backtesting to help users make informed trading decisions.

**Proposed Features**:

1. **Symbol + Pattern Type Statistics**
   - Store Fibonacci and Harmonic analysis results by Symbol and Pattern Type
   - Key format: `{SYMBOL}_{PATTERN}_{DIRECTION}` (e.g., `BTCUSDT_Gartley_bull`)
   - Save to database or JSON file after each backtest

2. **Live Display in Active Signals**
   - Add column or expandable section showing historical stats
   - Example display:
     ```
     Pattern: BTCUSDT Gartley Bull
     Historical Data (15 patterns analyzed):
     - 61.8% Fib: Avg 7.2 crosses (high oscillation - good TP)
     - Point A: Hit 80% of the time
     - Point C: Hit 65% of the time
     - Avg time to completion: 12 candles
     ```

3. **Decision Support Information**
   - Show which Fibonacci levels have highest crossing frequency → Best TP zones
   - Show harmonic point hit rates → Probability of retracement
   - Display sample size (how many historical patterns analyzed)
   - Color code: Green = high confidence (many samples), Yellow = medium, Red = low samples

4. **Real-Time Context**
   - User sees pattern forming live
   - System shows: "Based on 15 historical BTCUSDT Gartley patterns..."
   - User can decide whether to take trade based on historical performance
   - No need to switch to backtesting - all info available in monitoring window

**Implementation Steps**:
1. Create statistics storage system (SQLite table or JSON):
   - Table: `pattern_statistics`
   - Columns: symbol, pattern_type, direction, fib_level, avg_crosses, point_hit_rate, sample_count, last_updated

2. Update backtesting to save results:
   - After Fibonacci/Harmonic analysis completes, save stats to database
   - Aggregate by symbol + pattern type + direction

3. Query stats when pattern detected:
   - In Active Signals, when pattern appears, query historical stats
   - Display in tooltip, expandable row, or dedicated column

4. UI Enhancement options:
   - Tooltip on hover: Quick stats preview
   - Expandable row: Click to see detailed breakdown
   - Separate column: Always visible summary
   - Side panel: Full historical analysis

**Benefits**:
- Live trading decisions backed by historical data
- No manual cross-referencing between backtesting and live monitoring
- Confidence scores based on sample size
- Identify which patterns work best for each symbol
- Spot patterns with high Fibonacci oscillation = optimal TP zones

**Example User Workflow**:
1. Pattern appears: BTCUSDT Gartley Bull detected
2. Active Signals shows: "Historical: 61.8% Fib 8.2x crosses (excellent TP), Point A hit 75%"
3. User sees high oscillation at 61.8% → Sets take profit there
4. Makes informed decision based on historical performance

**Related Issues**:
- Issue #5: Fibonacci Analysis (provides source data)
- Issue #6: Harmonic Points Analysis (provides source data)
- Both analyses must be completed and refined before this feature

**Dependencies**:
- Fibonacci crossing analysis must be working correctly
- Harmonic points analysis must be working correctly
- Statistics storage system must be designed
- Active Signals window UI must support additional data display

**Date Created**: 2025-10-06
**Priority**: Medium-High - Powerful feature for trading decisions, but depends on completing Issues #5 and #6 first

---

## 8. BacktestingDialog Does Not Open in Maximized Mode

**Status**: NOT RESOLVED - Low priority

**Description**:
BacktestingDialog window does not open in maximized mode by default, despite having the maximize functionality implemented. All other windows (ActiveSignalsWindow, PatternChartWindow, AllPatternsWindow, PatternViewerWindow, Main window, Watchlist dialog) open maximized correctly.

**Current Implementation**:
- `setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)` added
- `QTimer.singleShot(0, self.showMaximized)` called after `initUI()` in `__init__`
- QTimer imported in backtesting_dialog.py

**Investigation**:
The issue is likely related to how QDialog behaves differently from QMainWindow when `.show()` is called from the parent window (harmonic_patterns_qt.py line 5925). The parent calls `self.backtesting_dialog.show()` which may override the internal `showMaximized()` call.

**Attempted Fixes**:
1. Called `showMaximized()` directly after `initUI()` - didn't work
2. Used `QTimer.singleShot(0, self.showMaximized)` to delay maximize - didn't work
3. Both maximize button and window flags are correctly set

**Possible Solutions** (not yet attempted):
1. Override the `show()` method in BacktestingDialog to call `showMaximized()` instead
2. Change the parent window to call `showMaximized()` instead of `show()`
3. Use `exec()` or different dialog show mode
4. Convert to QMainWindow instead of QDialog

**Files Modified**:
- backtesting_dialog.py: Lines 12 (QTimer import), 253 (window flags), 268 (showMaximized call)

**Date Created**: 2025-10-07
**Priority**: Low - User can manually maximize; does not affect functionality

