# Watchlist Auto-Update System

## Overview

The Watchlist Auto-Update System automatically keeps your chart data up-to-date based on each chart's timeframe. Once you download a chart, it's automatically added to the watchlist and will update itself without manual intervention.

## How It Works

### 1. Automatic Watchlist Addition
When you download data using the "Download from Binance" feature:
- The chart is **automatically added** to the watchlist
- A file is created: `data/watchlist.json`
- The chart's details are saved (symbol, timeframe, file path, last update time)

### 2. Smart Update Scheduling
Each chart knows when it needs updating based on its timeframe:
- **1m chart** → Updates every 1 minute
- **5m chart** → Updates every 5 minutes
- **1h chart** → Updates every 1 hour
- **4h chart** → Updates every 4 hours
- **1d chart** → Updates every 1 day
- **Custom timeframes** → Updates based on parsed timeframe (e.g., "2d" = every 2 days)

### 3. Background Auto-Updates
- The system checks every **5 minutes** if any charts need updating
- Only downloads **new candles** since last update (efficient!)
- Appends new data to existing CSV files
- Updates happen silently in the background
- Status messages appear in the status bar

## Files Created

### watchlist.json
Located in: `data/watchlist.json`

Example content:
```json
{
  "charts": [
    {
      "symbol": "BTCUSDT",
      "timeframe": "1d",
      "last_update": "2025-10-04T10:30:00",
      "next_update": "2025-10-05T10:30:00",
      "file_path": "C:\\Users\\vivek\\Desktop\\Harmonics_Manas\\btcusdt_1d.csv",
      "enabled": true
    },
    {
      "symbol": "ETHUSDT",
      "timeframe": "4h",
      "last_update": "2025-10-04T08:00:00",
      "next_update": "2025-10-04T12:00:00",
      "file_path": "C:\\Users\\vivek\\Desktop\\Harmonics_Manas\\ethusdt_4h.csv",
      "enabled": true
    }
  ]
}
```

## Using the Watchlist Manager (Programmatically)

### Add a Chart
```python
from watchlist_manager import WatchlistManager

watchlist = WatchlistManager()
watchlist.add_chart(
    symbol="BTCUSDT",
    timeframe="1d",
    file_path="btcusdt_1d.csv",
    enabled=True
)
```

### Remove a Chart
```python
watchlist.remove_chart("BTCUSDT", "1d")
```

### Enable/Disable a Chart
```python
# Disable updates for a specific chart
watchlist.enable_chart("BTCUSDT", "1d", enabled=False)

# Re-enable updates
watchlist.enable_chart("BTCUSDT", "1d", enabled=True)
```

### Get Charts Needing Update
```python
charts = watchlist.get_charts_needing_update()
for chart in charts:
    print(f"{chart.symbol} {chart.timeframe} needs update")
```

### Get Watchlist Summary
```python
summary = watchlist.get_status_summary()
print(f"Total charts: {summary['total_charts']}")
print(f"Enabled: {summary['enabled_charts']}")
print(f"Needs update: {summary['needs_update']}")
```

## Using the Auto-Update Scheduler

### Manual Update Triggers
```python
from auto_update_scheduler import AutoUpdateScheduler

# Update specific chart now
scheduler.update_now(symbol="BTCUSDT", timeframe="1d")

# Update all charts now
scheduler.update_now()
```

### Pause/Resume Updates
```python
# Pause automatic updates (e.g., during backtesting)
scheduler.pause()

# Resume automatic updates
scheduler.resume()
```

### Get Scheduler Statistics
```python
stats = scheduler.get_stats()
print(f"Running: {stats['running']}")
print(f"Total updates: {stats['total_updates']}")
print(f"Failed updates: {stats['failed_updates']}")
print(f"Last check: {stats['last_check']}")
```

## Current Implementation Status

✅ **Completed:**
1. Watchlist Manager - tracks all charts with metadata
2. Auto-Update Scheduler - background service with 5-min check interval
3. Automatic integration - charts auto-added when downloaded
4. Smart update logic - only fetches new candles
5. Graceful shutdown - stops cleanly when app closes

## Benefits

### 1. Always Up-To-Date Data
- No need to manually re-download
- Charts stay current automatically
- Perfect for live trading analysis

### 2. Efficient Updates
- Only downloads new candles (not full history)
- Minimal bandwidth usage
- Fast updates even for multiple charts

### 3. Multiple Timeframes
- Track different symbols at different timeframes
- Each updates on its own schedule
- Example: BTC 1d, ETH 4h, SOL 1h all updating independently

### 4. Zero Configuration
- Works automatically after downloading data
- No manual watchlist management needed
- Just download and forget!

## Example Workflow

1. **Download Charts:**
   ```
   Download BTCUSDT 1d  → Auto-added to watchlist
   Download ETHUSDT 4h  → Auto-added to watchlist
   Download SOLUSDT 1h  → Auto-added to watchlist
   ```

2. **Automatic Updates:**
   - Every 5 minutes, scheduler checks if updates needed
   - SOLUSDT updates hourly (1h timeframe)
   - ETHUSDT updates every 4 hours (4h timeframe)
   - BTCUSDT updates daily (1d timeframe)

3. **Keep Working:**
   - Continue your analysis
   - Run backtests
   - Detect patterns
   - Data stays fresh automatically!

## Troubleshooting

### Charts Not Updating?
1. Check `data/watchlist.json` exists
2. Verify chart is enabled (`"enabled": true`)
3. Check console for error messages
4. Ensure internet connection is active

### Want to Stop Auto-Updates?
```python
# Stop the scheduler
auto_updater.stop()

# Or pause temporarily
auto_updater.pause()
```

### Manual Force Update?
```python
# Update specific chart immediately
auto_updater.update_now("BTCUSDT", "1d")

# Or update all charts
auto_updater.update_now()
```

## Future Enhancements (Optional)

Future features that could be added:
- GUI panel to view/manage watchlist
- Manual enable/disable buttons per chart
- Update history log
- Configurable check interval
- Email/notification on failed updates
- Retry logic for failed updates

## Technical Details

### Thread Safety
- Watchlist uses threading locks for safe concurrent access
- Scheduler runs in background daemon thread
- Properly cleaned up on app closure

### Data Integrity
- New data appended to existing CSV
- Duplicates removed based on timestamp
- Data sorted chronologically after each update

### Error Handling
- Failed updates logged but don't stop scheduler
- Statistics track success/failure rates
- Graceful degradation if Binance API unavailable

---

**Status:** Fully Implemented ✅
**Version:** 1.0
**Last Updated:** October 4, 2025
