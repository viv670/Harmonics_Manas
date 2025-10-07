# Pattern Monitoring System - Setup Guide

## Overview

The Pattern Monitoring System provides **automated pattern detection and real-time alerts** for harmonic patterns. After data updates from the auto-updater, the system automatically:

1. ✅ Detects new formed ABCD and XABCD patterns
2. ⚡ Tracks price movement toward PRZ zones
3. 🔔 Sends desktop notifications and sound alerts
4. 💾 Stores signals in SQLite database for tracking
5. 📊 Displays active signals in GUI

---

## Components

### 1. **signal_database.py** - Signal Storage
- SQLite database for persistent signal storage
- Stores pattern details, PRZ zones, price levels, alerts sent
- Status tracking: `detected` → `approaching` → `entered`
- Methods for adding, updating, querying signals

**Database Schema:**
```
signals table:
  - signal_id (unique identifier)
  - symbol, timeframe, pattern_type, pattern_name, direction
  - prz_min, prz_max, current_price, distance_to_prz_pct
  - entry_price, stop_loss, targets
  - status (detected/approaching/entered/completed/invalidated)
  - alerts_sent_json (tracks which alerts already sent)
  - detected_at, last_updated
  - points_json, d_lines_json
```

**Database Location:** `data/signals.db`

---

### 2. **alert_manager.py** - Desktop Notifications & Sound

Sends alerts through multiple channels:

**Desktop Notifications:**
- Windows 10/11 toast notifications
- Shows pattern name, symbol, timeframe, PRZ info
- 10-second display duration
- Requires: `win10toast` package

**Sound Alerts:**
- System beep using `winsound`
- Different beep patterns for different alert types:
  - **Detected:** Single beep (1000 Hz, 200ms)
  - **Approaching:** Double beep (1200 Hz, 150ms each)
  - **Entered:** Triple beep (1500 Hz, 200ms each) - **MOST URGENT**

**Alert Logging:**
- All alerts logged to `data/alerts.log`
- Format: `timestamp | alert_type | symbol | pattern | details`

**Alert Types:**
1. **Detected** - New pattern found
2. **Approaching** - Price within 5% of PRZ
3. **Entered** - Price inside PRZ zone (READY TO TRADE!)

---

### 3. **pattern_monitor_service.py** - Core Monitoring Logic

**PatternMonitorService** (Single symbol/timeframe):
- Detects formed patterns using `detect_xabcd_patterns()` and `detect_strict_abcd_patterns()`
- Calculates distance to PRZ (percentage)
- Determines status based on price position
- Updates signal database
- Sends alerts when status changes
- Tracks which alerts already sent (no duplicates)

**MultiSymbolMonitor** (Multiple symbol/timeframe pairs):
- Manages monitoring for entire watchlist
- Shares single database and alert manager
- Routes updates to appropriate monitor

**Status Logic:**
```python
if price inside PRZ:
    status = 'entered'  # 🎯 READY TO TRADE
elif distance_to_prz <= 5%:
    status = 'approaching'  # ⚡ Getting close
else:
    status = 'detected'  # 🔍 Monitoring
```

---

### 4. **auto_update_scheduler.py** - Integration Point

**Modified Functions:**
- `__init__()`: Added `enable_pattern_monitoring` parameter (default: `True`)
- `_update_chart()`: Triggers pattern monitoring after successful data update
- `_run_pattern_monitoring()`: Loads updated data, runs pattern detection, logs results

**New Methods:**
- `enable_pattern_monitoring()`: Enable monitoring
- `disable_pattern_monitoring()`: Disable monitoring
- `get_active_signals()`: Get all active signals from database

**Workflow:**
```
Data Update → Pattern Detection → Status Check → Alert Trigger
```

---

### 5. **active_signals_window.py** - GUI Display

**Features:**
- Real-time table of active signals (auto-refreshes every 10 seconds)
- Filters by status and symbol
- Detailed signal information panel
- Manual signal invalidation
- Status color coding:
  - **Detected:** Gray
  - **Approaching:** Orange
  - **Entered:** Green

**Keyboard Shortcuts:**
- `Ctrl+A`: Open Active Signals window (from main GUI)

**Columns:**
- Symbol, Timeframe, Pattern Name, Direction
- Status, Current Price, PRZ Min/Max
- Distance %, Detected Time, Alerts Sent

---

## Installation & Setup

### 1. Install Dependencies

```bash
pip install win10toast
```

**Note:** `winsound` is built into Python on Windows (no installation needed)

### 2. Verify Installation

Run the test scripts to verify each component:

```bash
# Test signal database
python signal_database.py

# Test alert manager (will show notifications and beeps)
python alert_manager.py

# Test pattern monitor
python pattern_monitor_service.py

# Test active signals GUI
python active_signals_window.py
```

### 3. Enable in Main Application

Pattern monitoring is **enabled by default** when auto-updater starts.

To manually control:

```python
# In main GUI or script
auto_updater.enable_pattern_monitoring()   # Enable
auto_updater.disable_pattern_monitoring()  # Disable
```

---

## Usage

### Automatic Monitoring (Recommended)

1. **Add charts to watchlist** via Watchlist Manager
2. **Enable auto-update** for charts you want to monitor
3. **Pattern monitoring runs automatically** after each data update
4. **Receive alerts** when patterns detected, approaching PRZ, or entered PRZ

### Manual Monitoring

```python
from pattern_monitor_service import PatternMonitorService
import pandas as pd

# Load data
df = pd.read_csv('data/btcusdt_4h.csv')
df['Time'] = pd.to_datetime(df['Time'])
df.set_index('Time', inplace=True)

# Create monitor
monitor = PatternMonitorService(
    symbol='BTCUSDT',
    timeframe='4h',
    approaching_threshold_pct=5.0  # Alert when within 5% of PRZ
)

# Process data
results = monitor.process_new_data(df)

print(f"New patterns: {results['new_patterns_detected']}")
print(f"Patterns approaching: {results['patterns_approaching']}")
print(f"Patterns entered: {results['patterns_entered']}")
print(f"Alerts sent: {results['alerts_sent']}")
```

### View Active Signals in GUI

1. Open main application
2. Click **Tools → 🔔 Active Signals** (or press `Ctrl+A`)
3. View all active signals, filter by status/symbol
4. Click a signal to see detailed information
5. Manually invalidate signals if needed

---

## Configuration

### Alert Settings

Edit in `alert_manager.py` or create custom `AlertConfig`:

```python
from alert_manager import AlertManager, AlertConfig

config = AlertConfig(
    desktop_notifications=True,   # Enable/disable desktop notifications
    sound_alerts=True,             # Enable/disable sound beeps
    log_alerts=True,               # Enable/disable file logging
    log_file="data/alerts.log"    # Alert log file path
)

alert_manager = AlertManager(config)
```

### Monitoring Settings

```python
monitor = PatternMonitorService(
    symbol='BTCUSDT',
    timeframe='4h',
    extremum_length=1,                # Extremum detection length
    approaching_threshold_pct=5.0     # Alert when within 5% of PRZ
)
```

### Database Location

Default: `data/signals.db`

To change:
```python
from signal_database import SignalDatabase

db = SignalDatabase(db_path="custom/path/signals.db")
```

---

## Alert Behavior

### Alert Types & Triggers

| Alert Type | Trigger | Desktop Notification | Sound Pattern | Urgency |
|------------|---------|---------------------|---------------|---------|
| **Detected** | New pattern found | ✅ | 1 beep | Low |
| **Approaching** | Distance ≤ 5% to PRZ | ✅ | 2 beeps | Medium |
| **Entered** | Price inside PRZ | ✅ | 3 beeps | **HIGH** |

### Alert Deduplication

- System tracks which alerts already sent per signal
- No duplicate alerts for same signal/alert_type combination
- Stored in `alerts_sent_json` field in database

### Example Alert Flow

```
1. New pattern detected
   → Alert: "🎯 Pattern Detected: BTCUSDT"
   → 1 beep

2. Price moves closer (within 5% of PRZ)
   → Alert: "⚡ Approaching PRZ: BTCUSDT"
   → 2 beeps

3. Price enters PRZ zone
   → Alert: "🎯 ENTERED PRZ: BTCUSDT - ⚠️ READY TO TRADE!"
   → 3 beeps (URGENT)
```

---

## Database Maintenance

### Cleanup Old Signals

Automatically remove completed/invalidated signals older than 30 days:

```python
# From auto-updater
auto_updater.pattern_monitor.cleanup_all_old_signals(days=30)

# From individual monitor
monitor.cleanup_old_signals(days=30)
```

### Query Signals

```python
from signal_database import SignalDatabase

db = SignalDatabase()

# Get all active signals
active = db.get_active_signals()

# Get signals for specific symbol
btc_signals = db.get_signals_by_symbol('BTCUSDT', active_only=True)

# Get signals by status
entered = db.get_signals_by_status('entered')
approaching = db.get_signals_by_status('approaching')
detected = db.get_signals_by_status('detected')
```

---

## Troubleshooting

### No Alerts Appearing

1. **Check if pattern monitoring is enabled:**
   ```python
   print(auto_updater.pattern_monitoring_enabled)
   ```

2. **Check if patterns are being detected:**
   - Open Active Signals window (`Ctrl+A`)
   - Check database: `data/signals.db`

3. **Check alert manager initialization:**
   - Look for "⚠️ win10toast not available" in console
   - Install: `pip install win10toast`

4. **Check alert log:**
   - Open `data/alerts.log`
   - Verify alerts are being logged

### Duplicate Alerts

- Should not happen - alerts are deduplicated by `alerts_sent_json`
- If occurring, check `alerts_sent_json` field in database

### Pattern Monitoring Not Running

1. **Check auto-updater initialization:**
   ```python
   print(auto_updater.pattern_monitor)
   # Should NOT be None
   ```

2. **Check watchlist:**
   - Pattern monitor initialized from watchlist
   - Add charts to watchlist via Watchlist Manager

3. **Check for errors in console:**
   - Look for "⚠️ Pattern monitoring error"
   - Check full traceback

### Sound Not Playing

- Windows only feature
- Uses `winsound` module (built-in)
- Check if `sound_alerts=True` in AlertConfig
- Check Windows sound settings

---

## Future Enhancements (Placeholders)

### Pattern Scoring (Backtest-Driven)

**Current:** Placeholder score of 50 for all patterns

**Future Implementation:**
- Calculate success rate per pattern type from backtesting results
- Score patterns based on:
  - Success rate for that pattern type on that symbol
  - PRZ quality (tight vs. wide zones)
  - Pattern size and timeframe
  - Historical performance
- Filter alerts to only high-quality patterns (score > 70)

**User's Note:**
> "To solve this problem only, I have created backtesting tab, and the idea is that we are going to test and based on the results we will know what is working and what is not working for that individual coin."

### Exchange Integration

**Future:** Automatic trade placement based on alerts
- Currently: Manual trading based on alerts
- Future: Connect to exchange API, auto-place orders on PRZ entry

---

## File Summary

| File | Purpose | Key Functions |
|------|---------|---------------|
| `signal_database.py` | Signal storage | `add_signal()`, `update_signal()`, `get_active_signals()` |
| `alert_manager.py` | Notifications & sound | `send_alert()`, `_send_desktop_notification()`, `_play_alert_sound()` |
| `pattern_monitor_service.py` | Core monitoring | `process_new_data()`, `_detect_patterns()`, `_determine_status()` |
| `auto_update_scheduler.py` | Integration | `_run_pattern_monitoring()`, `enable_pattern_monitoring()` |
| `active_signals_window.py` | GUI display | `refreshSignals()`, `updateTable()`, `invalidateSignal()` |

---

## Support

For issues or questions:
1. Check console output for detailed error messages
2. Check `data/alerts.log` for alert history
3. Check `pattern_debug.log` for pattern detection details
4. Review PENDING_ISSUES.md for known issues

---

**Version:** 1.0 (Basic Version)
**Date:** 2025-10-06
**Status:** ✅ Fully Implemented - Basic Version Complete
