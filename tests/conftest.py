"""
Pytest Configuration and Fixtures

Shared fixtures and configuration for all tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List


@pytest.fixture
def sample_ohlc_data():
    """Generate sample OHLC data for testing"""
    dates = pd.date_range('2024-01-01', periods=200, freq='1h')

    # Generate realistic price data
    base_price = 100
    prices = []
    current = base_price

    for i in range(200):
        change = np.random.randn() * 2
        current = current + change
        prices.append(current)

    df = pd.DataFrame({
        'Open': prices,
        'High': [p + abs(np.random.randn()) for p in prices],
        'Low': [p - abs(np.random.randn()) for p in prices],
        'Close': [p + np.random.randn() * 0.5 for p in prices],
        'Volume': np.random.randint(1000, 10000, 200)
    }, index=dates)

    # Ensure High is highest and Low is lowest
    df['High'] = df[['Open', 'Close', 'High']].max(axis=1)
    df['Low'] = df[['Open', 'Close', 'Low']].min(axis=1)

    return df


@pytest.fixture
def bullish_gartley_pattern():
    """Sample bullish Gartley pattern"""
    dates = pd.date_range('2024-01-01', periods=5)

    return {
        'name': 'Gartley_bull',
        'pattern_type': 'XABCD',
        'type': 'bullish',
        'points': {
            'X': {'time': dates[0], 'price': 100.0},
            'A': {'time': dates[1], 'price': 110.0},
            'B': {'time': dates[2], 'price': 103.82},  # 61.8% retracement
            'C': {'time': dates[3], 'price': 108.0},
            'D': {'time': dates[4], 'price': 104.28}   # 127.2% projection
        },
        'ratios': {
            'ab_retracement': 61.8,
            'bc_retracement': 61.8,
            'cd_projection': 127.2,
            'ad_retracement': 78.6
        },
        'prz_zone': {
            'low': 104.0,
            'high': 104.5
        }
    }


@pytest.fixture
def bearish_butterfly_pattern():
    """Sample bearish Butterfly pattern"""
    dates = pd.date_range('2024-01-01', periods=5)

    return {
        'name': 'Butterfly_bear',
        'pattern_type': 'XABCD',
        'type': 'bearish',
        'points': {
            'X': {'time': dates[0], 'price': 100.0},
            'A': {'time': dates[1], 'price': 90.0},
            'B': {'time': dates[2], 'price': 97.14},  # 78.6% retracement
            'C': {'time': dates[3], 'price': 92.0},
            'D': {'time': dates[4], 'price': 100.14}  # 161.8% projection
        },
        'ratios': {
            'ab_retracement': 78.6,
            'bc_retracement': 38.2,
            'cd_projection': 161.8,
            'ad_retracement': 127.0
        },
        'prz_zone': {
            'low': 99.8,
            'high': 100.5
        }
    }


@pytest.fixture
def extremum_points():
    """Sample extremum points for testing"""
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')

    return [
        {'index': 10, 'time': dates[10], 'price': 95.0, 'type': 'low'},
        {'index': 20, 'time': dates[20], 'price': 105.0, 'type': 'high'},
        {'index': 30, 'time': dates[30], 'price': 98.0, 'type': 'low'},
        {'index': 40, 'time': dates[40], 'price': 108.0, 'type': 'high'},
        {'index': 50, 'time': dates[50], 'price': 102.0, 'type': 'low'},
        {'index': 60, 'time': dates[60], 'price': 112.0, 'type': 'high'},
        {'index': 70, 'time': dates[70], 'price': 106.0, 'type': 'low'},
        {'index': 80, 'time': dates[80], 'price': 115.0, 'type': 'high'},
    ]


@pytest.fixture
def invalid_pattern():
    """Sample invalid pattern for testing validation"""
    dates = pd.date_range('2024-01-01', periods=4)

    return {
        'name': 'Invalid_Pattern',
        'pattern_type': 'ABCD',
        'type': 'bullish',
        'points': {
            'A': {'time': dates[0], 'price': 100.0},
            'B': {'time': dates[1], 'price': 90.0},
            'C': {'time': dates[2], 'price': 95.0},
            'D': {'time': dates[3], 'price': 85.0}  # Wrong direction
        },
        'ratios': {
            'bc_retracement': 50.0,
            'cd_projection': 100.0
        }
    }


@pytest.fixture
def mock_database(tmp_path):
    """Create temporary test database"""
    import sqlite3

    db_path = tmp_path / "test_signals.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create signals table
    cursor.execute('''
        CREATE TABLE signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            pattern_type TEXT NOT NULL,
            pattern_name TEXT NOT NULL,
            direction TEXT NOT NULL,
            status TEXT NOT NULL,
            detected_at TIMESTAMP NOT NULL,
            last_updated TIMESTAMP NOT NULL,
            pattern_data TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

    return str(db_path)


@pytest.fixture
def config_dict():
    """Sample configuration dictionary"""
    return {
        'pattern_detection': {
            'min_bars': 50,
            'max_bars': 500,
            'retracement_tolerance': 5.0,
            'projection_tolerance': 10.0
        },
        'cache': {
            'enabled': True,
            'max_cache_size': 100,
            'ttl_seconds': 3600
        },
        'parallel_processing': {
            'enabled': True,
            'max_workers': 4
        },
        'database': {
            'path': 'data/signals.db',
            'enable_wal': True
        }
    }


# Performance testing helpers
@pytest.fixture
def performance_timer():
    """Timer fixture for performance testing"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer()


# Mock objects for testing
@pytest.fixture
def mock_pattern_detector():
    """Mock pattern detector for testing"""
    class MockDetector:
        def __init__(self):
            self.detected_patterns = []

        def detect_patterns(self, df, pattern_type='all'):
            # Return mock patterns
            return [
                {
                    'name': 'Test_Pattern',
                    'type': 'bullish',
                    'points': {},
                    'ratios': {}
                }
            ]

        def validate_pattern(self, pattern):
            return True

    return MockDetector()


# Parametrize helpers
@pytest.fixture(params=['bullish', 'bearish'])
def pattern_direction(request):
    """Parametrized fixture for pattern directions"""
    return request.param


@pytest.fixture(params=['ABCD', 'XABCD'])
def pattern_type(request):
    """Parametrized fixture for pattern types"""
    return request.param


@pytest.fixture(params=[
    'Gartley', 'Butterfly', 'Bat', 'Crab', 'Shark',
    'Cypher', 'Three_Drives', 'ABCD'
])
def pattern_name(request):
    """Parametrized fixture for pattern names"""
    return request.param
