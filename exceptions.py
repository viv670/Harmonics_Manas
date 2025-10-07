"""
Custom Exception Hierarchy for Harmonic Pattern System

Provides structured error handling with specific exception types
for different failure scenarios.

Benefits:
- Clearer error messages
- Better error tracking
- Easier debugging
- Graceful error recovery
"""


class HarmonicPatternError(Exception):
    """Base exception for all harmonic pattern system errors"""
    pass


# Data-related exceptions
class DataError(HarmonicPatternError):
    """Base class for data-related errors"""
    pass


class InvalidDataError(DataError):
    """Raised when input data is invalid or malformed"""
    pass


class MissingDataError(DataError):
    """Raised when required data is missing"""
    pass


class DataQualityError(DataError):
    """Raised when data quality is insufficient"""
    pass


# Pattern detection exceptions
class PatternDetectionError(HarmonicPatternError):
    """Base class for pattern detection errors"""
    pass


class ValidationError(PatternDetectionError):
    """Raised when pattern validation fails"""
    pass


class RatioError(PatternDetectionError):
    """Raised when pattern ratios are invalid"""
    pass


class ExtremumError(PatternDetectionError):
    """Raised when extremum point detection fails"""
    pass


# Database exceptions
class DatabaseError(HarmonicPatternError):
    """Base class for database errors"""
    pass


class SignalNotFoundError(DatabaseError):
    """Raised when a signal cannot be found in database"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    pass


# Configuration exceptions
class ConfigurationError(HarmonicPatternError):
    """Base class for configuration errors"""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration is invalid"""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing"""
    pass


# API/Network exceptions
class APIError(HarmonicPatternError):
    """Base class for API errors"""
    pass


class DataDownloadError(APIError):
    """Raised when data download fails"""
    pass


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded"""
    pass


# Alert exceptions
class AlertError(HarmonicPatternError):
    """Base class for alert system errors"""
    pass


class AlertDeliveryError(AlertError):
    """Raised when alert delivery fails"""
    pass


class InvalidAlertError(AlertError):
    """Raised when alert configuration is invalid"""
    pass


# Utility functions for error handling
def format_error_message(error: Exception, context: str = "") -> str:
    """
    Format error message with context.

    Args:
        error: The exception that occurred
        context: Additional context about where/when error occurred

    Returns:
        Formatted error message string
    """
    error_type = type(error).__name__
    error_msg = str(error)

    if context:
        return f"[{context}] {error_type}: {error_msg}"
    else:
        return f"{error_type}: {error_msg}"


def is_recoverable_error(error: Exception) -> bool:
    """
    Determine if an error is recoverable.

    Args:
        error: The exception to check

    Returns:
        True if error is recoverable, False otherwise
    """
    # Recoverable errors - can retry or continue
    recoverable_types = (
        RateLimitError,
        DataDownloadError,
        DatabaseConnectionError,
        AlertDeliveryError,
    )

    # Non-recoverable errors - should stop execution
    non_recoverable_types = (
        InvalidDataError,
        InvalidConfigurationError,
        ValidationError,
    )

    if isinstance(error, recoverable_types):
        return True
    elif isinstance(error, non_recoverable_types):
        return False
    else:
        # Unknown errors are considered non-recoverable for safety
        return False


if __name__ == "__main__":
    print("Testing Exception Hierarchy...")

    # Test exception hierarchy
    try:
        raise InvalidDataError("Test data is malformed")
    except DataError as e:
        print(f"✓ Caught DataError: {e}")
    except HarmonicPatternError as e:
        print(f"✓ Caught HarmonicPatternError: {e}")

    # Test error formatting
    try:
        raise ValidationError("Pattern failed price containment check")
    except Exception as e:
        msg = format_error_message(e, "Pattern Detection")
        print(f"\n✓ Formatted message: {msg}")

    # Test recoverability check
    errors_to_test = [
        RateLimitError("API limit exceeded"),
        InvalidDataError("Missing OHLC columns"),
        DataDownloadError("Network timeout"),
        ValidationError("Invalid pattern structure"),
    ]

    print("\n✓ Recoverability check:")
    for error in errors_to_test:
        recoverable = is_recoverable_error(error)
        print(f"  {type(error).__name__}: {'Recoverable' if recoverable else 'Non-recoverable'}")

    print("\n✅ Exception system ready!")
