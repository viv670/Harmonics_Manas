"""
Pattern Detection Service

Business logic layer for pattern detection operations.
Separates detection logic from GUI and data access.
"""

import pandas as pd
from typing import List, Dict, Optional, Callable
from datetime import datetime
import logging

from pattern_cache import get_pattern_cache
from parallel_pattern_detector import detect_patterns_parallel
from pattern_validators import PriceContainmentValidator
from pattern_scoring import PatternStrengthScorer, filter_patterns_by_score
from exceptions import PatternDetectionError, ValidationError
from logging_config import get_logger


class PatternDetectionService:
    """
    Service for harmonic pattern detection operations.

    Handles all business logic related to pattern detection,
    validation, and scoring.
    """

    def __init__(self, use_cache: bool = True, use_parallel: bool = True):
        """
        Initialize pattern detection service.

        Args:
            use_cache: Whether to use pattern caching
            use_parallel: Whether to use parallel processing
        """
        self.use_cache = use_cache
        self.use_parallel = use_parallel
        self.cache = get_pattern_cache() if use_cache else None
        self.scorer = PatternStrengthScorer()
        self.logger = get_logger()

    def detect_patterns(
        self,
        df: pd.DataFrame,
        extremum_points: List[Dict],
        pattern_types: List[str],
        detection_methods: Dict[str, Callable],
        min_quality_score: int = 0,
        validate: bool = True
    ) -> List[Dict]:
        """
        Detect patterns with optional caching, parallel processing, and scoring.

        Args:
            df: OHLC DataFrame
            extremum_points: List of extremum points
            pattern_types: List of pattern types to detect
            detection_methods: Dict mapping pattern type to detection function
            min_quality_score: Minimum quality score (0-100)
            validate: Whether to validate patterns

        Returns:
            List of detected patterns
        """
        try:
            all_patterns = []

            # Use parallel processing if enabled and multiple pattern types
            if self.use_parallel and len(pattern_types) > 1:
                self.logger.info(f"Detecting {len(pattern_types)} pattern types in parallel")
                results = detect_patterns_parallel(
                    extremum_points,
                    df,
                    detection_methods
                )

                # Flatten results
                for pattern_type, patterns in results.items():
                    all_patterns.extend(patterns)

            else:
                # Sequential detection
                self.logger.info(f"Detecting {len(pattern_types)} pattern types sequentially")
                for pattern_type in pattern_types:
                    if pattern_type in detection_methods:
                        # Check cache first
                        if self.cache:
                            cached = self.cache.get(
                                extremum_points,
                                df,
                                pattern_type
                            )
                            if cached is not None:
                                self.logger.debug(f"Cache hit for {pattern_type}")
                                all_patterns.extend(cached)
                                continue

                        # Detect patterns
                        patterns = detection_methods[pattern_type](extremum_points, df)

                        # Cache results
                        if self.cache:
                            self.cache.set(extremum_points, df, pattern_type, patterns)

                        all_patterns.extend(patterns)

            # Validate patterns if requested
            if validate:
                all_patterns = self.validate_patterns(all_patterns, df)

            # Score and filter patterns
            if min_quality_score > 0:
                all_patterns = filter_patterns_by_score(
                    all_patterns,
                    df,
                    min_quality_score
                )

            self.logger.info(f"Detected {len(all_patterns)} patterns")
            return all_patterns

        except Exception as e:
            self.logger.error(f"Pattern detection failed: {e}")
            raise PatternDetectionError(f"Detection failed: {e}") from e

    def validate_patterns(
        self,
        patterns: List[Dict],
        df: pd.DataFrame
    ) -> List[Dict]:
        """
        Validate patterns using price containment rules.

        Args:
            patterns: List of patterns to validate
            df: OHLC DataFrame

        Returns:
            List of valid patterns
        """
        valid_patterns = []

        for pattern in patterns:
            try:
                is_valid = PriceContainmentValidator.validate_pattern(pattern, df)

                if is_valid:
                    pattern['validated'] = True
                    valid_patterns.append(pattern)
                else:
                    self.logger.debug(f"Pattern {pattern.get('name')} failed validation")

            except Exception as e:
                self.logger.warning(f"Validation error for pattern {pattern.get('name')}: {e}")
                continue

        return valid_patterns

    def score_patterns(
        self,
        patterns: List[Dict],
        df: pd.DataFrame
    ) -> List[Dict]:
        """
        Score pattern quality.

        Args:
            patterns: List of patterns
            df: OHLC DataFrame

        Returns:
            List of patterns with quality scores
        """
        for pattern in patterns:
            try:
                score = self.scorer.score_pattern(pattern, df)
                pattern['quality_score'] = score

                # Add score breakdown for detailed analysis
                breakdown = self.scorer.get_score_breakdown(pattern, df)
                pattern['score_breakdown'] = breakdown

            except Exception as e:
                self.logger.warning(f"Scoring error for pattern {pattern.get('name')}: {e}")
                pattern['quality_score'] = 0

        # Sort by quality score
        patterns.sort(key=lambda p: p.get('quality_score', 0), reverse=True)

        return patterns

    def find_best_pattern(
        self,
        df: pd.DataFrame,
        extremum_points: List[Dict],
        detection_methods: Dict[str, Callable],
        direction: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Find the highest quality pattern.

        Args:
            df: OHLC DataFrame
            extremum_points: List of extremum points
            detection_methods: Detection methods
            direction: Optional direction filter ('bullish' or 'bearish')

        Returns:
            Best pattern or None
        """
        # Detect all patterns
        patterns = self.detect_patterns(
            df,
            extremum_points,
            list(detection_methods.keys()),
            detection_methods,
            validate=True
        )

        # Filter by direction if specified
        if direction:
            patterns = [p for p in patterns if p.get('type') == direction]

        # Score patterns
        patterns = self.score_patterns(patterns, df)

        # Return best pattern
        return patterns[0] if patterns else None

    def get_pattern_statistics(
        self,
        patterns: List[Dict]
    ) -> Dict:
        """
        Get statistics about detected patterns.

        Args:
            patterns: List of patterns

        Returns:
            Statistics dictionary
        """
        if not patterns:
            return {
                'total': 0,
                'by_type': {},
                'by_direction': {},
                'avg_score': 0
            }

        # Count by type
        by_type = {}
        for pattern in patterns:
            ptype = pattern.get('name', 'Unknown')
            by_type[ptype] = by_type.get(ptype, 0) + 1

        # Count by direction
        by_direction = {}
        for pattern in patterns:
            direction = pattern.get('type', 'unknown')
            by_direction[direction] = by_direction.get(direction, 0) + 1

        # Average score
        scores = [p.get('quality_score', 0) for p in patterns]
        avg_score = sum(scores) / len(scores) if scores else 0

        return {
            'total': len(patterns),
            'by_type': by_type,
            'by_direction': by_direction,
            'avg_score': avg_score,
            'max_score': max(scores) if scores else 0,
            'min_score': min(scores) if scores else 0
        }

    def clear_cache(self):
        """Clear pattern detection cache"""
        if self.cache:
            self.cache.clear()
            self.logger.info("Pattern cache cleared")

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if self.cache:
            return self.cache.get_stats()
        return {'hits': 0, 'misses': 0, 'size': 0}


if __name__ == "__main__":
    print("Pattern Detection Service initialized")
    print()

    # Example usage
    service = PatternDetectionService(use_cache=True, use_parallel=True)

    # Mock data
    dates = pd.date_range('2024-01-01', periods=100)
    df = pd.DataFrame({
        'High': range(100, 200),
        'Low': range(90, 190),
        'Close': range(95, 195),
        'Volume': [1000] * 100
    }, index=dates)

    extremum = [
        {'index': 10, 'price': 100, 'type': 'low'},
        {'index': 20, 'price': 110, 'type': 'high'},
    ]

    print("✅ Pattern Detection Service ready!")
