# Active Trading Signals - Complete Walkthrough

## Overview
The Active Trading Signals window is your central hub for monitoring detected harmonic patterns, viewing their details, and managing price alerts.

---

## Window Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔔 Active Trading Signals                    [Pause] [Refresh] │
├─────────────────────────────────────────────────────────────────┤
│ Filters: [Symbol] [TF] [Pattern] [Direction] [Status]          │
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ SIGNALS TABLE (Top Half)                                    │ │
│ │ Symbol│TF│Pattern│Direction│Status│Price│PRZ│Distance│...  │ │
│ │ BTCUSDT│1d│Gartley│Bullish│Detected│$62,345│...│2.5%│... │ │
│ │ ETHUSDT│2d│Bat│Bearish│Approaching│$3,245│...│0.8%│...    │ │
│ └─────────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────┬──────────────────────────────────┐ │
│ │ PATTERN INFORMATION      │ PRICE ALERTS CONTROL             │ │
│ │ (Left - Details)         │ (Right - Alert Checkboxes)       │ │
│ │                          │                                  │ │
│ │ • Pattern details        │ [✓] Fibonacci  Fib 0%   $61,500 │ │
│ │ • Price levels           │ [ ] Fibonacci  Fib 23.6% $62,451│ │
│ │ • Targets                │ [✓] Fibonacci  Fib 50%  $63,750 │ │
│ │ • Historical stats       │ [ ] Harmonic   Point A  $64,000 │ │
│ │ • Price alerts summary   │ [✓] Harmonic   Point C  $55,200 │ │
│ └──────────────────────────┴──────────────────────────────────┘ │
│                                                                 │
│ [🗑️ Remove from Monitoring]                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Section 1: Signal Details (Left Side)

### What You See:

When you **select a pattern** from the table, the left side shows:

#### **A. Basic Pattern Information**
```
BTCUSDT 1d - Gartley1 Bullish

Pattern Type: XABCD
Direction: Bullish
Status: Detected
```

#### **B. Price Levels**
```
Current Price: $62,345.00
PRZ Zone: $61,000.00 - $61,500.00
Entry Price: $61,250.00
Stop Loss: $60,500.00
```

**What this means:**
- **Current Price**: Live price from latest data
- **PRZ Zone**: Potential Reversal Zone (where pattern completes)
- **Entry Price**: Recommended entry at PRZ midpoint
- **Stop Loss**: Calculated based on pattern structure

#### **C. Targets (Take Profit Levels)**
```
Target 1: $62,750.00
Target 2: $64,125.00
Target 3: $65,500.00
Target 4: $66,875.00
Target 5: $68,250.00
```

**What this means:**
- 5 targets calculated from Fibonacci extensions
- TP1 = 38.2%, TP2 = 61.8%, TP3 = 100%, TP4 = 127.2%, TP5 = 161.8%

#### **D. Pattern Points**
```json
{"X": 211, "A": 227, "B": 241, "C": 245, "D": null}
```

**What this means:**
- Bar indices where each pattern point occurred
- `D: null` means unformed pattern (waiting for D point)

#### **E. Timeline**
```
Detected: 2025-10-07 06:08:02
Last Updated: 2025-10-07 06:08:02
```

#### **F. System Alerts**
```
Status Change: Detected
```

**What this means:**
- Shows which alerts have been sent for this pattern
- Examples: "Status Change: Approaching", "PRZ Entered", etc.

---

## Section 2: Price Alerts (Still Left Side, Below Details)

### What You See:

#### **Fibonacci Levels:**
```
⭕ Fib 0% at $61,500.00 - Disabled
⭕ Fib 23.6% at $62,451.23 - Disabled
⭕ Fib 38.2% at $63,076.45 - Disabled
🔔 Fib 50% at $63,750.00 - Enabled
🔔 Fib 61.8% at $64,680.11 - Enabled
⭕ Fib 78.6% at $65,890.67 - Disabled
⭕ Fib 88.6% at $66,456.78 - Disabled
⭕ Fib 100% at $67,000.00 - Disabled
⭕ Fib 112.8% at $67,890.45 - Disabled
⭕ Fib 127.2% at $68,904.23 - Disabled
⭕ Fib 141.4% at $69,876.12 - Disabled
⭕ Fib 161.8% at $71,456.89 - Disabled
```

#### **Harmonic Points:**
```
⭕ Point A at $64,000.00 - Disabled
🔔 Point B at $59,500.00 - Enabled
🔔 Point C at $55,200.00 - Enabled
```

#### **Icons Explained:**
- **⭕ Gray Circle**: Alert is **disabled** (not monitoring this level)
- **🔔 Bell**: Alert is **enabled** (actively monitoring this level)
- **✅ Green Check**: Alert was **triggered** (price hit this level already)

#### **Tip at Bottom:**
```
💡 Tip: Enable/disable alerts using checkboxes below.
All alerts are disabled by default.
```

---

## Section 3: Historical Statistics (Left Side, Below Price Alerts)

### What You See (If Statistics Available):

```
─────────────────────────────────────────────────────────────
📊 Historical Statistics (From Backtesting):
─────────────────────────────────────────────────────────────
Based on 15 historical XABCD Gartley1 bullish patterns for BTCUSDT 1d

Fibonacci Levels (Most Hit):
  • Fib 50%: 80.0% hit rate, 2.3 avg touches (green)
  • Fib 61.8%: 73.3% hit rate, 1.8 avg touches (green)
  • Fib 38.2%: 66.7% hit rate, 2.1 avg touches (orange)
  • Fib 78.6%: 53.3% hit rate, 1.5 avg touches (orange)
  • Fib 100%: 46.7% hit rate, 1.2 avg touches (gray)

Harmonic Points:
  • Point C: 86.7% hit rate, 3.1 avg touches (green)
  • Point B: 60.0% hit rate, 1.9 avg touches (orange)
  • Point A: 40.0% hit rate, 1.3 avg touches (gray)

💡 Trading Tip: High hit rates (70%+) suggest reliable levels
for take-profit targets. High touch counts indicate oscillation zones.
```

### What You See (If No Statistics Yet):

```
─────────────────────────────────────────────────────────────
📊 Historical Statistics (From Backtesting):
─────────────────────────────────────────────────────────────
No historical data available yet. Run Fibonacci and Harmonic
Points analysis in backtesting to generate statistics.
```

### **Color Coding:**
- 🟢 **Green** (≥70%): Highly reliable level
- 🟠 **Orange** (50-69%): Moderately reliable
⚪ **Gray** (<50%): Less reliable

### **How to Generate Statistics:**

1. Load chart in main window (e.g., BTCUSDT 1d)
2. Click "Backtest" button
3. Run backtest with your parameters
4. Click "✓ Completed Successfully" category
5. Click "Fibonacci Level Analysis" button
6. Wait for analysis to complete
7. See message: `✅ Saved Fibonacci statistics for X pattern groups`
8. Now when you open Active Signals, patterns from BTCUSDT 1d will show statistics!

---

## Section 4: Price Alerts Control (Right Side)

### What You See:

A **table with checkboxes** to enable/disable specific price levels:

```
┌────────┬─────────────────┬──────────┬──────────────┐
│ Enable │ Type            │ Level    │ Price        │
├────────┼─────────────────┼──────────┼──────────────┤
│ [ ]    │ Fibonacci       │ Fib 0%   │ $61,500.00   │
│ [ ]    │ Fibonacci       │ Fib 23.6%│ $62,451.23   │
│ [✓]    │ Fibonacci       │ Fib 50%  │ $63,750.00   │ ← Enabled
│ [✓]    │ Fibonacci       │ Fib 61.8%│ $64,680.11   │ ← Enabled
│ [ ]    │ Fibonacci       │ Fib 100% │ $67,000.00   │
│ [✓]    │ Harmonic Point  │ Point C  │ $55,200.00   │ ← Enabled
│ [ ]    │ Harmonic Point  │ Point B  │ $59,500.00   │
└────────┴─────────────────┴──────────┴──────────────┘
```

### **How It Works:**

1. **Check a box** → Alert is **enabled** for that level
2. **Uncheck a box** → Alert is **disabled** for that level
3. Changes are **saved immediately** to the database
4. Pattern monitoring service checks these alerts every update cycle

### **What Happens When Price Hits an Enabled Alert:**

1. Price crosses the alert level (e.g., Fib 50% at $63,750)
2. System sends notification/alert (logged to alerts.log)
3. Alert is marked as **triggered** (✅ green background in table)
4. You see the alert in the system

### **Alert Lifecycle:**

```
Pattern Detected
    ↓
15 Price Alerts Created (all disabled by default)
    ↓
User Opens Active Signals Window
    ↓
User Selects Pattern
    ↓
User Enables 3 Alerts (e.g., Fib 50%, Fib 61.8%, Point C)
    ↓
Pattern Monitoring Service Checks Price Every Update
    ↓
Price Crosses Fib 50%
    ↓
Alert Triggered! ✅
    ↓
Notification Sent
    ↓
Alert Background Turns Green
```

### **Strategic Alert Selection (Using Historical Statistics):**

**Example Decision Process:**

You have a new Gartley pattern on BTCUSDT 1d.

**Step 1: Check Historical Stats**
```
Fib 50%: 80% hit rate ← Very high!
Fib 61.8%: 73% hit rate ← High!
Fib 100%: 46% hit rate ← Low
Point C: 86.7% hit rate ← Very high!
```

**Step 2: Enable High-Probability Alerts**
```
☑ Fib 50% (80% hit rate) - Set TP here
☑ Fib 61.8% (73% hit rate) - Set TP here
☑ Point C (86.7% hit rate) - Watch for reversal
☐ Fib 100% (46% hit rate) - Skip, low probability
```

**Step 3: Trading Plan**
- Entry: PRZ zone $61,000-$61,500
- Stop Loss: $60,500
- TP1: Fib 50% at $63,750 (80% chance of hitting)
- TP2: Fib 61.8% at $64,680 (73% chance of hitting)
- Watch Point C: If price revisits $55,200 (86.7% chance), possible re-entry

---

## Complete Workflow Example

### **Scenario: New Gartley Pattern Detected on BTCUSDT 1d**

#### **Step 1: Open Active Signals Window**
```
Tools → Active Trading Signals
```

#### **Step 2: Find Your Pattern**
Filter by:
- Symbol: BTCUSDT
- Timeframe: 1d
- Pattern: Gartley1

Click on the pattern row.

#### **Step 3: Review Signal Details (Left Side)**

**Pattern Information:**
```
BTCUSDT 1d - Gartley1 Bullish
Status: Detected
Current Price: $62,345
PRZ Zone: $61,000 - $61,500
Entry: $61,250
Stop Loss: $60,500
```

**Targets:**
```
TP1: $62,750
TP2: $64,125
TP3: $65,500
TP4: $66,875
TP5: $68,250
```

**Historical Statistics:**
```
📊 Based on 15 historical patterns:
  Fib 50%: 80% hit rate ✅
  Fib 61.8%: 73% hit rate ✅
  Point C: 86.7% hit rate ✅
```

#### **Step 4: Enable Strategic Alerts (Right Side)**

Based on statistics, enable high-probability levels:

```
[✓] Fib 50% at $63,750 (TP1 - 80% chance)
[✓] Fib 61.8% at $64,680 (TP2 - 73% chance)
[✓] Point C at $55,200 (Watch for reversal - 86% chance)
```

#### **Step 5: Monitor Pattern**

The system will:
1. Auto-update every 10 minutes
2. Check if price crosses any enabled alert
3. Send notification when alerts trigger
4. Update pattern status (Detected → Approaching → Entered → Completed)

#### **Step 6: Take Action When Alerts Trigger**

**Alert 1 Triggered: Fib 50% Hit**
```
✅ Fib 50% at $63,750 - Triggered
```
Action: Close 50% of position at TP1

**Alert 2 Triggered: Fib 61.8% Hit**
```
✅ Fib 61.8% at $64,680 - Triggered
```
Action: Close remaining 50% at TP2

**Pattern Completed!**

---

## Key Features Summary

### ✅ **What You Get:**

1. **Real-Time Monitoring**: All detected patterns in one place
2. **Detailed Analytics**: Complete pattern information, targets, statistics
3. **Historical Evidence**: See which levels hit most often (from backtesting)
4. **Custom Alerts**: Enable only the levels YOU want to monitor
5. **Smart Filtering**: Filter by symbol, timeframe, pattern, direction, status
6. **Auto-Refresh**: Updates every 30 seconds automatically
7. **Evidence-Based Trading**: Make decisions based on historical hit rates

### ✅ **What Makes It Powerful:**

1. **15 Price Alerts Per Pattern**: 12 Fibonacci + 3 Harmonic Points
2. **Pattern-Specific Statistics**: Different stats for each symbol/timeframe/pattern combo
3. **Color-Coded Reliability**: Green (70%+), Orange (50-69%), Gray (<50%)
4. **Triggered Alert Tracking**: See which levels already hit (green background)
5. **Flexible Alert Management**: Enable/disable any level with one click
6. **No Noise**: All alerts disabled by default - you choose what to monitor

---

## FAQs

### **Q: Why are all alerts disabled by default?**
**A:** To prevent alert spam. You should enable only high-probability levels based on statistics.

### **Q: How do I know which alerts to enable?**
**A:**
1. Check historical statistics (if available)
2. Enable levels with 70%+ hit rate (green)
3. Use high hit rate levels for TPs
4. Use high touch count levels for support/resistance zones

### **Q: What if I don't have historical statistics yet?**
**A:**
1. Run backtest for that symbol/timeframe
2. Click "Fibonacci Level Analysis" after backtest
3. Statistics will be saved to database
4. Open Active Signals again to see stats

### **Q: Can I enable all 15 alerts?**
**A:** Yes, but not recommended. You'll get too many notifications. Focus on high-probability levels.

### **Q: What happens when an alert triggers?**
**A:**
1. System logs the alert to `data/alerts.log`
2. Alert marked as triggered (✅) in UI
3. Table row background turns green
4. You can see it in Signal Details section

### **Q: Do alerts expire?**
**A:** Yes, when pattern reaches 161.8% Fibonacci extension (pattern fully completed).

### **Q: Can I re-enable a triggered alert?**
**A:** No. Once triggered, it stays triggered. Alerts are one-time notifications.

---

## Best Practices

### **1. Use Historical Statistics**
Don't guess - use data! Enable alerts for levels with 70%+ hit rate.

### **2. Start Conservative**
For new patterns without statistics, enable only:
- Fib 50% (common TP)
- Fib 61.8% (common TP)
- Point C (common reversal point)

### **3. Monitor Pattern Status**
- **Detected**: Pattern exists but price far from PRZ
- **Approaching**: Price within 5% of PRZ (prepare to trade)
- **Entered**: Price entered PRZ zone (consider entry)
- **Completed**: Pattern reached 161.8% (done)

### **4. Combine with Backtesting**
- Run backtests regularly
- Generate Fibonacci statistics
- Use stats to refine alert selection
- Better stats = better trading decisions

### **5. Review Triggered Alerts**
- Check which alerts triggered
- Compare with historical hit rates
- Validate your statistics are accurate
- Adjust future alert selections

---

## Summary

**Active Trading Signals Window = Your Pattern Trading Command Center**

**Left Side (Pattern Information):**
- Pattern details, prices, targets
- Historical statistics from backtesting
- Price alerts summary with status icons

**Right Side (Price Alerts Control):**
- Enable/disable specific Fibonacci and Harmonic Point alerts
- See which alerts are enabled (🔔) vs disabled (⭕) vs triggered (✅)
- Changes save immediately to database

**The Power:**
- Evidence-based alert selection (use historical statistics)
- Real-time monitoring with auto-refresh
- Flexible alert management (enable only what matters)
- Complete pattern lifecycle tracking

**The Workflow:**
1. Pattern detected → Signal created with 15 alerts (all disabled)
2. Open Active Signals → Select pattern → Review statistics
3. Enable high-probability alerts (70%+ hit rate)
4. Monitor pattern progress automatically
5. Get notified when enabled alerts trigger
6. Take profit at reliable levels with confidence!

---

**Last Updated:** 2025-10-07
**Status:** Fully Implemented ✅
