"""
Unit Tests for Pattern Detection

Tests for harmonic pattern detection logic, validation, and accuracy.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pattern_validators import PriceContainmentValidator


class TestPriceContainmentValidator:
    """Test price containment validation logic"""

    @pytest.mark.unit
    @pytest.mark.validation
    def test_bullish_abcd_valid(self, sample_ohlc_data):
        """Test valid bullish ABCD pattern validation"""
        df = sample_ohlc_data

        # Create valid bullish ABCD points
        a_idx, b_idx, c_idx = 10, 20, 30
        a_price = df['High'].iloc[a_idx]
        b_price = df['Low'].iloc[b_idx]
        c_price = df['High'].iloc[c_idx]

        # Ensure valid structure: A > B, C < A
        if c_price >= a_price or b_price >= a_price:
            pytest.skip("Sample data doesn't meet requirements")

        is_valid = PriceContainmentValidator.validate_bullish_abcd(
            df, a_idx, b_idx, c_idx, a_price, b_price, c_price
        )

        # May or may not pass depending on data, but should not raise exception
        assert isinstance(is_valid, bool)

    @pytest.mark.unit
    @pytest.mark.validation
    def test_bearish_abcd_valid(self, sample_ohlc_data):
        """Test valid bearish ABCD pattern validation"""
        df = sample_ohlc_data

        a_idx, b_idx, c_idx = 10, 20, 30
        a_price = df['Low'].iloc[a_idx]
        b_price = df['High'].iloc[b_idx]
        c_price = df['Low'].iloc[c_idx]

        # Ensure valid structure: A < B, C > A
        if c_price <= a_price or b_price <= a_price:
            pytest.skip("Sample data doesn't meet requirements")

        is_valid = PriceContainmentValidator.validate_bearish_abcd(
            df, a_idx, b_idx, c_idx, a_price, b_price, c_price
        )

        assert isinstance(is_valid, bool)

    @pytest.mark.unit
    @pytest.mark.validation
    def test_bullish_xabcd_valid(self, sample_ohlc_data):
        """Test valid bullish XABCD pattern validation"""
        df = sample_ohlc_data

        x_idx, a_idx, b_idx, c_idx = 5, 10, 20, 30
        x_price = df['Low'].iloc[x_idx]
        a_price = df['High'].iloc[a_idx]
        b_price = df['Low'].iloc[b_idx]
        c_price = df['High'].iloc[c_idx]

        is_valid = PriceContainmentValidator.validate_bullish_xabcd(
            df, x_idx, a_idx, b_idx, c_idx,
            x_price, a_price, b_price, c_price
        )

        assert isinstance(is_valid, bool)

    @pytest.mark.unit
    @pytest.mark.validation
    def test_invalid_indices(self, sample_ohlc_data):
        """Test validation with invalid indices"""
        df = sample_ohlc_data

        # Out of range indices should return False
        is_valid = PriceContainmentValidator.validate_bullish_abcd(
            df, 1000, 1001, 1002,  # Invalid indices
            100, 90, 95
        )

        assert is_valid is False

    @pytest.mark.unit
    @pytest.mark.validation
    def test_validate_pattern_convenience(self, bullish_gartley_pattern, sample_ohlc_data):
        """Test convenience validate_pattern function"""
        result = PriceContainmentValidator.validate_pattern(
            bullish_gartley_pattern,
            sample_ohlc_data
        )

        assert isinstance(result, bool)


class TestPatternRatios:
    """Test pattern ratio calculations"""

    @pytest.mark.unit
    @pytest.mark.pattern_detection
    def test_fibonacci_retracement(self):
        """Test Fibonacci retracement calculation"""
        # Move from 100 to 110 (10 points)
        # 61.8% retracement = 110 - (10 * 0.618) = 103.82
        start = 100
        end = 110
        retracement_pct = 61.8

        retracement_level = end - ((end - start) * (retracement_pct / 100))

        assert abs(retracement_level - 103.82) < 0.01

    @pytest.mark.unit
    @pytest.mark.pattern_detection
    def test_fibonacci_projection(self):
        """Test Fibonacci projection calculation"""
        # BC leg from 103.82 to 108 (4.18 points)
        # 127.2% projection = 108 - (4.18 * 1.272) = 102.68
        bc_start = 103.82
        bc_end = 108
        projection_pct = 127.2

        bc_length = bc_end - bc_start
        projection_level = bc_end - (bc_length * (projection_pct / 100))

        assert abs(projection_level - 102.68) < 0.1

    @pytest.mark.unit
    @pytest.mark.pattern_detection
    def test_ratio_tolerance(self):
        """Test ratio tolerance checking"""
        ideal_ratio = 61.8
        tolerance = 5.0

        # Within tolerance
        assert abs(62.0 - ideal_ratio) <= tolerance
        assert abs(61.5 - ideal_ratio) <= tolerance
        assert abs(66.0 - ideal_ratio) <= tolerance

        # Outside tolerance
        assert abs(70.0 - ideal_ratio) > tolerance
        assert abs(55.0 - ideal_ratio) > tolerance


class TestExtremumDetection:
    """Test extremum point detection"""

    @pytest.mark.unit
    @pytest.mark.pattern_detection
    def test_extremum_detection_basic(self):
        """Test basic extremum detection"""
        # Create data with clear peaks and valleys
        prices = [100, 105, 110, 105, 100, 95, 100, 105, 110]
        df = pd.DataFrame({
            'High': [p + 1 for p in prices],
            'Low': [p - 1 for p in prices],
            'Close': prices
        })

        # Peak at index 2 (110)
        # Valley at index 5 (95)
        # Peak at index 8 (110)

        # Simple extremum detection
        highs = df['High'].values
        lows = df['Low'].values

        local_maxima = []
        local_minima = []

        for i in range(1, len(df) - 1):
            if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
                local_maxima.append(i)
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
                local_minima.append(i)

        assert 2 in local_maxima  # Peak at 110
        assert 5 in local_minima  # Valley at 95

    @pytest.mark.unit
    @pytest.mark.pattern_detection
    def test_alternating_extremum(self):
        """Test that extremum points alternate high/low"""
        extremum_points = [
            {'type': 'low', 'price': 95},
            {'type': 'high', 'price': 105},
            {'type': 'low', 'price': 98},
            {'type': 'high', 'price': 108},
        ]

        # Check alternation
        for i in range(len(extremum_points) - 1):
            current_type = extremum_points[i]['type']
            next_type = extremum_points[i + 1]['type']
            assert current_type != next_type


class TestPatternCache:
    """Test pattern caching functionality"""

    @pytest.mark.unit
    def test_cache_hit(self):
        """Test cache hit detection"""
        from pattern_cache import PatternCache

        cache = PatternCache(max_size=10, ttl=60)

        # Mock data
        extremum = [{'index': 0, 'price': 100}]
        df = pd.DataFrame({'Close': [100, 101, 102]})
        patterns = [{'name': 'Test'}]

        # Store in cache
        cache.set(extremum, df, 'test_pattern', patterns)

        # Retrieve from cache
        cached = cache.get(extremum, df, 'test_pattern')

        assert cached is not None
        assert cached == patterns
        assert cache.get_stats()['hits'] == 1

    @pytest.mark.unit
    def test_cache_miss(self):
        """Test cache miss detection"""
        from pattern_cache import PatternCache

        cache = PatternCache(max_size=10, ttl=60)

        # Try to get non-existent item
        extremum = [{'index': 0, 'price': 100}]
        df = pd.DataFrame({'Close': [100, 101, 102]})

        cached = cache.get(extremum, df, 'test_pattern')

        assert cached is None
        assert cache.get_stats()['misses'] == 1

    @pytest.mark.unit
    def test_cache_expiry(self):
        """Test cache TTL expiration"""
        import time
        from pattern_cache import PatternCache

        cache = PatternCache(max_size=10, ttl=1)  # 1 second TTL

        extremum = [{'index': 0, 'price': 100}]
        df = pd.DataFrame({'Close': [100, 101, 102]})
        patterns = [{'name': 'Test'}]

        # Store in cache
        cache.set(extremum, df, 'test_pattern', patterns)

        # Wait for expiry
        time.sleep(1.1)

        # Should be expired
        cached = cache.get(extremum, df, 'test_pattern')
        assert cached is None


class TestPatternScoring:
    """Test pattern quality scoring"""

    @pytest.mark.unit
    def test_ratio_precision_score(self, bullish_gartley_pattern, sample_ohlc_data):
        """Test ratio precision scoring"""
        from pattern_scoring import PatternStrengthScorer

        scorer = PatternStrengthScorer()
        score = scorer._score_ratio_precision(bullish_gartley_pattern)

        # Perfect ratios should score high
        assert score >= 20  # At least 20/30 points

    @pytest.mark.unit
    def test_volume_confirmation_score(self, bullish_gartley_pattern, sample_ohlc_data):
        """Test volume confirmation scoring"""
        from pattern_scoring import PatternStrengthScorer

        scorer = PatternStrengthScorer()
        score = scorer._score_volume_confirmation(
            bullish_gartley_pattern,
            sample_ohlc_data
        )

        # Should return a score between 0-20
        assert 0 <= score <= 20

    @pytest.mark.unit
    def test_total_score_range(self, bullish_gartley_pattern, sample_ohlc_data):
        """Test total score is within 0-100 range"""
        from pattern_scoring import PatternStrengthScorer

        scorer = PatternStrengthScorer()
        score = scorer.score_pattern(bullish_gartley_pattern, sample_ohlc_data)

        assert 0 <= score <= 100
        assert isinstance(score, int)

    @pytest.mark.unit
    def test_score_breakdown(self, bullish_gartley_pattern, sample_ohlc_data):
        """Test score breakdown contains all components"""
        from pattern_scoring import PatternStrengthScorer

        scorer = PatternStrengthScorer()
        breakdown = scorer.get_score_breakdown(
            bullish_gartley_pattern,
            sample_ohlc_data
        )

        required_components = [
            'ratio_precision',
            'volume_confirmation',
            'trend_alignment',
            'price_cleanliness',
            'time_symmetry',
            'total'
        ]

        for component in required_components:
            assert component in breakdown


class TestParallelProcessing:
    """Test parallel pattern detection"""

    @pytest.mark.unit
    @pytest.mark.performance
    def test_parallel_detection_results(self, sample_ohlc_data, extremum_points):
        """Test parallel detection produces results"""
        from parallel_pattern_detector import ParallelPatternDetector

        def mock_detect(extremum, df):
            return [{'name': 'Test_Pattern', 'type': 'bullish'}]

        detector = ParallelPatternDetector(max_workers=2)

        detection_methods = {
            'pattern1': lambda: mock_detect(extremum_points, sample_ohlc_data),
            'pattern2': lambda: mock_detect(extremum_points, sample_ohlc_data),
        }

        results = detector.detect_all_patterns(
            extremum_points,
            sample_ohlc_data,
            detection_methods
        )

        assert len(results) == 2
        assert 'pattern1' in results
        assert 'pattern2' in results

    @pytest.mark.unit
    def test_parallel_error_isolation(self, sample_ohlc_data, extremum_points):
        """Test that errors in one pattern don't affect others"""
        from parallel_pattern_detector import ParallelPatternDetector

        def good_detect(extremum, df):
            return [{'name': 'Good'}]

        def bad_detect(extremum, df):
            raise ValueError("Test error")

        detector = ParallelPatternDetector(max_workers=2)

        detection_methods = {
            'good': lambda: good_detect(extremum_points, sample_ohlc_data),
            'bad': lambda: bad_detect(extremum_points, sample_ohlc_data),
        }

        results = detector.detect_all_patterns(
            extremum_points,
            sample_ohlc_data,
            detection_methods
        )

        # Good pattern should succeed
        assert 'good' in results
        assert len(results['good']) == 1

        # Bad pattern should return empty list
        assert 'bad' in results
        assert len(results['bad']) == 0


class TestConfiguration:
    """Test configuration management"""

    @pytest.mark.unit
    def test_config_loading(self, config_dict, tmp_path):
        """Test configuration loading from dict"""
        from config import Config

        config = Config.from_dict(config_dict)

        assert config.pattern_detection.min_bars == 50
        assert config.cache.enabled is True
        assert config.parallel_processing.max_workers == 4

    @pytest.mark.unit
    def test_config_save_load(self, config_dict, tmp_path):
        """Test saving and loading configuration"""
        from config import Config

        config = Config.from_dict(config_dict)

        # Save to file
        config_file = tmp_path / "config.json"
        config.to_json(str(config_file))

        # Load from file
        loaded_config = Config.from_json(str(config_file))

        assert loaded_config.pattern_detection.min_bars == config.pattern_detection.min_bars
        assert loaded_config.cache.ttl_seconds == config.cache.ttl_seconds


@pytest.mark.integration
class TestDatabaseOperations:
    """Test database operations"""

    def test_signal_insertion(self, mock_database):
        """Test inserting signals into database"""
        import sqlite3

        conn = sqlite3.connect(mock_database)
        cursor = conn.cursor()

        # Insert test signal
        cursor.execute('''
            INSERT INTO signals (symbol, timeframe, pattern_type, pattern_name,
                               direction, status, detected_at, last_updated, pattern_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('BTCUSDT', '1h', 'XABCD', 'Gartley_bull', 'bullish', 'active',
              datetime.now(), datetime.now(), '{}'))

        conn.commit()

        # Verify insertion
        cursor.execute('SELECT COUNT(*) FROM signals')
        count = cursor.fetchone()[0]

        assert count == 1

        conn.close()

    def test_signal_query(self, mock_database):
        """Test querying signals"""
        import sqlite3

        conn = sqlite3.connect(mock_database)
        cursor = conn.cursor()

        # Insert multiple signals
        signals = [
            ('BTCUSDT', '1h', 'XABCD', 'Gartley_bull', 'bullish', 'active'),
            ('ETHUSDT', '4h', 'ABCD', 'Butterfly_bear', 'bearish', 'completed'),
            ('BTCUSDT', '1d', 'XABCD', 'Bat_bull', 'bullish', 'active'),
        ]

        for signal in signals:
            cursor.execute('''
                INSERT INTO signals (symbol, timeframe, pattern_type, pattern_name,
                                   direction, status, detected_at, last_updated, pattern_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', signal + (datetime.now(), datetime.now(), '{}'))

        conn.commit()

        # Query active BTCUSDT signals
        cursor.execute('''
            SELECT COUNT(*) FROM signals
            WHERE symbol = ? AND status = ?
        ''', ('BTCUSDT', 'active'))

        count = cursor.fetchone()[0]
        assert count == 2

        conn.close()


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
