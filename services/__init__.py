"""
Service Layer Package

Provides business logic separation from GUI and data layers.
Implements MVC-like architecture for better code organization.
"""

from .pattern_service import PatternDetectionService
from .data_service import DataService
from .signal_service import SignalService
from .alert_service import AlertService

__all__ = [
    'PatternDetectionService',
    'DataService',
    'SignalService',
    'AlertService',
]
