# Harmonic Pattern Detection System - User Guide

## Quick Start Guide

### Installation

1. **Clone or download the repository**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **For testing (optional)**:
```bash
pip install -r requirements-test.txt
```

4. **Run the application**:
```bash
python harmonic_patterns_qt.py
```

---

## Getting Started

### First Time Setup

1. **Load Data**:
   - Click "Load Data" or press `Ctrl+O`
   - Select a CSV file with OHLC data
   - Or download data: Enter symbol → Click "Download"

2. **Detect Patterns**:
   - Press `Ctrl+D` or click "Detect Patterns"
   - Wait for detection to complete
   - Browse detected patterns with arrows or `Ctrl+Left/Right`

3. **View Pattern Details**:
   - Click on a pattern in the list
   - View pattern points, ratios, and PRZ zone
   - Check quality score and validation status

---

## Main Interface

### Toolbar Buttons

| Button | Shortcut | Function |
|--------|----------|----------|
| Load Data | `Ctrl+O` | Load CSV data file |
| Download | - | Download data from Yahoo Finance |
| Detect | `Ctrl+D` | Detect harmonic patterns |
| Previous | `Ctrl+Left` | Previous pattern |
| Next | `Ctrl+Right` | Next pattern |
| Backtesting | `Ctrl+B` | Open backtesting window |
| Signals | `Ctrl+S` | View active signals |
| Watchlist | `Ctrl+W` | Manage watchlist |

### Keyboard Shortcuts

#### Detection
- `Ctrl+D`: Detect patterns
- `Ctrl+Shift+D`: Detect all pattern types

#### Navigation
- `Ctrl+Right`: Next pattern
- `Ctrl+Left`: Previous pattern
- `Ctrl+Home`: First pattern
- `Ctrl+End`: Last pattern

#### Windows
- `Ctrl+B`: Open backtesting
- `Ctrl+S`: Open signals window
- `Ctrl+W`: Open watchlist
- `Ctrl+H`: Show history

#### Chart
- `Ctrl++`: Zoom in
- `Ctrl+-`: Zoom out
- `Ctrl+0`: Reset zoom

#### Application
- `F1`: Show keyboard shortcuts
- `Ctrl+Q`: Quit application

---

## Features

### 1. Pattern Detection

**Supported Patterns**:
- Gartley (bullish/bearish)
- Butterfly (bullish/bearish)
- Bat (bullish/bearish)
- Crab (bullish/bearish)
- Shark (bullish/bearish)
- Cypher (bullish/bearish)
- Three Drives (bullish/bearish)
- ABCD (bullish/bearish)

**Detection Options**:
- Minimum quality score filter
- Pattern type selection
- Timeframe selection
- Formed vs unformed patterns

### 2. Pattern Validation

All patterns are validated using:
- **Price Containment**: Ensures proper structure
- **Ratio Validation**: Checks Fibonacci ratios
- **Structure Rules**: Alternating highs/lows

**Validation Status**:
- ✓ Valid: Pattern passes all checks
- ✗ Invalid: Pattern violates rules

### 3. Quality Scoring

Each pattern receives a score (0-100) based on:

1. **Ratio Precision (30 pts)**:
   - How close ratios match ideal Fibonacci levels
   - Perfect match = 30 pts

2. **Volume Confirmation (20 pts)**:
   - High volume at reversal (D point)
   - Low volume approaching PRZ
   - Good volume profile = 20 pts

3. **Trend Alignment (20 pts)**:
   - Bullish pattern in uptrend = 20 pts
   - Bearish pattern in downtrend = 20 pts
   - Counter-trend = 5 pts

4. **Price Cleanliness (15 pts)**:
   - Clean candles with small wicks
   - No violations between points
   - Perfect formation = 15 pts

5. **Time Symmetry (15 pts)**:
   - Balanced time between points
   - Low variance = 15 pts

**Score Interpretation**:
- 80-100: Excellent - Very high probability
- 60-79: Good - High probability
- 40-59: Fair - Moderate probability
- 0-39: Poor - Low probability

### 4. Multi-Timeframe Analysis

Analyze patterns across multiple timeframes simultaneously.

**How to Use**:
1. Load data for primary timeframe
2. Open multi-TF analysis tool
3. Select supporting timeframes (4h, 1d, etc.)
4. View confluence signals

**Confluence Score**:
- Based on number of supporting patterns
- Direction alignment bonus
- Higher timeframe bonus
- 0-100 scale

**Signal Strength**:
- Very Strong: 75+ confluence score
- Strong: 50-74
- Moderate: 25-49
- Weak: 0-24

### 5. Signal Management

Track detected patterns as tradeable signals.

**Signal Lifecycle**:
1. **Active**: Pattern detected, waiting for entry
2. **Monitoring**: Position entered, tracking
3. **Completed**: Target hit successfully
4. **Failed**: Stop loss hit
5. **Dismissed**: Manually cancelled

**Signal Features**:
- Entry price tracking
- Stop loss management
- Multiple take profit levels
- Real-time status updates
- PnL calculation

### 6. Alert System

Set price-based and pattern-based alerts.

**Alert Types**:
1. **Price Alerts**:
   - Above: Trigger when price goes above level
   - Below: Trigger when price goes below level
   - Cross Above: Price crosses from below to above
   - Cross Below: Price crosses from above to below

2. **Pattern Alerts**:
   - New pattern detected
   - Pattern enters PRZ zone
   - Pattern completion

**Alert Delivery**:
- On-screen notifications
- Log file (`data/alerts.log`)
- Console output
- Custom handlers (email, etc.)

### 7. Backtesting

Test pattern performance on historical data.

**Backtesting Process**:
1. Select symbol and timeframe
2. Set backtest period
3. Choose pattern types
4. Configure entry/exit rules
5. Run backtest
6. Analyze results

**Results Include**:
- Win rate
- Average profit/loss
- Risk/reward ratios
- Pattern-specific performance
- Detailed trade log
- Performance charts

**Export Options**:
- Excel spreadsheet
- CSV file
- PDF report

### 8. Watchlist

Monitor multiple symbols for patterns.

**Watchlist Features**:
- Add/remove symbols
- Auto-refresh intervals
- Pattern detection across all symbols
- Alert integration
- Status indicators

**How to Use**:
1. Press `Ctrl+W` to open watchlist
2. Add symbols to monitor
3. Set refresh interval
4. View detected patterns
5. Click to view details

### 9. Pattern History

Track pattern outcomes for performance analysis.

**Tracked Metrics**:
- Pattern success/failure rate
- Average profit/loss
- Maximum favorable excursion (MFE)
- Maximum adverse excursion (MAE)
- Quality score correlation

**Analysis Features**:
- Best performing patterns
- Worst performing patterns
- Quality vs success analysis
- Time-based performance
- Symbol-specific stats

---

## Configuration

### Settings File

Create `config.json` to customize settings:

```json
{
  "pattern_detection": {
    "min_bars": 50,
    "max_bars": 500,
    "retracement_tolerance": 5.0,
    "projection_tolerance": 10.0
  },
  "cache": {
    "enabled": true,
    "max_cache_size": 100,
    "ttl_seconds": 3600
  },
  "parallel_processing": {
    "enabled": true,
    "max_workers": 4
  },
  "ui": {
    "theme": "dark",
    "chart_style": "candle"
  }
}
```

### Performance Settings

**For Better Performance**:
- Enable caching: `cache.enabled = true`
- Enable parallel processing: `parallel_processing.enabled = true`
- Increase workers for more CPU cores
- Increase cache size for repeated analysis

**For Lower Memory Usage**:
- Reduce cache size
- Disable caching
- Use sequential processing
- Limit pattern types

---

## Data Format

### CSV Requirements

Your CSV file must contain:
- **Date/Time column**: For index
- **Open**: Opening price
- **High**: Highest price
- **Low**: Lowest price
- **Close**: Closing price
- **Volume** (optional): Trading volume

**Example CSV**:
```csv
Date,Open,High,Low,Close,Volume
2024-01-01 00:00:00,50000,51000,49500,50500,1000000
2024-01-01 01:00:00,50500,51500,50000,51000,1200000
```

### Supported Timeframes

- **Intraday**: 1m, 5m, 15m, 30m, 1h, 4h, 12h
- **Daily and Higher**: 1d, 1w, 1M

### Data Sources

1. **Manual CSV**: Load your own OHLC data
2. **Yahoo Finance**: Built-in downloader
3. **Exchange Export**: Export from trading platform
4. **API Integration**: Use data service for custom sources

---

## Troubleshooting

### Common Issues

**1. No patterns detected**:
- Check data has enough bars (minimum 50)
- Verify data quality (no gaps)
- Try lower quality score threshold
- Ensure correct timeframe

**2. Slow performance**:
- Enable caching in settings
- Enable parallel processing
- Reduce detection window size
- Optimize database (run `optimize_database.py`)

**3. Database errors**:
- Check disk space
- Verify database permissions
- Run database optimization
- Delete and recreate if corrupted

**4. Pattern validation fails**:
- Check for data gaps
- Verify OHLC relationship (High ≥ Open, Close; Low ≤ Open, Close)
- Look for missing extremum points

### Log Files

Check log files for detailed error information:
- `logs/harmonic_patterns.log`: Main application log
- `logs/performance.log`: Performance metrics
- `data/alerts.log`: Alert history
- `pattern_debug.log`: Pattern detection debug

### Getting Help

1. Check `API_DOCUMENTATION.md` for technical details
2. Review `IMPROVEMENTS_SUMMARY.md` for recent changes
3. Run tests: `pytest tests/` to verify installation
4. Check GitHub issues for known problems

---

## Advanced Usage

### Custom Pattern Detection

Implement your own pattern detector:

```python
from services import PatternDetectionService

def my_custom_pattern_detector(extremum_points, df):
    patterns = []
    # Your detection logic
    return patterns

service = PatternDetectionService()
detection_methods = {
    'custom': my_custom_pattern_detector
}

patterns = service.detect_patterns(
    df, extremum, ['custom'], detection_methods
)
```

### Custom Alert Handlers

Create custom alert delivery:

```python
from services import AlertService

def email_handler(alert):
    send_email(
        to='trader@example.com',
        subject=f"Alert: {alert['symbol']}",
        body=alert['message']
    )

alert_service = AlertService()
alert_service.register_alert_handler(email_handler)
```

### Automated Trading Integration

Connect to trading platform:

```python
from services import SignalService

signal_service = SignalService()

# Monitor for new signals
active_signals = signal_service.get_active_signals()

for signal in active_signals:
    if should_enter_trade(signal):
        # Place order via your broker API
        place_order(
            symbol=signal['symbol'],
            side='buy' if signal['direction'] == 'bullish' else 'sell',
            entry=signal['entry_price'],
            stop_loss=signal['stop_loss'],
            take_profit=signal['take_profit']
        )
```

---

## Best Practices

### Pattern Selection

1. **Focus on high-quality patterns**: Use minimum score of 60+
2. **Prefer confluence**: Look for multi-timeframe alignment
3. **Consider trend**: Trade with higher timeframe trend
4. **Validate manually**: Always visually confirm patterns

### Risk Management

1. **Always use stop loss**: Never trade without protection
2. **Position sizing**: Risk 1-2% per trade
3. **Take profit levels**: Use multiple TPs (50%, 100%, 161.8%)
4. **Track performance**: Review historical pattern success

### System Usage

1. **Regular data updates**: Keep data current
2. **Database optimization**: Run monthly
3. **Review logs**: Check for errors periodically
4. **Backup data**: Save signals and history databases
5. **Test changes**: Use backtesting before live trading

---

## Tips and Tricks

### Keyboard Efficiency

- Use `Ctrl+D` for quick pattern detection
- Navigate patterns with arrow keys
- Press `F1` anytime to see shortcuts
- Use `Ctrl+B` to quickly backtest current pattern

### Pattern Analysis

- Check quality score breakdown to understand weaknesses
- Compare similar patterns across timeframes
- Look for time symmetry in high-quality patterns
- Verify volume at D point for confirmation

### Performance Optimization

- Close unused windows to save memory
- Clear cache periodically if memory limited
- Use specific pattern types instead of "All"
- Limit historical data to necessary period

### Multi-Monitor Setup

- Main chart on primary monitor
- Backtesting on secondary monitor
- Watchlist on tertiary monitor
- Signals window floating

---

## Appendix

### Pattern Cheat Sheet

**Gartley**:
- AB: 61.8% of XA
- BC: 38.2-88.6% of AB
- CD: 127.2-161.8% of BC
- AD: 78.6% of XA

**Butterfly**:
- AB: 78.6% of XA
- BC: 38.2-88.6% of AB
- CD: 161.8-224% of BC
- AD: 127-161.8% of XA

**Bat**:
- AB: 38.2-50% of XA
- BC: 38.2-88.6% of AB
- CD: 161.8-261.8% of BC
- AD: 88.6% of XA

**Crab**:
- AB: 38.2-61.8% of XA
- BC: 38.2-88.6% of AB
- CD: 224-361.8% of BC
- AD: 161.8% of XA

### Fibonacci Levels

Common retracement levels:
- 23.6%, 38.2%, 50%, 61.8%, 78.6%

Common projection levels:
- 127.2%, 141.4%, 161.8%, 200%, 224%, 261.8%

### Color Coding

- **Green**: Bullish patterns
- **Red**: Bearish patterns
- **Blue**: PRZ zones
- **Yellow**: Pattern points
- **Gray**: Inactive/dismissed

---

## Version History

### Version 2.0 (Current)
- Multi-timeframe analysis
- Pattern quality scoring
- Service layer architecture
- Comprehensive testing
- Performance optimizations

### Version 1.0
- Initial release
- Basic pattern detection
- Simple backtesting
- Manual validation

---

## Quick Reference Card

| Task | Action |
|------|--------|
| Load Data | `Ctrl+O` |
| Detect Patterns | `Ctrl+D` |
| Next Pattern | `Ctrl+Right` |
| Previous Pattern | `Ctrl+Left` |
| Backtest | `Ctrl+B` |
| View Signals | `Ctrl+S` |
| Watchlist | `Ctrl+W` |
| Zoom In | `Ctrl++` |
| Zoom Out | `Ctrl+-` |
| Help | `F1` |
| Quit | `Ctrl+Q` |

---

For detailed API documentation, see `API_DOCUMENTATION.md`
