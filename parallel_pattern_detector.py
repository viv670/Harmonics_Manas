"""
Parallel Pattern Detection System
Detects all pattern types simultaneously using concurrent processing

Features:
- Parallel detection of all 4 pattern types
- Thread pool executor for optimal CPU utilization
- Error isolation (one pattern type failure doesn't affect others)
- Progress tracking for UI feedback
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional, Callable
import pandas as pd
import time


class ParallelPatternDetector:
    """
    Detect multiple pattern types in parallel for maximum performance.

    Uses ThreadPoolExecutor to run pattern detection methods concurrently.
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize parallel detector.

        Args:
            max_workers: Maximum number of parallel workers (default: 4)
        """
        self.max_workers = max_workers
        self._results = {}
        self._errors = {}

    def detect_all_patterns(
        self,
        extremum_points: List[Tuple],
        df: pd.DataFrame,
        detection_methods: Dict[str, Callable],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, List[Dict]]:
        """
        Detect all pattern types in parallel.

        Args:
            extremum_points: List of (timestamp, price, is_high, bar_index)
            df: OHLC DataFrame
            detection_methods: Dict mapping pattern type to detection function
                Example: {
                    'formed_abcd': lambda: detector.detect_formed_abcd(),
                    'unformed_abcd': lambda: detector.detect_unformed_abcd(),
                    'formed_xabcd': lambda: detector.detect_formed_xabcd(),
                    'unformed_xabcd': lambda: detector.detect_unformed_xabcd()
                }
            progress_callback: Optional callback(pattern_type, status) for progress

        Returns:
            Dictionary mapping pattern type to list of detected patterns
            Example: {
                'formed_abcd': [...],
                'unformed_abcd': [...],
                'formed_xabcd': [...],
                'unformed_xabcd': [...]
            }
        """
        self._results = {}
        self._errors = {}

        start_time = time.time()

        # Submit all detection tasks to thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Map futures to pattern types
            future_to_pattern = {}

            for pattern_type, detection_func in detection_methods.items():
                if progress_callback:
                    progress_callback(pattern_type, 'started')

                future = executor.submit(self._safe_detect, pattern_type, detection_func)
                future_to_pattern[future] = pattern_type

            # Collect results as they complete
            for future in as_completed(future_to_pattern):
                pattern_type = future_to_pattern[future]

                try:
                    patterns = future.result()
                    self._results[pattern_type] = patterns

                    if progress_callback:
                        progress_callback(pattern_type, 'completed', len(patterns))

                except Exception as e:
                    self._errors[pattern_type] = str(e)

                    if progress_callback:
                        progress_callback(pattern_type, 'error', error=str(e))

        elapsed_time = time.time() - start_time

        # Log summary
        total_patterns = sum(len(patterns) for patterns in self._results.values())
        print(f"\n✅ Parallel Pattern Detection Complete")
        print(f"   Time: {elapsed_time:.2f}s")
        print(f"   Total patterns: {total_patterns}")
        print(f"   Breakdown:")
        for pattern_type, patterns in self._results.items():
            print(f"     - {pattern_type}: {len(patterns)}")

        if self._errors:
            print(f"   Errors: {len(self._errors)}")
            for pattern_type, error in self._errors.items():
                print(f"     - {pattern_type}: {error}")

        return self._results

    def _safe_detect(self, pattern_type: str, detection_func: Callable) -> List[Dict]:
        """
        Safely execute detection function with error handling.

        Args:
            pattern_type: Name of pattern type
            detection_func: Function to call for detection

        Returns:
            List of detected patterns (empty list on error)
        """
        try:
            print(f"🔍 Starting {pattern_type} detection...")
            start = time.time()

            patterns = detection_func()

            elapsed = time.time() - start
            print(f"✓ {pattern_type}: {len(patterns)} patterns in {elapsed:.2f}s")

            return patterns if patterns is not None else []

        except Exception as e:
            print(f"✗ {pattern_type} failed: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_results(self) -> Dict[str, List[Dict]]:
        """
        Get detection results.

        Returns:
            Dictionary mapping pattern type to patterns
        """
        return self._results.copy()

    def get_errors(self) -> Dict[str, str]:
        """
        Get detection errors.

        Returns:
            Dictionary mapping pattern type to error message
        """
        return self._errors.copy()

    def get_all_patterns(self) -> List[Dict]:
        """
        Get all detected patterns as a single list.

        Returns:
            Combined list of all patterns from all types
        """
        all_patterns = []
        for patterns in self._results.values():
            all_patterns.extend(patterns)
        return all_patterns


def detect_patterns_parallel(
    extremum_points: List[Tuple],
    df: pd.DataFrame,
    detector_object,
    progress_callback: Optional[Callable] = None
) -> Dict[str, List[Dict]]:
    """
    Convenience function to detect all patterns in parallel.

    Args:
        extremum_points: Extremum points list
        df: OHLC DataFrame
        detector_object: PatternDetector instance with detection methods
        progress_callback: Optional progress callback

    Returns:
        Dictionary of patterns by type
    """
    parallel_detector = ParallelPatternDetector(max_workers=4)

    # Create detection method map
    detection_methods = {
        'formed_abcd': detector_object.detect_abcd_patterns,
        'formed_abcd_strict': detector_object.detect_formed_abcd_patterns,
        'formed_xabcd': detector_object.detect_formed_xabcd_patterns,
        'unformed_abcd': detector_object.detect_unformed_patterns,
        'unformed_xabcd': detector_object.detect_unformed_xabcd_patterns,
    }

    results = parallel_detector.detect_all_patterns(
        extremum_points,
        df,
        detection_methods,
        progress_callback
    )

    return results


if __name__ == "__main__":
    print("Testing Parallel Pattern Detection...")

    # Mock detection functions for testing
    import random
    import time as _time

    def mock_detect_formed_abcd():
        _time.sleep(random.uniform(0.5, 1.5))  # Simulate work
        return [{'name': 'ABCD_1', 'type': 'formed'}] * random.randint(1, 5)

    def mock_detect_unformed_abcd():
        _time.sleep(random.uniform(0.5, 1.5))
        return [{'name': 'ABCD_2', 'type': 'unformed'}] * random.randint(1, 5)

    def mock_detect_formed_xabcd():
        _time.sleep(random.uniform(0.5, 1.5))
        return [{'name': 'Gartley', 'type': 'formed'}] * random.randint(1, 5)

    def mock_detect_unformed_xabcd():
        _time.sleep(random.uniform(0.5, 1.5))
        return [{'name': 'Butterfly', 'type': 'unformed'}] * random.randint(1, 5)

    detection_methods = {
        'formed_abcd': mock_detect_formed_abcd,
        'unformed_abcd': mock_detect_unformed_abcd,
        'formed_xabcd': mock_detect_formed_xabcd,
        'unformed_xabcd': mock_detect_unformed_xabcd,
    }

    def progress_callback(pattern_type, status, count=0, error=None):
        if status == 'started':
            print(f"  → {pattern_type}: Starting...")
        elif status == 'completed':
            print(f"  ✓ {pattern_type}: Found {count} patterns")
        elif status == 'error':
            print(f"  ✗ {pattern_type}: Error - {error}")

    detector = ParallelPatternDetector(max_workers=4)
    results = detector.detect_all_patterns(
        [], None, detection_methods, progress_callback
    )

    print(f"\n📊 Results:")
    print(f"  Total pattern types: {len(results)}")
    print(f"  Total patterns: {len(detector.get_all_patterns())}")

    print("\n✅ Parallel detection test complete!")
