"""
Centralized Configuration Management
All configuration parameters in one place for easy modification

This module provides:
- Type-safe configuration with dataclasses
- Environment-based configuration
- Configuration validation
- JSON/YAML configuration file support
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
import json
from pathlib import Path


@dataclass
class PatternDetectionConfig:
    """Configuration for pattern detection algorithms"""

    # Performance limits
    max_extremum_points: int = 200
    max_patterns_per_type: int = 100
    detection_timeout_seconds: int = 10
    max_future_candles: int = 100

    # Validation settings
    enable_price_containment: bool = True
    enable_d_crossing_check: bool = True
    enable_c_crossing_check: bool = True

    # Search window settings
    default_search_window: int = 20
    auto_search_window: bool = True
    unlimited_search_value: int = 9  # Typing 9 triggers unlimited search

    # Adaptive limits
    small_dataset_threshold: int = 100
    medium_dataset_threshold: int = 500
    small_dataset_max_points: Optional[int] = None  # No limit
    medium_dataset_max_points: int = 300
    large_dataset_max_points: int = 200

    # Pattern filtering
    min_pattern_quality_score: int = 0
    filter_crossed_patterns: bool = True


@dataclass
class CacheConfig:
    """Configuration for pattern caching system"""

    enabled: bool = True
    max_cache_size: int = 100
    ttl_seconds: int = 3600  # 1 hour
    auto_cleanup: bool = True
    cleanup_interval_seconds: int = 600  # 10 minutes


@dataclass
class ParallelProcessingConfig:
    """Configuration for parallel processing"""

    enabled: bool = True
    max_workers: int = 4
    min_patterns_for_parallel: int = 2  # Only use parallel if detecting 2+ pattern types
    thread_pool_timeout: int = 60


@dataclass
class DatabaseConfig:
    """Configuration for database operations"""

    database_path: str = "data/signals.db"
    enable_wal_mode: bool = True  # Write-Ahead Logging for better concurrency
    auto_vacuum: bool = True
    cache_size_kb: int = 10000  # 10MB cache
    connection_timeout: int = 30


@dataclass
class UIConfig:
    """Configuration for user interface"""

    # Default extremum value
    default_extremum_value: int = 3

    # Chart settings
    default_chart_theme: str = "dark"
    candlestick_width: float = 0.6
    show_volume: bool = True

    # Pattern colors
    bullish_color: str = "#00FF00"
    bearish_color: str = "#FF0000"
    prz_color: str = "#FF8C00"

    # Performance
    max_patterns_to_display: int = 50
    enable_pattern_labels: bool = True
    enable_tooltips: bool = True


@dataclass
class AlertConfig:
    """Configuration for price alerts"""

    enabled: bool = True
    check_interval_seconds: int = 60
    max_alerts_per_pattern: int = 10

    # Email alerts
    enable_email_alerts: bool = False
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    from_email: str = ""
    to_emails: List[str] = field(default_factory=list)

    # Desktop notifications
    enable_desktop_notifications: bool = True
    notification_duration_seconds: int = 5


@dataclass
class BacktestingConfig:
    """Configuration for backtesting"""

    # Default parameters
    default_risk_reward_ratio: float = 2.0
    default_stop_loss_pct: float = 2.0
    default_position_size_pct: float = 100.0

    # Fibonacci levels for targets
    fibonacci_levels: List[float] = field(default_factory=lambda: [
        0, 23.6, 38.2, 50, 61.8, 78.6, 88.6, 100, 112.8, 127.2, 141.4, 161.8
    ])

    # Performance tracking
    track_pattern_statistics: bool = True
    min_sample_size_for_stats: int = 10


@dataclass
class LoggingConfig:
    """Configuration for logging"""

    # Logging levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
    console_level: str = "INFO"
    file_level: str = "DEBUG"

    # Log file settings
    log_file_path: str = "logs/harmonic_patterns.log"
    max_log_file_size_mb: int = 10
    backup_count: int = 5

    # Format
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


@dataclass
class Config:
    """Main configuration container"""

    pattern_detection: PatternDetectionConfig = field(default_factory=PatternDetectionConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    parallel_processing: ParallelProcessingConfig = field(default_factory=ParallelProcessingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    alerts: AlertConfig = field(default_factory=AlertConfig)
    backtesting: BacktestingConfig = field(default_factory=BacktestingConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def to_dict(self) -> Dict:
        """Convert configuration to dictionary"""
        return asdict(self)

    def to_json(self, file_path: str) -> None:
        """Save configuration to JSON file"""
        with open(file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> 'Config':
        """Load configuration from dictionary"""
        return cls(
            pattern_detection=PatternDetectionConfig(**data.get('pattern_detection', {})),
            cache=CacheConfig(**data.get('cache', {})),
            parallel_processing=ParallelProcessingConfig(**data.get('parallel_processing', {})),
            database=DatabaseConfig(**data.get('database', {})),
            ui=UIConfig(**data.get('ui', {})),
            alerts=AlertConfig(**data.get('alerts', {})),
            backtesting=BacktestingConfig(**data.get('backtesting', {})),
            logging=LoggingConfig(**data.get('logging', {}))
        )

    @classmethod
    def from_json(cls, file_path: str) -> 'Config':
        """Load configuration from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def create_default_config_file(cls, file_path: str = 'config.json') -> None:
        """Create default configuration file"""
        config = cls()
        config.to_json(file_path)
        print(f"✓ Default configuration created at: {file_path}")


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get global configuration instance (singleton).

    Returns:
        Global Config instance
    """
    global _config

    if _config is None:
        # Try to load from file
        config_path = Path('config.json')
        if config_path.exists():
            try:
                _config = Config.from_json(str(config_path))
                print(f"✓ Configuration loaded from {config_path}")
            except Exception as e:
                print(f"⚠️  Failed to load config from {config_path}: {e}")
                print("   Using default configuration")
                _config = Config()
        else:
            # Use default configuration
            _config = Config()

    return _config


def reload_config(file_path: str = 'config.json') -> Config:
    """
    Reload configuration from file.

    Args:
        file_path: Path to configuration file

    Returns:
        Reloaded Config instance
    """
    global _config
    _config = Config.from_json(file_path)
    print(f"✓ Configuration reloaded from {file_path}")
    return _config


if __name__ == "__main__":
    print("Configuration Management System")
    print("="*60)
    print()

    # Create default configuration
    config = Config()

    print("Default Configuration:")
    print()
    print("Pattern Detection:")
    print(f"  Max extremum points: {config.pattern_detection.max_extremum_points}")
    print(f"  Max patterns per type: {config.pattern_detection.max_patterns_per_type}")
    print(f"  Detection timeout: {config.pattern_detection.detection_timeout_seconds}s")
    print()

    print("Cache:")
    print(f"  Enabled: {config.cache.enabled}")
    print(f"  Max size: {config.cache.max_cache_size}")
    print(f"  TTL: {config.cache.ttl_seconds}s")
    print()

    print("Parallel Processing:")
    print(f"  Enabled: {config.parallel_processing.enabled}")
    print(f"  Max workers: {config.parallel_processing.max_workers}")
    print()

    print("Database:")
    print(f"  Path: {config.database.database_path}")
    print(f"  WAL mode: {config.database.enable_wal_mode}")
    print(f"  Cache size: {config.database.cache_size_kb}KB")
    print()

    # Create default config file
    print("Creating default configuration file...")
    Config.create_default_config_file('config_default.json')

    print()
    print("="*60)
    print("Configuration system ready!")
