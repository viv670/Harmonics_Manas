# Harmonic Pattern Detection System - API Documentation

## Table of Contents

1. [Overview](#overview)
2. [Core Modules](#core-modules)
3. [Service Layer](#service-layer)
4. [Pattern Detection](#pattern-detection)
5. [Data Management](#data-management)
6. [Signal Management](#signal-management)
7. [Alert System](#alert-system)
8. [Multi-Timeframe Analysis](#multi-timeframe-analysis)
9. [Testing](#testing)
10. [Configuration](#configuration)
11. [Examples](#examples)

---

## Overview

The Harmonic Pattern Detection System is a comprehensive trading analysis tool that detects, validates, scores, and tracks harmonic patterns across multiple timeframes.

### Key Features

- **Pattern Detection**: Automatic detection of 8+ harmonic patterns
- **Validation**: Price containment and structure validation
- **Scoring**: Multi-factor quality scoring (0-100 scale)
- **Caching**: Intelligent pattern caching for performance
- **Parallel Processing**: Concurrent pattern detection
- **Multi-Timeframe**: Cross-timeframe pattern analysis
- **Signal Management**: Complete signal lifecycle tracking
- **Historical Analysis**: Pattern performance tracking
- **Alert System**: Price and pattern-based alerts

---

## Core Modules

### Pattern Cache (`pattern_cache.py`)

Intelligent caching system for pattern detection results.

#### API Reference

```python
from pattern_cache import get_pattern_cache

# Get singleton cache instance
cache = get_pattern_cache()

# Store patterns in cache
cache.set(extremum_points, df, 'pattern_type', patterns, **params)

# Retrieve from cache
cached_patterns = cache.get(extremum_points, df, 'pattern_type', **params)

# Get cache statistics
stats = cache.get_stats()
# Returns: {'hits': int, 'misses': int, 'hit_rate': float, 'size': int}

# Clear cache
cache.clear()
```

**Configuration**:
- `max_size`: Maximum cache entries (default: 100)
- `ttl`: Time-to-live in seconds (default: 3600)

---

### Parallel Pattern Detector (`parallel_pattern_detector.py`)

Concurrent pattern detection for improved performance.

#### API Reference

```python
from parallel_pattern_detector import detect_patterns_parallel, ParallelPatternDetector

# Quick function (uses default 4 workers)
results = detect_patterns_parallel(extremum_points, df, detection_methods)

# Full API with custom workers
detector = ParallelPatternDetector(max_workers=8)

detection_methods = {
    'gartley': detect_gartley_function,
    'butterfly': detect_butterfly_function,
}

results = detector.detect_all_patterns(
    extremum_points,
    df,
    detection_methods,
    progress_callback=lambda current, total: print(f"{current}/{total}")
)

# Results format: {'gartley': [...], 'butterfly': [...]}
```

**Performance**: 4x speedup with 4 workers on typical workloads.

---

### Pattern Validators (`pattern_validators.py`)

Unified validation logic for all pattern types.

#### API Reference

```python
from pattern_validators import PriceContainmentValidator

# Validate specific pattern type
is_valid = PriceContainmentValidator.validate_bullish_abcd(
    df, a_idx, b_idx, c_idx, a_price, b_price, c_price
)

# Auto-detect and validate
is_valid = PriceContainmentValidator.validate_pattern(pattern, df)

# Check post-D validation
is_valid = PriceContainmentValidator.validate_bullish_abcd(
    df, a_idx, b_idx, c_idx, a_price, b_price, c_price,
    d_price=d_price, check_post_c=True
)
```

**Validation Rules**:
- **Bullish ABCD**: A > C > B, no high exceeds A/C, no low breaks B
- **Bearish ABCD**: A < C < B, no low breaks A/C, no high exceeds B
- **XABCD patterns**: Additional X-point validation

---

### Pattern Scoring (`pattern_scoring.py`)

Multi-factor quality scoring system.

#### API Reference

```python
from pattern_scoring import PatternStrengthScorer, filter_patterns_by_score

scorer = PatternStrengthScorer()

# Score single pattern
score = scorer.score_pattern(pattern, df)  # Returns 0-100

# Get detailed breakdown
breakdown = scorer.get_score_breakdown(pattern, df)
# Returns: {
#     'ratio_precision': float,      # 0-30 pts
#     'volume_confirmation': float,  # 0-20 pts
#     'trend_alignment': float,      # 0-20 pts
#     'price_cleanliness': float,    # 0-15 pts
#     'time_symmetry': float,        # 0-15 pts
#     'total': int                   # 0-100
# }

# Filter patterns by minimum score
high_quality = filter_patterns_by_score(patterns, df, min_score=70)
```

**Scoring Components**:
1. **Ratio Precision** (30 pts): Closeness to ideal Fibonacci ratios
2. **Volume Confirmation** (20 pts): Volume profile at key points
3. **Trend Alignment** (20 pts): Alignment with higher TF trend
4. **Price Cleanliness** (15 pts): Clean formation quality
5. **Time Symmetry** (15 pts): Balanced timing between points

---

## Service Layer

### Pattern Detection Service (`services/pattern_service.py`)

Business logic for pattern detection operations.

#### API Reference

```python
from services import PatternDetectionService

service = PatternDetectionService(use_cache=True, use_parallel=True)

# Detect patterns with all features
patterns = service.detect_patterns(
    df=ohlc_data,
    extremum_points=extremum,
    pattern_types=['gartley', 'butterfly', 'bat'],
    detection_methods=detection_funcs,
    min_quality_score=60,
    validate=True
)

# Find best single pattern
best = service.find_best_pattern(
    df, extremum, detection_methods,
    direction='bullish'  # Optional filter
)

# Get pattern statistics
stats = service.get_pattern_statistics(patterns)
# Returns: {
#     'total': int,
#     'by_type': dict,
#     'by_direction': dict,
#     'avg_score': float
# }

# Cache management
service.clear_cache()
cache_stats = service.get_cache_stats()
```

---

### Data Service (`services/data_service.py`)

Data loading, validation, and management.

#### API Reference

```python
from services import DataService

service = DataService(data_dir='data')

# Load from CSV
df = service.load_csv('btcusdt_1h.csv', validate=True)

# Download from Yahoo Finance
df = service.download_data(
    symbol='BTCUSDT',
    interval='1h',    # 1m, 5m, 15m, 1h, 4h, 1d
    period='1mo',     # 1d, 5d, 1mo, 3mo, 1y
    save=True         # Save to CSV
)

# Get latest N bars
df = service.get_latest_data('BTCUSDT', interval='1h', bars=100)

# Resample to different timeframe
df_4h = service.resample_data(df_1h, '4h')

# Add technical indicators
df = service.calculate_indicators(df, ['SMA_20', 'SMA_50', 'EMA_20', 'RSI'])

# Get data info
info = service.get_data_info(df)
# Returns: {
#     'rows': int,
#     'columns': list,
#     'start_date': datetime,
#     'end_date': datetime,
#     'missing_values': dict,
#     'price_range': dict
# }
```

---

### Signal Service (`services/signal_service.py`)

Signal lifecycle management.

#### API Reference

```python
from services import SignalService

service = SignalService(db_path='data/signals.db')

# Create signal
signal_id = service.create_signal(
    symbol='BTCUSDT',
    timeframe='1h',
    pattern=pattern_dict,
    entry_price=50000,
    stop_loss=49000,
    take_profit=52000
)

# Get signal by ID
signal = service.get_signal(signal_id)

# Get active signals
active = service.get_active_signals(symbol='BTCUSDT', timeframe='1h')

# Update status
service.update_signal_status(signal_id, 'completed', notes='TP hit')

# Query by pattern
signals = service.get_signals_by_pattern('Gartley_bull', direction='bullish', limit=100)

# Get statistics
stats = service.get_signal_statistics()
# Returns: {
#     'total': int,
#     'by_status': dict,
#     'by_pattern': dict,
#     'by_direction': dict,
#     'avg_quality_score': float
# }

# Cleanup old signals
service.cleanup_old_signals(days=30)
```

---

### Alert Service (`services/alert_service.py`)

Price and pattern-based alerts.

#### API Reference

```python
from services import AlertService, console_alert_handler, log_alert_handler

service = AlertService(alert_log_path='data/alerts.log')

# Register alert handlers
service.register_alert_handler(console_alert_handler)
service.register_alert_handler(log_alert_handler)

# Create custom handler
def email_alert_handler(alert):
    send_email(alert['message'])

service.register_alert_handler(email_alert_handler)

# Create alert
alert = service.create_alert(
    alert_type='price',
    symbol='BTCUSDT',
    condition='above',  # above, below, cross_above, cross_below
    target_price=50000,
    message='BTC above 50k!',
    metadata={'timeframe': '1h'}
)

# Check alerts (call on each price update)
triggered = service.check_alerts('BTCUSDT', current_price=51000, previous_price=49000)

# Get active alerts
active = service.get_active_alerts(symbol='BTCUSDT')

# Cancel alert
service.cancel_alert(alert_id)

# Get history
history = service.get_alert_history(limit=100)

# Cleanup
service.cleanup_old_alerts()
```

---

## Multi-Timeframe Analysis

### Multi-Timeframe Analyzer (`multi_timeframe_analysis.py`)

Cross-timeframe pattern detection and confluence analysis.

#### API Reference

```python
from multi_timeframe_analysis import MultiTimeframeAnalyzer, analyze_symbol_multi_tf

# Full API
analyzer = MultiTimeframeAnalyzer()

# Load data for multiple timeframes
analyzer.load_timeframe_data(
    symbol='BTCUSDT',
    timeframes=['1h', '4h', '1d'],
    period='3mo'
)

# Detect patterns across all timeframes
analyzer.detect_patterns_multi_tf(
    symbol='BTCUSDT',
    timeframes=['1h', '4h', '1d'],
    detection_func=my_detection_function
)

# Find confluence signals
signals = analyzer.find_confluence_signals(
    primary_tf='1h',
    supporting_tfs=['4h', '1d']
)

# Each signal contains:
# - primary_pattern: Main pattern
# - supporting_patterns: Patterns on higher TFs
# - confluence_score: 0-100 score
# - higher_tf_bias: bullish/bearish/neutral
# - signal_strength: weak/moderate/strong/very_strong

# Generate report
report = analyzer.generate_report(signals)
print(report)

# Quick convenience function
signals = analyze_symbol_multi_tf(
    symbol='BTCUSDT',
    primary_tf='1h',
    supporting_tfs=['4h', '1d'],
    detection_func=detect_function
)
```

**Confluence Scoring**:
- Base score: 20 pts per supporting pattern (max 60)
- Direction alignment: +20 pts
- Higher TF patterns: +10 pts each (max 20)

---

## Pattern History Database

### Pattern History DB (`pattern_history_db.py`)

Track pattern outcomes for performance analysis.

#### API Reference

```python
from pattern_history_db import PatternHistoryDB

db = PatternHistoryDB('data/pattern_history.db')

# Store pattern
pattern_id = db.store_pattern(
    symbol='BTCUSDT',
    timeframe='1h',
    pattern=pattern_dict,
    entry_price=50000,
    stop_loss=49000,
    take_profit_1=52000,
    take_profit_2=54000
)

# Update outcome after pattern completes
db.update_pattern_outcome(
    pattern_id=pattern_id,
    outcome='success',  # success, failed, neutral
    actual_high=53000,
    actual_low=49500,
    exit_price=52000,
    notes='TP1 hit'
)

# Get pattern statistics
stats = db.get_pattern_statistics(
    pattern_name='Gartley_bull',
    direction='bullish'
)
# Returns: [{
#     'pattern_name': str,
#     'direction': str,
#     'total_patterns': int,
#     'successful': int,
#     'failed': int,
#     'success_rate': float,
#     'avg_pnl_pct': float,
#     'avg_quality_score': float,
#     'avg_max_profit': float,
#     'avg_max_loss': float
# }]

# Get best performing patterns
best = db.get_best_patterns(min_samples=10, limit=10)

# Analyze quality vs success
quality_analysis = db.analyze_pattern_quality()
# Returns score ranges with success rates

# Get recent patterns
recent = db.get_recent_patterns(days=30, symbol='BTCUSDT', limit=100)
```

---

## Configuration

### Config System (`config.py`)

Centralized configuration management.

#### API Reference

```python
from config import Config, get_config, save_config

# Get default config
config = get_config()

# Load from file
config = Config.from_json('config.json')

# Load from dict
config = Config.from_dict({
    'pattern_detection': {
        'min_bars': 50,
        'max_bars': 500
    }
})

# Access settings
min_bars = config.pattern_detection.min_bars
cache_enabled = config.cache.enabled
max_workers = config.parallel_processing.max_workers

# Modify settings
config.cache.ttl_seconds = 7200
config.parallel_processing.max_workers = 8

# Save to file
config.to_json('config.json')

# Save as default
save_config(config)

# Convert to dict
config_dict = config.to_dict()
```

**Configuration Modules**:
1. `pattern_detection`: Detection parameters
2. `cache`: Caching settings
3. `parallel_processing`: Parallel execution
4. `database`: Database configuration
5. `ui`: UI preferences
6. `alert`: Alert settings
7. `backtesting`: Backtesting parameters
8. `logging`: Logging configuration

---

## Testing

### Pytest Framework

#### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_pattern_detection.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m performance   # Performance tests only
```

#### Using Fixtures

```python
def test_pattern_detection(sample_ohlc_data, extremum_points):
    """Test using fixtures from conftest.py"""
    # sample_ohlc_data and extremum_points are automatically provided
    patterns = detect_patterns(sample_ohlc_data, extremum_points)
    assert len(patterns) > 0
```

**Available Fixtures**:
- `sample_ohlc_data`: Mock OHLC DataFrame
- `bullish_gartley_pattern`: Sample bullish Gartley
- `bearish_butterfly_pattern`: Sample bearish Butterfly
- `extremum_points`: Sample extremum points
- `mock_database`: Temporary test database
- `config_dict`: Sample configuration
- `performance_timer`: Performance testing timer

---

## Examples

### Example 1: Basic Pattern Detection

```python
from services import PatternDetectionService, DataService

# Load data
data_service = DataService()
df = data_service.download_data('BTCUSDT', '1h', '1mo')

# Detect patterns
pattern_service = PatternDetectionService(use_cache=True, use_parallel=True)

detection_methods = {
    'gartley': detect_gartley,
    'butterfly': detect_butterfly,
    'bat': detect_bat
}

patterns = pattern_service.detect_patterns(
    df=df,
    extremum_points=extremum,
    pattern_types=['gartley', 'butterfly', 'bat'],
    detection_methods=detection_methods,
    min_quality_score=60,
    validate=True
)

print(f"Found {len(patterns)} high-quality patterns")
```

### Example 2: Multi-Timeframe Analysis

```python
from multi_timeframe_analysis import analyze_symbol_multi_tf

# Analyze with confluence
signals = analyze_symbol_multi_tf(
    symbol='BTCUSDT',
    primary_tf='1h',
    supporting_tfs=['4h', '1d'],
    detection_func=detect_all_patterns
)

# Filter for strong signals
strong_signals = [s for s in signals if s.signal_strength == 'very_strong']

for signal in strong_signals:
    print(f"Strong signal: {signal.primary_pattern.pattern_name}")
    print(f"Confluence: {signal.confluence_score}/100")
    print(f"Supporting TFs: {len(signal.supporting_patterns)}")
```

### Example 3: Signal Management

```python
from services import SignalService, AlertService

signal_service = SignalService()
alert_service = AlertService()

# Create signal
signal_id = signal_service.create_signal(
    symbol='BTCUSDT',
    timeframe='1h',
    pattern=best_pattern,
    entry_price=50000,
    stop_loss=49000,
    take_profit=52000
)

# Create alert for entry
alert_service.create_alert(
    'price',
    'BTCUSDT',
    'cross_below',
    50000,
    f"Entry signal #{signal_id}"
)

# On price update
triggered = alert_service.check_alerts('BTCUSDT', current_price, previous_price)
if triggered:
    print(f"Alert triggered! Entry at {current_price}")
```

### Example 4: Performance Tracking

```python
from pattern_history_db import PatternHistoryDB

history_db = PatternHistoryDB()

# Store pattern when detected
pattern_id = history_db.store_pattern(
    symbol='BTCUSDT',
    timeframe='1h',
    pattern=detected_pattern,
    entry_price=50000,
    stop_loss=49000,
    take_profit_1=52000
)

# Update outcome after completion
history_db.update_pattern_outcome(
    pattern_id=pattern_id,
    outcome='success',
    actual_high=53000,
    actual_low=49800,
    exit_price=52000
)

# Analyze performance
stats = history_db.get_pattern_statistics(pattern_name='Gartley_bull')
print(f"Gartley Bull success rate: {stats[0]['success_rate']}%")

best_patterns = history_db.get_best_patterns(min_samples=10)
print(f"Best pattern: {best_patterns[0]['pattern_name']}")
```

---

## Error Handling

### Custom Exceptions

```python
from exceptions import (
    HarmonicPatternError,
    DataError,
    InvalidDataError,
    PatternDetectionError,
    DatabaseError,
    AlertError
)

try:
    patterns = detect_patterns(df, extremum)
except InvalidDataError as e:
    print(f"Data validation failed: {e}")
except PatternDetectionError as e:
    print(f"Detection failed: {e}")
except HarmonicPatternError as e:
    print(f"General error: {e}")
```

### Error Utilities

```python
from exceptions import format_error_message, is_recoverable_error

try:
    # Some operation
    pass
except Exception as e:
    msg = format_error_message(e, context="Pattern Detection")
    print(msg)

    if is_recoverable_error(e):
        # Retry operation
        pass
    else:
        # Stop execution
        raise
```

---

## Logging

### Logger Setup

```python
from logging_config import setup_logging, get_logger, log_performance, LoggerContext

# Setup logging system
logger = setup_logging(
    log_dir='logs',
    log_file='harmonic_patterns.log',
    console_level='INFO',
    file_level='DEBUG',
    max_file_size_mb=10,
    backup_count=5
)

# Get logger in any module
logger = get_logger('harmonic_patterns')

# Use logger
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")

# Log performance
log_performance("Pattern Detection", 2.5, "Detected 10 patterns")

# Use context manager
with LoggerContext(logger, "Data Loading", level=logging.INFO):
    # Operation is automatically timed and logged
    df = load_data()
```

---

## Performance Tips

1. **Enable Caching**: Use `PatternDetectionService(use_cache=True)` for repeated analyses
2. **Parallel Processing**: Enable for multiple pattern types: `use_parallel=True`
3. **Quality Filtering**: Filter early with `min_quality_score` to reduce processing
4. **Database Indices**: Run `optimize_database.py` periodically
5. **Cache Size**: Increase cache size for better hit rates: `PatternCache(max_size=200)`
6. **Worker Count**: Adjust parallel workers based on CPU: `max_workers=cpu_count()`

---

## Version Information

- **Version**: 2.0
- **Last Updated**: 2025-10-07
- **Python**: 3.8+
- **Dependencies**: See `requirements.txt` and `requirements-test.txt`

---

## Support

For issues, questions, or contributions:
- Check `IMPROVEMENTS_SUMMARY.md` for recent changes
- Review test files in `tests/` for usage examples
- See individual module docstrings for detailed API docs
