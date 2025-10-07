"""
Pattern Detection Cache System
Provides intelligent caching for pattern detection to avoid redundant calculations

Features:
- Hash-based cache invalidation
- Automatic cache cleanup
- Memory-efficient storage
- Thread-safe operations
"""

import hashlib
import json
import threading
import time
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np


class PatternCache:
    """
    Thread-safe cache for pattern detection results.

    Caches patterns based on:
    - Extremum points hash
    - DataFrame hash (last N rows)
    - Detection parameters

    Automatically invalidates when data changes.
    """

    def __init__(self, max_cache_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize pattern cache.

        Args:
            max_cache_size: Maximum number of cache entries
            ttl_seconds: Time-to-live for cache entries (default 1 hour)
        """
        self._cache = {}
        self._lock = threading.Lock()
        self._max_size = max_cache_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def _compute_extremum_hash(self, extremum_points: List[Tuple]) -> str:
        """
        Compute hash of extremum points.

        Args:
            extremum_points: List of (timestamp, price, is_high, bar_index)

        Returns:
            SHA256 hash string
        """
        if not extremum_points:
            return ""

        # Convert to string representation for hashing
        # Only use last 500 points to avoid huge strings
        points_to_hash = extremum_points[-500:]

        data_str = ""
        for point in points_to_hash:
            # Include bar_index (element 3) and is_high (element 2) for uniqueness
            # When extremum=1, same bar can be both high and low
            bar_idx = point[3] if len(point) > 3 else 0
            is_high = point[2] if len(point) > 2 else False
            price = point[1] if len(point) > 1 else 0
            data_str += f"{bar_idx}_{is_high}_{price:.8f}|"

        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def _compute_df_hash(self, df: pd.DataFrame, last_n_rows: int = 100) -> str:
        """
        Compute hash of dataframe (last N rows for efficiency).

        Args:
            df: OHLC DataFrame
            last_n_rows: Number of recent rows to hash

        Returns:
            SHA256 hash string
        """
        if df is None or df.empty:
            return ""

        # Only hash recent data (last N rows)
        recent_df = df.tail(last_n_rows)

        # Create hash from OHLC values
        data_str = ""
        for idx, row in recent_df.iterrows():
            try:
                o = float(row.get('Open', 0))
                h = float(row.get('High', 0))
                l = float(row.get('Low', 0))
                c = float(row.get('Close', 0))
                data_str += f"{o:.8f}_{h:.8f}_{l:.8f}_{c:.8f}|"
            except (ValueError, TypeError):
                continue

        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def _compute_params_hash(self, **params) -> str:
        """
        Compute hash of detection parameters.

        Args:
            **params: Detection parameters (extremum, search_window, etc.)

        Returns:
            SHA256 hash string
        """
        # Sort parameters for consistent hashing
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.sha256(param_str.encode()).hexdigest()[:16]

    def _compute_cache_key(self, extremum_points: List[Tuple], df: pd.DataFrame,
                          pattern_type: str, **params) -> str:
        """
        Compute complete cache key.

        Args:
            extremum_points: Extremum points list
            df: OHLC DataFrame
            pattern_type: Type of pattern (formed_abcd, unformed_abcd, etc.)
            **params: Detection parameters

        Returns:
            Combined cache key
        """
        ext_hash = self._compute_extremum_hash(extremum_points)
        df_hash = self._compute_df_hash(df)
        param_hash = self._compute_params_hash(**params)

        return f"{pattern_type}_{ext_hash}_{df_hash}_{param_hash}"

    def get(self, extremum_points: List[Tuple], df: pd.DataFrame,
            pattern_type: str, **params) -> Optional[List[Dict]]:
        """
        Get cached patterns if available.

        Args:
            extremum_points: Extremum points list
            df: OHLC DataFrame
            pattern_type: Type of pattern
            **params: Detection parameters

        Returns:
            Cached patterns or None if not found
        """
        cache_key = self._compute_cache_key(extremum_points, df, pattern_type, **params)

        with self._lock:
            if cache_key in self._cache:
                entry = self._cache[cache_key]

                # Check TTL
                if time.time() - entry['timestamp'] < self._ttl:
                    self._hits += 1
                    return entry['patterns']
                else:
                    # Expired entry
                    del self._cache[cache_key]

            self._misses += 1
            return None

    def set(self, extremum_points: List[Tuple], df: pd.DataFrame,
            pattern_type: str, patterns: List[Dict], **params) -> None:
        """
        Cache pattern detection results.

        Args:
            extremum_points: Extremum points list
            df: OHLC DataFrame
            pattern_type: Type of pattern
            patterns: Detected patterns to cache
            **params: Detection parameters
        """
        cache_key = self._compute_cache_key(extremum_points, df, pattern_type, **params)

        with self._lock:
            # Enforce size limit (LRU-like eviction)
            if len(self._cache) >= self._max_size:
                # Remove oldest entry
                oldest_key = min(self._cache.keys(),
                               key=lambda k: self._cache[k]['timestamp'])
                del self._cache[oldest_key]

            self._cache[cache_key] = {
                'patterns': patterns,
                'timestamp': time.time()
            }

    def clear(self) -> None:
        """Clear all cached patterns."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def get_stats(self) -> Dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0

            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'total_requests': total_requests,
                'hit_rate': hit_rate
            }

    def remove_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        current_time = time.time()
        removed = 0

        with self._lock:
            keys_to_remove = [
                key for key, entry in self._cache.items()
                if current_time - entry['timestamp'] >= self._ttl
            ]

            for key in keys_to_remove:
                del self._cache[key]
                removed += 1

        return removed


# Global cache instance
_global_pattern_cache = None
_cache_lock = threading.Lock()


def get_pattern_cache() -> PatternCache:
    """
    Get global pattern cache instance (singleton).

    Returns:
        Global PatternCache instance
    """
    global _global_pattern_cache

    if _global_pattern_cache is None:
        with _cache_lock:
            if _global_pattern_cache is None:
                _global_pattern_cache = PatternCache(
                    max_cache_size=100,
                    ttl_seconds=3600  # 1 hour
                )

    return _global_pattern_cache


if __name__ == "__main__":
    # Test the cache system
    print("Testing Pattern Cache System...")

    # Create test data
    extremum_points = [
        (pd.Timestamp('2024-01-01'), 100.0, True, 0),
        (pd.Timestamp('2024-01-02'), 95.0, False, 1),
        (pd.Timestamp('2024-01-03'), 98.0, True, 2),
        (pd.Timestamp('2024-01-04'), 93.0, False, 3),
    ]

    df = pd.DataFrame({
        'Open': [100, 95, 98, 93],
        'High': [101, 96, 99, 94],
        'Low': [99, 94, 97, 92],
        'Close': [100, 95, 98, 93]
    })

    cache = get_pattern_cache()

    # Test cache miss
    result = cache.get(extremum_points, df, 'formed_abcd', extremum=3, search_window=20)
    print(f"Cache miss test: {result is None}")  # Should be True

    # Set cache
    test_patterns = [{'name': 'test_pattern', 'type': 'bullish'}]
    cache.set(extremum_points, df, 'formed_abcd', test_patterns, extremum=3, search_window=20)

    # Test cache hit
    result = cache.get(extremum_points, df, 'formed_abcd', extremum=3, search_window=20)
    print(f"Cache hit test: {result == test_patterns}")  # Should be True

    # Test stats
    stats = cache.get_stats()
    print(f"\nCache Statistics:")
    print(f"  Size: {stats['size']}/{stats['max_size']}")
    print(f"  Hits: {stats['hits']}")
    print(f"  Misses: {stats['misses']}")
    print(f"  Hit Rate: {stats['hit_rate']:.1f}%")

    print("\n✅ Pattern cache system test complete!")
