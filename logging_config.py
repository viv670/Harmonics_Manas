"""
Comprehensive Logging Configuration
Provides structured logging with rotation, formatting, and multiple handlers

Features:
- Rotating file logs (10MB max, 5 backups)
- Console output for errors
- Configurable log levels
- Structured log format
- Performance logging
- Error tracking
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"

        return super().format(record)


def setup_logging(
    log_dir: str = "logs",
    log_file: str = "harmonic_patterns.log",
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    max_file_size_mb: int = 10,
    backup_count: int = 5,
    use_colors: bool = True
) -> logging.Logger:
    """
    Setup comprehensive logging system.

    Args:
        log_dir: Directory for log files
        log_file: Log file name
        console_level: Minimum level for console output
        file_level: Minimum level for file output
        max_file_size_mb: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        use_colors: Whether to use colored console output

    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger('harmonic_patterns')
    logger.setLevel(logging.DEBUG)  # Capture all levels, handlers will filter

    # Remove existing handlers to avoid duplicates
    logger.handlers = []

    # Log format
    detailed_format = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    simple_format = '%(levelname)s: %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # File handler with rotation
    file_path = log_path / log_file
    file_handler = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=max_file_size_mb * 1024 * 1024,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(getattr(logging, file_level.upper()))
    file_formatter = logging.Formatter(detailed_format, date_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler (only for warnings and above by default)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, console_level.upper()))

    if use_colors and sys.stdout.isatty():
        console_formatter = ColoredFormatter(simple_format, date_format)
    else:
        console_formatter = logging.Formatter(simple_format, date_format)

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Performance log file (separate from main log)
    perf_file = log_path / 'performance.log'
    perf_handler = logging.handlers.RotatingFileHandler(
        perf_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3
    )
    perf_handler.setLevel(logging.INFO)
    perf_formatter = logging.Formatter('%(asctime)s - %(message)s', date_format)
    perf_handler.setFormatter(perf_formatter)

    # Create separate performance logger
    perf_logger = logging.getLogger('harmonic_patterns.performance')
    perf_logger.setLevel(logging.INFO)
    perf_logger.addHandler(perf_handler)
    perf_logger.propagate = False  # Don't send to parent logger

    logger.info("Logging system initialized")
    logger.info(f"Log file: {file_path}")
    logger.info(f"File level: {file_level}, Console level: {console_level}")

    return logger


def get_logger(name: str = 'harmonic_patterns') -> logging.Logger:
    """
    Get logger instance.

    Args:
        name: Logger name (default: 'harmonic_patterns')

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_performance(operation: str, duration: float, details: Optional[str] = None):
    """
    Log performance metrics.

    Args:
        operation: Name of operation
        duration: Time taken in seconds
        details: Optional additional details
    """
    perf_logger = logging.getLogger('harmonic_patterns.performance')

    msg = f"{operation}: {duration:.3f}s"
    if details:
        msg += f" - {details}"

    perf_logger.info(msg)


def log_error_with_context(logger: logging.Logger, error: Exception, context: str):
    """
    Log error with full context and traceback.

    Args:
        logger: Logger instance
        error: Exception that occurred
        context: Context description
    """
    import traceback

    logger.error(f"Error in {context}: {type(error).__name__}: {str(error)}")
    logger.debug(f"Traceback:\n{traceback.format_exc()}")


class LoggerContext:
    """Context manager for logging operations with timing"""

    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None

    def __enter__(self):
        import time
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        duration = time.time() - self.start_time

        if exc_type is None:
            self.logger.log(self.level, f"Completed: {self.operation} ({duration:.3f}s)")
            log_performance(self.operation, duration)
        else:
            self.logger.error(f"Failed: {self.operation} ({duration:.3f}s) - {exc_type.__name__}: {exc_val}")

        return False  # Don't suppress exceptions


if __name__ == "__main__":
    print("Testing Logging System...")
    print()

    # Setup logging
    logger = setup_logging(console_level="DEBUG")

    # Test different log levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    # Test performance logging
    import time
    time.sleep(0.1)
    log_performance("Test Operation", 0.1, "Test details")

    # Test logger context
    print("\nTesting logger context...")
    with LoggerContext(logger, "Test Operation"):
        time.sleep(0.05)
        logger.info("Doing work...")

    # Test error logging
    print("\nTesting error logging...")
    try:
        raise ValueError("Test error")
    except Exception as e:
        log_error_with_context(logger, e, "Test Function")

    print("\n✅ Logging system ready!")
    print(f"Check logs directory for log files")
