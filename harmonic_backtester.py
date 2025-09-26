"""
Harmonic Pattern Backtesting System
====================================
Walk-forward simulation for testing harmonic pattern trading strategies.
Uses unformed patterns for entry signals and formed patterns for confirmation.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import json
from enum import Enum

# Import pattern detection modules
from comprehensive_abcd_patterns import detect_unformed_abcd_patterns
from comprehensive_xabcd_patterns import detect_comprehensive_xabcd_patterns
from gui_compatible_detection import (
    detect_gui_compatible_abcd_patterns,
    detect_gui_compatible_xabcd_patterns,
    detect_all_gui_patterns,
    simulate_gui_display
)
from extremum import find_extremum_points


class TradeDirection(Enum):
    """Trade direction based on pattern type"""
    LONG = "long"
    SHORT = "short"


@dataclass
class PatternSignal:
    """Represents a potential trading signal from an unformed pattern"""
    timestamp: pd.Timestamp
    pattern_type: str  # ABCD or XABCD
    pattern_name: str  # Gartley, Bat, Butterfly, etc.
    points: Dict[str, Tuple[datetime, float]]  # X, A, B, C points
    prz_zones: List[Tuple[float, float]]  # Predicted D zones
    timestamp: datetime  # When this prediction was made
    extremum_state: List  # State of extremums at prediction time


@dataclass
class BacktestResult:
    """Result of a single backtest comparison"""
    formed_pattern: Dict  # The actual formed pattern
    predictions: List[PatternPrediction]  # All predictions at point C
    successful_predictions: List[PatternPrediction]  # Predictions that hit
    success_rate: float
    mode: BacktestMode
    evolution_history: Optional[List] = None  # For evolution mode


class HarmonicBacktester:
    """Main backtesting engine for harmonic patterns"""

    def __init__(self, data: pd.DataFrame, mode: BacktestMode = BacktestMode.BOTH):
        """
        Initialize backtester

        Args:
            data: OHLC DataFrame with Date index
            mode: Backtesting mode to use
        """
        self.data = data
        self.mode = mode
        self.results = []
        self.statistics = {}

    def run_backtest(self) -> Dict:
        """
        Run the complete backtest

        Returns:
            Dictionary containing backtest results and statistics
        """
        print(f"\n{'='*60}")
        print(f"Starting Harmonic Pattern Backtest")
        print(f"Mode: {self.mode.value}")
        print(f"Data range: {self.data.index[0]} to {self.data.index[-1]}")
        print(f"Total bars: {len(self.data)}")
        print(f"{'='*60}\n")

        # Step 1: Detect all extremum points
        print("Step 1: Detecting extremum points...")
        all_extremums = detect_extremum_points(self.data, length=5)
        print(f"Found {len(all_extremums)} extremum points")

        # Step 2: Detect all formed patterns
        print("\nStep 2: Detecting formed patterns...")
        formed_patterns = self._detect_formed_patterns(all_extremums)
        print(f"Found {sum(len(p) for p in formed_patterns.values())} formed patterns")

        # Step 3: Run backtests based on mode
        if self.mode in [BacktestMode.SNAPSHOT, BacktestMode.BOTH]:
            print("\nStep 3a: Running Snapshot Mode backtest...")
            snapshot_results = self._run_snapshot_backtest(formed_patterns, all_extremums)
            self.results.extend(snapshot_results)

        if self.mode in [BacktestMode.EVOLUTION, BacktestMode.BOTH]:
            print("\nStep 3b: Running Evolution Mode backtest...")
            evolution_results = self._run_evolution_backtest(formed_patterns, all_extremums)
            self.results.extend(evolution_results)

        # Step 4: Calculate statistics
        print("\nStep 4: Calculating statistics...")
        self.statistics = self._calculate_statistics()

        return {
            'results': self.results,
            'statistics': self.statistics,
            'summary': self._generate_summary()
        }

    def _detect_formed_patterns(self, extremums: List) -> Dict:
        """Detect all formed patterns in the data - using same detection as main GUI"""
        patterns = {
            'strict_abcd': [],
            'strict_xabcd': []
        }

        # Detect strict ABCD patterns (same as main GUI)
        try:
            patterns['strict_abcd'] = detect_strict_abcd_patterns(
                extremums,
                self.data,
                log_details=False
            )
            print(f"  - Found {len(patterns['strict_abcd'])} formed ABCD patterns")
        except Exception as e:
            print(f"Error detecting ABCD patterns: {e}")

        # Detect strict XABCD patterns (same as main GUI)
        try:
            patterns['strict_xabcd'] = detect_strict_xabcd_patterns(
                extremums,
                self.data,
                log_details=False
            )
            print(f"  - Found {len(patterns['strict_xabcd'])} formed XABCD patterns")
        except Exception as e:
            print(f"Error detecting XABCD patterns: {e}")

        return patterns

    def _run_snapshot_backtest(self, formed_patterns: Dict, all_extremums: List) -> List[BacktestResult]:
        """
        Snapshot Mode: Test patterns as they existed at point C
        """
        results = []

        for pattern_type, patterns in formed_patterns.items():
            for pattern in patterns:
                # Get point C timestamp
                c_point = pattern.get('points', {}).get('C')
                if not c_point:
                    continue

                c_time = c_point.get('time')
                c_index = self._get_data_index(c_time)

                # Slice data up to point C
                data_at_c = self.data.iloc[:c_index + 1]
                extremums_at_c = [e for e in all_extremums
                                 if self._get_data_index(e[0]) <= c_index]

                # Detect unformed patterns at point C
                predictions = self._detect_unformed_patterns_at_point(
                    data_at_c,
                    extremums_at_c,
                    pattern
                )

                # Check which predictions were successful
                successful = self._check_prediction_success(predictions, pattern)

                # Create result
                result = BacktestResult(
                    formed_pattern=pattern,
                    predictions=predictions,
                    successful_predictions=successful,
                    success_rate=len(successful) / len(predictions) if predictions else 0,
                    mode=BacktestMode.SNAPSHOT
                )
                results.append(result)

        return results

    def _run_evolution_backtest(self, formed_patterns: Dict, all_extremums: List) -> List[BacktestResult]:
        """
        Evolution Mode: Track pattern evolution as new extremums form
        """
        results = []

        for pattern_type, patterns in formed_patterns.items():
            for pattern in patterns:
                # Get key points
                b_point = pattern.get('points', {}).get('B')
                c_point = pattern.get('points', {}).get('C')
                d_point = pattern.get('points', {}).get('D')

                if not all([b_point, c_point, d_point]):
                    continue

                b_time = b_point.get('time')
                c_time = c_point.get('time')
                d_time = d_point.get('time')

                # Track pattern evolution from B to D
                evolution_history = []
                predictions_all_versions = []

                # Find all extremums between B and D
                b_index = self._get_data_index(b_time)
                d_index = self._get_data_index(d_time)

                intermediate_extremums = [
                    e for e in all_extremums
                    if b_index < self._get_data_index(e[0]) < d_index
                ]

                # For each potential C point, create pattern version
                for ext in intermediate_extremums:
                    if ext[2] == c_point.get('is_high', True):  # Same type as C
                        # Create pattern version with this as C
                        version_data = self.data.iloc[:self._get_data_index(ext[0]) + 1]
                        version_extremums = [
                            e for e in all_extremums
                            if self._get_data_index(e[0]) <= self._get_data_index(ext[0])
                        ]

                        # Detect predictions for this version
                        predictions = self._detect_unformed_patterns_at_point(
                            version_data,
                            version_extremums,
                            pattern,
                            override_c=ext
                        )

                        evolution_history.append({
                            'c_point': ext,
                            'predictions': predictions
                        })
                        predictions_all_versions.extend(predictions)

                # Check which predictions were successful
                successful = self._check_prediction_success(predictions_all_versions, pattern)

                # Create result
                result = BacktestResult(
                    formed_pattern=pattern,
                    predictions=predictions_all_versions,
                    successful_predictions=successful,
                    success_rate=len(successful) / len(predictions_all_versions) if predictions_all_versions else 0,
                    mode=BacktestMode.EVOLUTION,
                    evolution_history=evolution_history
                )
                results.append(result)

        return results

    def _detect_unformed_patterns_at_point(self, data_slice: pd.DataFrame,
                                          extremums: List,
                                          reference_pattern: Dict,
                                          override_c: Optional[Tuple] = None) -> List[PatternPrediction]:
        """Detect all unformed patterns at a specific point in time"""
        predictions = []

        # Detect unformed ABCD patterns
        if 'ABCD' in str(reference_pattern.get('pattern_type', '')).upper():
            try:
                unformed_abcd = detect_comprehensive_unformed_abcd(
                    extremums,
                    data_slice,
                    log_details=False
                )

                for pattern in unformed_abcd:
                    if self._patterns_match_abc(pattern, reference_pattern, override_c):
                        pred = PatternPrediction(
                            pattern_name=pattern.get('name', 'Unknown'),
                            pattern_type='ABCD',
                            points=pattern.get('points', {}),
                            prz_zones=self._extract_prz_zones(pattern),
                            timestamp=data_slice.index[-1],
                            extremum_state=extremums.copy()
                        )
                        predictions.append(pred)

            except Exception as e:
                print(f"Error detecting unformed ABCD: {e}")

        # Detect unformed XABCD patterns
        else:
            try:
                unformed_xabcd = detect_comprehensive_unformed_xabcd(
                    extremums,
                    data_slice,
                    log_details=False
                )

                for pattern in unformed_xabcd:
                    if self._patterns_match_xabc(pattern, reference_pattern, override_c):
                        pred = PatternPrediction(
                            pattern_name=pattern.get('name', 'Unknown'),
                            pattern_type='XABCD',
                            points=pattern.get('points', {}),
                            prz_zones=self._extract_prz_zones(pattern),
                            timestamp=data_slice.index[-1],
                            extremum_state=extremums.copy()
                        )
                        predictions.append(pred)

            except Exception as e:
                print(f"Error detecting unformed XABCD: {e}")

        return predictions

    def _patterns_match_abc(self, pattern1: Dict, pattern2: Dict, override_c: Optional[Tuple] = None) -> bool:
        """Check if two ABCD patterns have matching A, B, C points"""
        p1_points = pattern1.get('points', {})
        p2_points = pattern2.get('points', {})

        # Match A and B points
        for point in ['A', 'B']:
            p1 = p1_points.get(point, {})
            p2 = p2_points.get(point, {})

            if abs(p1.get('price', 0) - p2.get('price', 0)) > 0.01:
                return False

        # Match C point (or use override)
        if override_c:
            p1_c = p1_points.get('C', {})
            if abs(p1_c.get('price', 0) - override_c[1]) > 0.01:
                return False
        else:
            p1_c = p1_points.get('C', {})
            p2_c = p2_points.get('C', {})
            if abs(p1_c.get('price', 0) - p2_c.get('price', 0)) > 0.01:
                return False

        return True

    def _patterns_match_xabc(self, pattern1: Dict, pattern2: Dict, override_c: Optional[Tuple] = None) -> bool:
        """Check if two XABCD patterns have matching X, A, B, C points"""
        p1_points = pattern1.get('points', {})
        p2_points = pattern2.get('points', {})

        # Match X, A, and B points
        for point in ['X', 'A', 'B']:
            p1 = p1_points.get(point, {})
            p2 = p2_points.get(point, {})

            if abs(p1.get('price', 0) - p2.get('price', 0)) > 0.01:
                return False

        # Match C point (or use override)
        if override_c:
            p1_c = p1_points.get('C', {})
            if abs(p1_c.get('price', 0) - override_c[1]) > 0.01:
                return False
        else:
            p1_c = p1_points.get('C', {})
            p2_c = p2_points.get('C', {})
            if abs(p1_c.get('price', 0) - p2_c.get('price', 0)) > 0.01:
                return False

        return True

    def _extract_prz_zones(self, pattern: Dict) -> List[Tuple[float, float]]:
        """Extract PRZ zones from an unformed pattern"""
        zones = []

        # Check for D_projected in points
        d_projected = pattern.get('points', {}).get('D_projected', {})

        if 'prz_zones' in d_projected:
            # ABCD pattern format
            for zone in d_projected.get('prz_zones', []):
                if isinstance(zone, (list, tuple)) and len(zone) >= 2:
                    zones.append((float(zone[0]), float(zone[1])))

        elif 'd_lines' in d_projected:
            # XABCD pattern format - create zones from lines
            d_lines = d_projected.get('d_lines', [])
            if d_lines:
                min_d = min(d_lines)
                max_d = max(d_lines)
                # Create zone with 0.5% tolerance
                tolerance = (max_d - min_d) * 0.005 if max_d > min_d else max_d * 0.005
                zones.append((min_d - tolerance, max_d + tolerance))

        return zones

    def _check_prediction_success(self, predictions: List[PatternPrediction],
                                 formed_pattern: Dict) -> List[PatternPrediction]:
        """Check which predictions successfully predicted the formed pattern's D point"""
        successful = []

        # Get actual D point
        d_point = formed_pattern.get('points', {}).get('D', {})
        d_price = d_point.get('price', 0)

        if not d_price:
            return successful

        # Check each prediction
        for prediction in predictions:
            # Check if D price falls within any PRZ zone
            for zone_min, zone_max in prediction.prz_zones:
                if zone_min <= d_price <= zone_max:
                    successful.append(prediction)
                    break  # Count only once per prediction

        return successful

    def _get_data_index(self, timestamp) -> int:
        """Get DataFrame index for a timestamp"""
        try:
            if isinstance(timestamp, (pd.Timestamp, datetime)):
                return self.data.index.get_loc(timestamp)
            return self.data.index.get_loc(pd.Timestamp(timestamp))
        except:
            # Find nearest
            return self.data.index.get_indexer([pd.Timestamp(timestamp)], method='nearest')[0]

    def _calculate_statistics(self) -> Dict:
        """Calculate comprehensive statistics from backtest results"""
        stats = {
            'total_patterns_tested': len(self.results),
            'by_mode': {},
            'by_pattern_type': defaultdict(lambda: {'total': 0, 'successful': 0}),
            'by_pattern_name': defaultdict(lambda: {'total': 0, 'successful': 0}),
            'overall_success_rate': 0,
            'best_patterns': [],
            'convergence_zones': 0
        }

        # Separate by mode
        for mode in BacktestMode:
            mode_results = [r for r in self.results if r.mode == mode]
            if mode_results:
                stats['by_mode'][mode.value] = {
                    'total': len(mode_results),
                    'avg_predictions': np.mean([len(r.predictions) for r in mode_results]),
                    'avg_success_rate': np.mean([r.success_rate for r in mode_results]),
                    'patterns_with_success': sum(1 for r in mode_results if r.success_rate > 0)
                }

        # Analyze by pattern type and name
        for result in self.results:
            pattern_type = result.formed_pattern.get('pattern_type', 'unknown')
            pattern_name = result.formed_pattern.get('name', 'unknown')

            stats['by_pattern_type'][pattern_type]['total'] += len(result.predictions)
            stats['by_pattern_type'][pattern_type]['successful'] += len(result.successful_predictions)

            stats['by_pattern_name'][pattern_name]['total'] += len(result.predictions)
            stats['by_pattern_name'][pattern_name]['successful'] += len(result.successful_predictions)

            # Count convergence zones (multiple patterns predicting same area)
            if len(result.successful_predictions) > 1:
                stats['convergence_zones'] += 1

        # Calculate overall success rate
        total_predictions = sum(len(r.predictions) for r in self.results)
        total_successful = sum(len(r.successful_predictions) for r in self.results)
        stats['overall_success_rate'] = (total_successful / total_predictions * 100) if total_predictions > 0 else 0

        # Find best performing patterns
        pattern_performance = []
        for name, data in stats['by_pattern_name'].items():
            if data['total'] > 0:
                success_rate = (data['successful'] / data['total']) * 100
                pattern_performance.append({
                    'name': name,
                    'success_rate': success_rate,
                    'total_predictions': data['total']
                })

        stats['best_patterns'] = sorted(pattern_performance,
                                       key=lambda x: x['success_rate'],
                                       reverse=True)[:10]

        return stats

    def _generate_summary(self) -> str:
        """Generate a human-readable summary of backtest results"""
        summary = []
        summary.append("\n" + "="*60)
        summary.append("HARMONIC PATTERN BACKTEST SUMMARY")
        summary.append("="*60)

        summary.append(f"\nOverall Statistics:")
        summary.append(f"  Total Patterns Tested: {self.statistics['total_patterns_tested']}")
        summary.append(f"  Overall Success Rate: {self.statistics['overall_success_rate']:.2f}%")
        summary.append(f"  Convergence Zones Found: {self.statistics['convergence_zones']}")

        if self.statistics.get('by_mode'):
            summary.append(f"\nResults by Mode:")
            for mode, data in self.statistics['by_mode'].items():
                summary.append(f"  {mode.upper()}:")
                summary.append(f"    - Patterns Tested: {data['total']}")
                summary.append(f"    - Avg Predictions per Pattern: {data['avg_predictions']:.1f}")
                summary.append(f"    - Avg Success Rate: {data['avg_success_rate']*100:.2f}%")
                summary.append(f"    - Patterns with Success: {data['patterns_with_success']}")

        if self.statistics.get('best_patterns'):
            summary.append(f"\nTop Performing Patterns:")
            for i, pattern in enumerate(self.statistics['best_patterns'][:5], 1):
                summary.append(f"  {i}. {pattern['name']}: {pattern['success_rate']:.2f}% "
                             f"({pattern['total_predictions']} predictions)")

        summary.append("\n" + "="*60)

        return "\n".join(summary)

    def export_results(self, filepath: str):
        """Export backtest results to JSON file"""
        export_data = {
            'metadata': {
                'backtest_date': datetime.now().isoformat(),
                'mode': self.mode.value,
                'data_range': f"{self.data.index[0]} to {self.data.index[-1]}",
                'total_bars': len(self.data)
            },
            'statistics': self.statistics,
            'detailed_results': []
        }

        # Convert results to serializable format
        for result in self.results[:100]:  # Limit to first 100 for file size
            export_data['detailed_results'].append({
                'formed_pattern': str(result.formed_pattern.get('name', 'Unknown')),
                'prediction_count': len(result.predictions),
                'successful_count': len(result.successful_predictions),
                'success_rate': result.success_rate,
                'mode': result.mode.value
            })

        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)

        print(f"Results exported to {filepath}")


def run_backtest_from_ui(data: pd.DataFrame, mode_str: str = "both") -> Dict:
    """
    Convenience function to run backtest from UI

    Args:
        data: OHLC DataFrame
        mode_str: "snapshot", "evolution", or "both"

    Returns:
        Backtest results dictionary
    """
    mode_map = {
        "snapshot": BacktestMode.SNAPSHOT,
        "evolution": BacktestMode.EVOLUTION,
        "both": BacktestMode.BOTH
    }

    mode = mode_map.get(mode_str.lower(), BacktestMode.BOTH)

    backtester = HarmonicBacktester(data, mode)
    results = backtester.run_backtest()

    # Optionally export results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = f"backtest_results_{timestamp}.json"
    backtester.export_results(export_path)

    return results


if __name__ == "__main__":
    # Test the backtester
    print("Harmonic Pattern Backtester Module Loaded")
    print("Use run_backtest_from_ui() to execute backtests from the main application")