"""
Improved Pattern Display System for Harmonic Pattern Detection
Implements unified data structures, pagination, and optimized rendering
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import pyqtgraph as pg
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSpinBox, QCheckBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QFrame, QSlider,
    QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor

# Configuration
MAX_PATTERNS_PER_PAGE = 20
MAX_PATTERNS_TO_RENDER = 75  # Increased to show all patterns on a page
PATTERN_SCORE_THRESHOLD = 0.5

class PatternCategory(Enum):
    """Pattern categories for classification"""
    FORMED_ABCD = "formed_abcd"
    FORMED_XABCD = "formed_xabcd"
    UNFORMED_ABCD = "unformed_abcd"
    UNFORMED_XABCD = "unformed_xabcd"

class PatternDirection(Enum):
    """Pattern direction"""
    BULLISH = "bullish"
    BEARISH = "bearish"

@dataclass
class UnifiedPatternPoint:
    """Unified representation of a pattern point"""
    name: str  # X, A, B, C, D, D_projected
    time: pd.Timestamp
    price: float
    index: int
    is_projected: bool = False

@dataclass
class UnifiedPattern:
    """Unified pattern data structure for all pattern types"""
    # Core identification
    pattern_id: str
    name: str
    category: PatternCategory
    direction: PatternDirection

    # Pattern points (unified structure)
    points: Dict[str, UnifiedPatternPoint]

    # Projections for unformed patterns
    projections: List[Dict[str, Any]] = field(default_factory=list)
    prz_zones: List[Tuple[float, float]] = field(default_factory=list)

    # Pattern metrics
    ratios: Dict[str, float] = field(default_factory=dict)
    score: float = 0.0  # Pattern quality score (0-1)
    confidence: float = 0.0  # Confidence level (0-1)

    # Metadata
    detection_time: pd.Timestamp = None
    source_algorithm: str = ""

    def get_time_range(self) -> Tuple[pd.Timestamp, pd.Timestamp]:
        """Get the time range covered by this pattern"""
        times = [p.time for p in self.points.values() if p.time is not None]
        if times:
            return min(times), max(times)
        return None, None

    def get_point_indices(self) -> Dict[str, int]:
        """Get indices of all pattern points"""
        indices = {}
        for point_name, point in self.points.items():
            if not point.is_projected:
                indices[point_name] = point.index
        return indices

    def get_price_range(self) -> Tuple[float, float]:
        """Get the price range covered by this pattern"""
        prices = [p.price for p in self.points.values() if p.price is not None]
        if prices:
            return min(prices), max(prices)
        return None, None

    def overlaps_with(self, other: 'UnifiedPattern', time_threshold: int = 5,
                      min_shared_points: int = 2) -> bool:
        """Check if this pattern overlaps with another pattern

        Args:
            other: Another pattern to compare
            time_threshold: Maximum time difference for points to be considered shared
            min_shared_points: Minimum number of shared points required for overlap
        """
        # Check time overlap
        t1_min, t1_max = self.get_time_range()
        t2_min, t2_max = other.get_time_range()

        if t1_min and t2_min:
            # Convert to indices for comparison
            time_overlap = not (t1_max < t2_min or t2_max < t1_min)

            # Special case: time-based clustering (0 shared points required)
            if min_shared_points == 0:
                return time_overlap

            # Check if they share similar points
            if time_overlap:
                shared_points = 0
                # Check all possible points including X and D
                for point_name in ['X', 'A', 'B', 'C', 'D']:
                    if point_name in self.points and point_name in other.points:
                        p1 = self.points[point_name]
                        p2 = other.points[point_name]
                        if p1 and p2 and abs(p1.index - p2.index) <= time_threshold:
                            shared_points += 1

                return shared_points >= min_shared_points

        return False

class PatternScorer:
    """Score and rank patterns based on quality metrics"""

    @staticmethod
    def calculate_score(pattern: UnifiedPattern) -> float:
        """Calculate a quality score for a pattern (0-1)"""
        score = 0.0
        weights = {
            'ratio_accuracy': 0.3,
            'pattern_completion': 0.2,
            'time_symmetry': 0.2,
            'volume_confirmation': 0.1,
            'pattern_type': 0.2
        }

        # 1. Ratio accuracy (how close ratios are to ideal)
        ratio_score = PatternScorer._score_ratios(pattern)
        score += ratio_score * weights['ratio_accuracy']

        # 2. Pattern completion (formed vs unformed)
        if pattern.category in [PatternCategory.FORMED_ABCD, PatternCategory.FORMED_XABCD]:
            score += 1.0 * weights['pattern_completion']
        else:
            score += 0.5 * weights['pattern_completion']

        # 3. Time symmetry (even spacing between points)
        time_score = PatternScorer._score_time_symmetry(pattern)
        score += time_score * weights['time_symmetry']

        # 4. Pattern type preference (some patterns are more reliable)
        type_score = PatternScorer._score_pattern_type(pattern)
        score += type_score * weights['pattern_type']

        # 5. Volume confirmation (placeholder - would need volume data)
        score += 0.5 * weights['volume_confirmation']

        return min(1.0, max(0.0, score))

    @staticmethod
    def _score_ratios(pattern: UnifiedPattern) -> float:
        """Score based on how close ratios are to ideal values"""
        if not pattern.ratios:
            return 0.5

        # Example: Check if ratios are within acceptable ranges
        score = 0.0
        ratio_count = 0

        for ratio_name, ratio_value in pattern.ratios.items():
            if isinstance(ratio_value, (int, float)):
                # Score based on common harmonic ratios
                ideal_ratios = [38.2, 50.0, 61.8, 78.6, 88.6, 100.0, 127.2, 161.8, 224.0, 261.8]
                min_diff = min(abs(ratio_value - ideal) for ideal in ideal_ratios)

                # Score inversely proportional to difference from ideal
                if min_diff < 5:
                    score += 1.0
                elif min_diff < 10:
                    score += 0.7
                elif min_diff < 15:
                    score += 0.4
                else:
                    score += 0.1

                ratio_count += 1

        return score / max(1, ratio_count)

    @staticmethod
    def _score_time_symmetry(pattern: UnifiedPattern) -> float:
        """Score based on time symmetry between legs"""
        points = ['X', 'A', 'B', 'C', 'D'] if 'X' in pattern.points else ['A', 'B', 'C', 'D']

        if len(points) < 3:
            return 0.5

        # Calculate time differences between consecutive points
        time_diffs = []
        for i in range(len(points) - 1):
            if points[i] in pattern.points and points[i+1] in pattern.points:
                p1 = pattern.points[points[i]]
                p2 = pattern.points[points[i+1]]
                time_diffs.append(abs(p2.index - p1.index))

        if len(time_diffs) < 2:
            return 0.5

        # Calculate coefficient of variation (lower is better)
        mean_diff = np.mean(time_diffs)
        std_diff = np.std(time_diffs)

        if mean_diff > 0:
            cv = std_diff / mean_diff
            # Convert CV to score (0 CV = 1.0 score, high CV = low score)
            score = max(0.0, 1.0 - cv)
            return score

        return 0.5

    @staticmethod
    def _score_pattern_type(pattern: UnifiedPattern) -> float:
        """Score based on pattern type reliability"""
        # High reliability patterns
        high_reliability = ['Gartley', 'Bat', 'Butterfly', 'Crab', 'AB=CD']
        medium_reliability = ['Shark', 'Cypher', 'Three-Drive']

        pattern_base = pattern.name.split('_')[0] if '_' in pattern.name else pattern.name

        for high_pattern in high_reliability:
            if high_pattern.lower() in pattern_base.lower():
                return 1.0

        for med_pattern in medium_reliability:
            if med_pattern.lower() in pattern_base.lower():
                return 0.7

        return 0.4  # Other patterns

class PatternClusterer:
    """Cluster overlapping patterns to reduce visual clutter"""

    @staticmethod
    def cluster_patterns(patterns: List[UnifiedPattern],
                        mode: str = "share_2",
                        time_threshold: int = 5) -> List[List[UnifiedPattern]]:
        """Group overlapping patterns into clusters based on selected mode

        Args:
            patterns: List of patterns to cluster
            mode: Clustering mode - 'none', 'share_4', 'share_3', 'share_2', 'share_1', 'pattern_type'
            time_threshold: Time difference threshold for shared points

        Returns:
            List of pattern clusters
        """
        if not patterns or mode == "none":
            # No clustering - return each pattern as its own cluster
            return [[p] for p in patterns]

        # Special handling for pattern_type clustering
        if mode == "pattern_type":
            return PatternClusterer._cluster_by_pattern_type(patterns)

        # Determine min_shared_points based on mode
        if mode == "share_4":
            min_shared_points = 4  # 4+ shared points (X,A,B,C or A,B,C,D)
        elif mode == "share_3":
            min_shared_points = 3  # 3+ shared points
        elif mode == "share_2":
            min_shared_points = 2  # 2+ shared points (default)
        elif mode == "share_1":
            min_shared_points = 1  # 1+ shared point
        else:
            # Backwards compatibility for old modes
            if mode == "strict":
                min_shared_points = 3
            elif mode == "moderate":
                min_shared_points = 2
            elif mode == "loose":
                min_shared_points = 1
            else:
                min_shared_points = 2  # Default

        clusters = []
        used = set()

        for i, pattern in enumerate(patterns):
            if i in used:
                continue

            # Start new cluster
            cluster = [pattern]
            used.add(i)

            # Find all overlapping patterns
            for j, other in enumerate(patterns[i+1:], start=i+1):
                if j in used:
                    continue

                # Check if pattern overlaps with any pattern in current cluster
                for cluster_pattern in cluster:
                    if other.overlaps_with(cluster_pattern, time_threshold, min_shared_points):
                        cluster.append(other)
                        used.add(j)
                        break

            clusters.append(cluster)

        return clusters

    @staticmethod
    def _cluster_by_pattern_type(patterns: List[UnifiedPattern]) -> List[List[UnifiedPattern]]:
        """Cluster patterns by their pattern type (e.g., all Bat patterns together)"""
        from collections import defaultdict

        type_clusters = defaultdict(list)
        for pattern in patterns:
            # Extract base pattern type (e.g., "Bat" from "Bat_bullish")
            pattern_type = pattern.name.split('_')[0] if '_' in pattern.name else pattern.name
            type_clusters[pattern_type].append(pattern)

        # Convert to list of clusters
        return list(type_clusters.values())

    @staticmethod
    def get_cluster_representative(cluster: List[UnifiedPattern]) -> UnifiedPattern:
        """Get the best representative pattern from a cluster"""
        if not cluster:
            return None

        # Return pattern with highest score
        return max(cluster, key=lambda p: p.score)

class ImprovedAllPatternsWindow(QMainWindow):
    """Improved window for displaying patterns with pagination and optimization"""

    def __init__(self, parent, data, patterns_dict, extremum_points):
        try:
            super().__init__()
            print("ImprovedAllPatternsWindow __init__ called")
            print(f"Data shape: {data.shape if hasattr(data, 'shape') else len(data) if data is not None else 'None'}")
            print(f"Patterns dict keys: {list(patterns_dict.keys()) if patterns_dict else 'None'}")
            print(f"Extremum points: {len(extremum_points) if extremum_points else 0}")

            # Check for invalid data
            if data is None or (hasattr(data, 'empty') and data.empty):
                print("WARNING: Data is None or empty")
                self.data = pd.DataFrame()
            else:
                self.data = data

            if extremum_points is None:
                print("WARNING: extremum_points is None")
                self.extremum_points = []
            else:
                self.extremum_points = extremum_points

            # Convert patterns to unified format
            print(f"Converting patterns to unified format...")
            print(f"Pattern types received: {patterns_dict.keys() if patterns_dict else 'None'}")
            for ptype, plist in patterns_dict.items():
                if isinstance(plist, list):
                    print(f"  {ptype}: {len(plist)} patterns")

            try:
                self.unified_patterns = self.convert_to_unified_patterns(patterns_dict)
                print(f"Total unified patterns created: {len(self.unified_patterns)}")
            except Exception as e:
                print(f"ERROR converting patterns: {e}")
                import traceback
                print(traceback.format_exc())
                self.unified_patterns = []

            # Score and rank patterns
            try:
                print(f"Scoring patterns...")
                self.score_patterns()
            except Exception as e:
                print(f"ERROR scoring patterns: {e}")
                import traceback
                print(traceback.format_exc())

            # Cluster patterns
            try:
                print(f"Clustering patterns...")
                self.pattern_clusters = PatternClusterer.cluster_patterns(self.unified_patterns)
                print(f"Created {len(self.pattern_clusters)} pattern clusters")
            except Exception as e:
                print(f"ERROR clustering patterns: {e}")
                import traceback
                print(traceback.format_exc())
                self.pattern_clusters = []

            # Pagination state
            self.current_page = 0
            self.patterns_per_page = MAX_PATTERNS_PER_PAGE
            self.filtered_patterns = self.unified_patterns.copy()

            # UI elements
            self.pattern_lines = []
            self.pattern_labels = []

            self.setWindowTitle("Improved Pattern Viewer")
            self.setGeometry(200, 200, 1400, 900)

            try:
                print("Initializing UI...")
                self.initUI()
            except Exception as e:
                print(f"ERROR initializing UI: {e}")
                import traceback
                print(traceback.format_exc())
                raise

            try:
                print("Updating display...")
                self.update_display()
            except Exception as e:
                print(f"ERROR updating display: {e}")
                import traceback
                print(traceback.format_exc())
                raise

        except Exception as e:
            print(f"CRITICAL ERROR in ImprovedAllPatternsWindow.__init__: {e}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error args: {e.args}")
            import traceback
            print(f"Full traceback:\n{traceback.format_exc()}")
            raise

    def convert_to_unified_patterns(self, patterns_dict: Dict) -> List[UnifiedPattern]:
        """Convert legacy pattern format to unified format"""
        unified = []
        pattern_id = 0

        for ptype, plist in patterns_dict.items():
            for pattern in plist:
                if not isinstance(pattern, dict):
                    continue

                try:
                    # Determine category
                    if ptype == 'abcd':
                        category = PatternCategory.FORMED_ABCD
                    elif ptype == 'xabcd':
                        category = PatternCategory.FORMED_XABCD
                    elif ptype == 'unformed':
                        category = PatternCategory.UNFORMED_ABCD
                    elif ptype == 'unformed_xabcd':
                        category = PatternCategory.UNFORMED_XABCD
                    else:
                        continue

                    # Determine direction
                    pattern_name = pattern.get('name', '').lower()
                    direction = PatternDirection.BULLISH if 'bull' in pattern_name else PatternDirection.BEARISH

                    # Convert points - handle both regular and indices-based patterns
                    unified_points = {}

                    # First check for indices (used by XABCD patterns and unformed ABCD)
                    # IMPORTANT: indices refer to positions in extremum_points array, NOT data indices!
                    if 'indices' in pattern:
                        indices = pattern['indices']  # This is a LIST like [0, 1, 2], [0, 1, 2, 3] or [0, 1, 2, 3, 4]
                        points = pattern.get('points', {})

                        # Determine point mapping based on pattern type and indices length
                        if category == PatternCategory.UNFORMED_ABCD and len(indices) == 3:
                            # Unformed ABCD has only A, B, C points
                            point_mapping = {'A': 0, 'B': 1, 'C': 2}
                        elif category == PatternCategory.UNFORMED_XABCD and len(indices) == 4:
                            # Unformed XABCD has X, A, B, C (no D)
                            point_mapping = {'X': 0, 'A': 1, 'B': 2, 'C': 3}
                        elif category in [PatternCategory.FORMED_ABCD] and len(indices) == 4:
                            # Formed ABCD has A, B, C, D points
                            point_mapping = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
                        elif category in [PatternCategory.FORMED_XABCD] and len(indices) == 5:
                            # Formed XABCD has X, A, B, C, D points
                            point_mapping = {'X': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4}
                        else:
                            # Debug output for unexpected cases
                            print(f"WARNING: Unexpected indices configuration - category: {category}, indices length: {len(indices)}")
                            point_mapping = {}

                        # Map indices to actual data indices
                        for point_name, idx_position in point_mapping.items():
                            if idx_position < len(indices):
                                # Get actual data index from extremum index
                                ext_idx = indices[idx_position]

                                # Calculate actual index in data
                                if ext_idx < len(self.extremum_points):
                                    ext_point = self.extremum_points[ext_idx]

                                    # Handle different formats of extremum points
                                    if isinstance(ext_point, dict):
                                        timestamp = ext_point.get('time')
                                        price = ext_point.get('price', 0)
                                        is_high = ext_point.get('is_high', False)
                                    elif isinstance(ext_point, (list, tuple)) and len(ext_point) >= 2:
                                        timestamp = ext_point[0]
                                        price = ext_point[1]
                                        # Check if there's a third element indicating is_high
                                        is_high = ext_point[2] if len(ext_point) > 2 else False
                                    else:
                                        continue

                                    # For patterns, always use the price from points data if available
                                    # This ensures we get the correct high/low value
                                    if point_name in points:
                                        point_data = points[point_name]
                                        if isinstance(point_data, dict):
                                            # Override with the price from the pattern data
                                            if 'price' in point_data:
                                                price = point_data['price']
                                            # Also use the time from points if available
                                            if 'time' in point_data:
                                                timestamp = point_data['time']

                                    try:
                                        # Try to find the exact match in data
                                        if hasattr(self.data.index, 'get_loc'):
                                            try:
                                                data_idx = self.data.index.get_loc(timestamp)
                                            except KeyError:
                                                # Search for nearest if exact not found
                                                min_diff = float('inf')
                                                data_idx = 0
                                                for idx, t in enumerate(self.data.index):
                                                    try:
                                                        diff = abs((t - timestamp).total_seconds())
                                                        if diff < min_diff:
                                                            min_diff = diff
                                                            data_idx = idx
                                                    except:
                                                        continue
                                        else:
                                            # Fallback for different index types
                                            data_idx = list(self.data.index).index(timestamp)
                                    except Exception as e:
                                        print(f"Error finding data index for timestamp {timestamp}: {e}")
                                        data_idx = ext_idx  # Ultimate fallback

                                    unified_points[point_name] = UnifiedPatternPoint(
                                        name=point_name,
                                        time=timestamp,
                                        price=price,
                                        index=data_idx,
                                        is_projected=False
                                    )

                    # Then handle regular points format
                    elif 'points' in pattern:
                        for point_name, point_data in pattern['points'].items():
                            if isinstance(point_data, dict) and point_name != 'D_projected':
                                # Get time and calculate index
                                time_val = point_data.get('time')
                                index_val = point_data.get('index')

                                if time_val is not None and index_val is None:
                                    # Calculate index from time
                                    try:
                                        # Try exact match first
                                        index_val = self.data.index.get_loc(time_val)
                                    except KeyError:
                                        # If not found, search manually for nearest
                                        try:
                                            min_diff = float('inf')
                                            index_val = 0
                                            for idx, t in enumerate(self.data.index):
                                                diff = abs((t - time_val).total_seconds())
                                                if diff < min_diff:
                                                    min_diff = diff
                                                    index_val = idx
                                        except:
                                            index_val = 0
                                    except Exception as e:
                                        print(f"Error finding index for time {time_val}: {e}")
                                        index_val = 0

                                unified_points[point_name] = UnifiedPatternPoint(
                                    name=point_name,
                                    time=time_val,
                                    price=point_data.get('price', 0),
                                    index=index_val or 0,
                                    is_projected=False
                                )

                    # Handle projections for unformed patterns
                    projections = []
                    prz_zones = []

                    if 'points' in pattern and 'D_projected' in pattern['points']:
                        d_proj = pattern['points']['D_projected']

                        if isinstance(d_proj, dict):
                            # Handle PRZ zones (unformed ABCD)
                            if 'prz_zones' in d_proj:
                                zones = d_proj['prz_zones']
                                if isinstance(zones, list):
                                    for zone in zones:
                                        if isinstance(zone, dict) and 'min' in zone and 'max' in zone:
                                            prz_zones.append((zone['min'], zone['max']))
                                        elif isinstance(zone, (list, tuple)) and len(zone) >= 2:
                                            prz_zones.append((zone[0], zone[1]))

                            # Handle D lines (unformed XABCD)
                            elif 'd_lines' in d_proj:
                                d_lines = d_proj['d_lines']
                                if isinstance(d_lines, list):
                                    projections = [{'price': p, 'type': 'line'} for p in d_lines if isinstance(p, (int, float))]
                                    if category == PatternCategory.UNFORMED_XABCD:
                                        print(f"Found {len(projections)} D lines for unformed XABCD pattern {pattern.get('name', 'unknown')}")

                            # Handle single price
                            elif 'price' in d_proj:
                                projections = [{'price': d_proj['price'], 'type': 'single'}]

                    # Only create pattern if we have at least 2 points
                    if len(unified_points) >= 2:
                        # Create unified pattern
                        unified_pattern = UnifiedPattern(
                            pattern_id=f"pattern_{pattern_id}",
                            name=pattern.get('name', 'Unknown'),
                            category=category,
                            direction=direction,
                            points=unified_points,
                            projections=projections,
                            prz_zones=prz_zones,
                            ratios=pattern.get('ratios', {}),
                            source_algorithm=ptype
                        )

                        unified.append(unified_pattern)
                        pattern_id += 1
                    else:
                        print(f"Skipping pattern {pattern.get('name', 'unknown')} - insufficient points ({len(unified_points)})")

                except Exception as e:
                    print(f"Error converting pattern {pattern.get('name', 'unknown')}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue

        return unified

    def score_patterns(self):
        """Calculate scores for all patterns"""
        scorer = PatternScorer()
        for pattern in self.unified_patterns:
            pattern.score = scorer.calculate_score(pattern)

        # Sort by score
        self.unified_patterns.sort(key=lambda p: p.score, reverse=True)

    def initUI(self):
        """Initialize the user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left side: Chart
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)

        # Chart
        self.chart = pg.PlotWidget()
        self.chart.showGrid(x=True, y=True, alpha=0.3)
        self.chart.setLabel('left', 'Price')
        self.chart.setLabel('bottom', 'Time')
        chart_layout.addWidget(self.chart)

        # Pagination controls
        pagination_widget = QWidget()
        pagination_layout = QHBoxLayout(pagination_widget)

        self.prev_btn = QPushButton("← Previous Page")
        self.prev_btn.clicked.connect(self.previous_page)
        pagination_layout.addWidget(self.prev_btn)

        self.page_label = QLabel("Page 1 of 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pagination_layout.addWidget(self.page_label)

        self.next_btn = QPushButton("Next Page →")
        self.next_btn.clicked.connect(self.next_page)
        pagination_layout.addWidget(self.next_btn)

        # Patterns per page selector
        pagination_layout.addWidget(QLabel("Patterns per page:"))
        self.per_page_spin = QSpinBox()
        self.per_page_spin.setRange(5, 50)
        self.per_page_spin.setValue(MAX_PATTERNS_PER_PAGE)
        self.per_page_spin.valueChanged.connect(self.on_per_page_changed)
        pagination_layout.addWidget(self.per_page_spin)

        chart_layout.addWidget(pagination_widget)

        # Info label - improved readability
        self.info_label = QLabel("Patterns: 0")
        self.info_label.setStyleSheet("""
            QLabel {
                padding: 12px;
                font-size: 13px;
                color: #2c3e50;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                line-height: 1.5;
            }
        """)
        self.info_label.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML formatting
        chart_layout.addWidget(self.info_label)

        # Pattern Details Table - moved here for better visibility
        details_group = QGroupBox("Pattern Details")
        details_layout = QVBoxLayout(details_group)

        # Add pattern selector dropdown
        selector_layout = QHBoxLayout()
        selector_label = QLabel("Select Pattern:")
        selector_layout.addWidget(selector_label)

        self.pattern_selector = QComboBox()
        self.pattern_selector.setMaximumWidth(300)
        self.pattern_selector.currentIndexChanged.connect(self.on_pattern_selected)
        selector_layout.addWidget(self.pattern_selector, 1)
        selector_layout.addStretch()
        details_layout.addLayout(selector_layout)

        self.details_table = QTableWidget()
        self.details_table.setColumnCount(6)
        self.details_table.setHorizontalHeaderLabels(["Pattern/Point", "Price", "PRZ/Projection", "Type", "Direction", "Score"])
        self.details_table.horizontalHeader().setStretchLastSection(True)
        self.details_table.setMaximumHeight(220)  # Slightly reduced to accommodate dropdown
        self.details_table.setAlternatingRowColors(True)
        details_layout.addWidget(self.details_table)

        chart_layout.addWidget(details_group)

        main_layout.addWidget(chart_widget, 3)

        # Right side: Filters and controls
        filter_widget = self.create_filter_panel()
        main_layout.addWidget(filter_widget, 1)

    def create_filter_panel(self) -> QWidget:
        """Create the filter panel"""
        filter_widget = QWidget()
        filter_widget.setMaximumWidth(400)
        filter_layout = QVBoxLayout(filter_widget)

        # Title
        title = QLabel("PATTERN FILTERS")
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filter_layout.addWidget(title)


        # Pattern type filter
        type_group = QGroupBox("Pattern Type")
        type_layout = QVBoxLayout(type_group)

        self.formed_abcd_cb = QCheckBox("Formed ABCD")
        self.formed_abcd_cb.setChecked(True)
        self.formed_abcd_cb.stateChanged.connect(self.apply_filters)
        type_layout.addWidget(self.formed_abcd_cb)

        self.formed_xabcd_cb = QCheckBox("Formed XABCD")
        self.formed_xabcd_cb.setChecked(True)
        self.formed_xabcd_cb.stateChanged.connect(self.apply_filters)
        type_layout.addWidget(self.formed_xabcd_cb)

        self.unformed_abcd_cb = QCheckBox("Unformed ABCD")
        self.unformed_abcd_cb.setChecked(True)  # Changed to True to show unformed patterns
        self.unformed_abcd_cb.stateChanged.connect(self.apply_filters)
        type_layout.addWidget(self.unformed_abcd_cb)

        self.unformed_xabcd_cb = QCheckBox("Unformed XABCD")
        self.unformed_xabcd_cb.setChecked(True)  # Changed to True to show unformed patterns
        self.unformed_xabcd_cb.stateChanged.connect(self.apply_filters)
        type_layout.addWidget(self.unformed_xabcd_cb)

        filter_layout.addWidget(type_group)

        # Direction filter
        direction_group = QGroupBox("Direction")
        direction_layout = QVBoxLayout(direction_group)

        self.bullish_cb = QCheckBox("Bullish")
        self.bullish_cb.setChecked(True)
        self.bullish_cb.stateChanged.connect(self.apply_filters)
        direction_layout.addWidget(self.bullish_cb)

        self.bearish_cb = QCheckBox("Bearish")
        self.bearish_cb.setChecked(True)
        self.bearish_cb.stateChanged.connect(self.apply_filters)
        direction_layout.addWidget(self.bearish_cb)

        filter_layout.addWidget(direction_group)

        # Display options
        display_group = QGroupBox("Display Options")
        display_layout = QVBoxLayout(display_group)

        # Clustering mode dropdown
        cluster_label = QLabel("Pattern Clustering:")
        display_layout.addWidget(cluster_label)

        self.cluster_combo = QComboBox()
        self.cluster_combo.addItems([
            "No Clustering",
            "Point Sharing Analysis",
            "By Pattern Type"
        ])
        self.cluster_combo.setCurrentIndex(1)  # Default to Point Sharing Analysis
        self.cluster_combo.setToolTip(
            "Control how patterns are grouped:\n"
            "• No Clustering: Show all patterns individually\n"
            "• Point Sharing Analysis: Analyze point sharing frequency statistics\n"
            "• By Pattern Type: Group patterns by their type\n"
            "• Moderate: Group similar patterns (2+ shared points)\n"
            "• Loose: Group any overlapping patterns (1+ shared points)\n"
            "• By Pattern Type: Group patterns of the same type (e.g., all Bat patterns)\n"
            "• Loose: Group patterns with any shared point\n"
            "• Time-based: Group patterns in same time window\n"
            "• Smart: Automatically adjust based on pattern count"
        )
        self.cluster_combo.currentIndexChanged.connect(self.on_cluster_mode_changed)
        display_layout.addWidget(self.cluster_combo)

        # Cluster preview label - improved visibility
        self.cluster_preview_label = QLabel("")
        self.cluster_preview_label.setWordWrap(True)  # Enable word wrap
        self.cluster_preview_label.setTextFormat(Qt.TextFormat.RichText)  # Enable rich text for HTML formatting
        self.cluster_preview_label.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 12px;
                padding: 5px;
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        """)
        display_layout.addWidget(self.cluster_preview_label)
        self.update_cluster_preview()

        self.show_zones_cb = QCheckBox("Show PRZ Zones")
        self.show_zones_cb.setChecked(True)
        self.show_zones_cb.stateChanged.connect(self.update_display)
        display_layout.addWidget(self.show_zones_cb)

        filter_layout.addWidget(display_group)

        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)

        self.stats_label = QLabel("Total: 0 patterns\nFiltered: 0 patterns\nClusters: 0")
        stats_layout.addWidget(self.stats_label)

        filter_layout.addWidget(stats_group)

        filter_layout.addStretch()

        return filter_widget

    def apply_filters(self):
        """Apply filters to patterns"""
        self.filtered_patterns = []

        for pattern in self.unified_patterns:

            # Category filter
            if pattern.category == PatternCategory.FORMED_ABCD and not self.formed_abcd_cb.isChecked():
                continue
            if pattern.category == PatternCategory.FORMED_XABCD and not self.formed_xabcd_cb.isChecked():
                continue
            if pattern.category == PatternCategory.UNFORMED_ABCD and not self.unformed_abcd_cb.isChecked():
                continue
            if pattern.category == PatternCategory.UNFORMED_XABCD and not self.unformed_xabcd_cb.isChecked():
                continue

            # Direction filter
            if pattern.direction == PatternDirection.BULLISH and not self.bullish_cb.isChecked():
                continue
            if pattern.direction == PatternDirection.BEARISH and not self.bearish_cb.isChecked():
                continue

            self.filtered_patterns.append(pattern)

        # Reset to first page
        self.current_page = 0
        self.update_display()
        self.update_cluster_preview()  # Update clustering preview when filters change

    def update_display(self):
        """Update the pattern display"""
        # Clear existing
        self.chart.clear()

        # Add candlestick data
        if self.data is not None and len(self.data) > 0:
            try:
                # Import CandlestickItem from main file
                from harmonic_patterns_qt import CandlestickItem
                candles = CandlestickItem(self.data)
                self.chart.addItem(candles)
            except Exception as e:
                print(f"Error adding candlestick data: {e}")
                # Continue without candlesticks if there's an error

        # Get clustering mode
        cluster_modes = ["none", "point_sharing", "pattern_type"]
        cluster_mode = cluster_modes[self.cluster_combo.currentIndex()]

        # Calculate pagination based on clustering mode
        total_patterns = len(self.filtered_patterns)

        if cluster_mode != "none" and cluster_mode != "point_sharing":
            # Cluster ALL filtered patterns first
            all_clusters = PatternClusterer.cluster_patterns(self.filtered_patterns, mode=cluster_mode)
            all_representatives = [PatternClusterer.get_cluster_representative(c) for c in all_clusters]

            # Calculate pages based on clustered results
            total_pages = max(1, (len(all_representatives) + self.patterns_per_page - 1) // self.patterns_per_page)

            # Apply pagination to the clustered results
            start_idx = self.current_page * self.patterns_per_page
            end_idx = min(start_idx + self.patterns_per_page, len(all_representatives))
            patterns_to_display = all_representatives[start_idx:end_idx][:MAX_PATTERNS_TO_RENDER]

            # Update info with clustering details
            mode_text = self.cluster_combo.currentText()
            # Get the active filter type
            filter_names = []
            if self.formed_abcd_cb.isChecked():
                filter_names.append("Formed ABCD")
            if self.formed_xabcd_cb.isChecked():
                filter_names.append("Formed XABCD")
            if self.unformed_abcd_cb.isChecked():
                filter_names.append("Unformed ABCD")
            if self.unformed_xabcd_cb.isChecked():
                filter_names.append("Unformed XABCD")

            filter_name = ", ".join(filter_names) if filter_names else "None"
            if len(filter_names) == 4:
                filter_name = "All Categories"

            # Debug output
            print(f"DEBUG: Clustering mode={mode_text}")
            print(f"  Total filtered patterns: {total_patterns}")
            print(f"  Total clusters: {len(all_clusters)}")
            print(f"  Total representatives: {len(all_representatives)}")
            print(f"  Current page: {self.current_page + 1}")
            print(f"  Patterns on this page: {len(patterns_to_display)}")

            self.info_label.setText(
                f"<b>Total Patterns:</b> {len(self.unified_patterns)}<br>"
                f"<b>Filter ({filter_name}):</b> {total_patterns} patterns<br>"
                f"<b>Clustering ({mode_text}):</b> {len(all_representatives)} total groups<br>"
                f"<b>Page {self.current_page + 1}/{total_pages}:</b> Showing {len(patterns_to_display)} of {len(all_representatives)} groups"
            )
        else:
            # Calculate pages for non-clustering mode
            total_pages = max(1, (total_patterns + self.patterns_per_page - 1) // self.patterns_per_page)

            # Get patterns for current page
            start_idx = self.current_page * self.patterns_per_page
            end_idx = min(start_idx + self.patterns_per_page, total_patterns)
            page_patterns = self.filtered_patterns[start_idx:end_idx]
            patterns_to_display = page_patterns[:MAX_PATTERNS_TO_RENDER]

            # Update info
            # Get the active filter type
            filter_names = []
            if self.formed_abcd_cb.isChecked():
                filter_names.append("Formed ABCD")
            if self.formed_xabcd_cb.isChecked():
                filter_names.append("Formed XABCD")
            if self.unformed_abcd_cb.isChecked():
                filter_names.append("Unformed ABCD")
            if self.unformed_xabcd_cb.isChecked():
                filter_names.append("Unformed XABCD")

            filter_name = ", ".join(filter_names) if filter_names else "None"
            if len(filter_names) == 4:
                filter_name = "All Categories"

            self.info_label.setText(
                f"<b>Total Patterns:</b> {len(self.unified_patterns)}<br>"
                f"<b>Filter ({filter_name}):</b> {total_patterns} patterns<br>"
                f"<b>Current Page:</b> {len(page_patterns)} patterns<br>"
                f"<b>Displayed:</b> {len(patterns_to_display)} patterns"
            )

        # Update page label and navigation buttons
        self.page_label.setText(f"Page {self.current_page + 1} of {total_pages}")
        self.prev_btn.setEnabled(self.current_page > 0)
        self.next_btn.setEnabled(self.current_page < total_pages - 1)

        # Draw patterns
        self.draw_patterns(patterns_to_display)

        # Update statistics
        self.update_statistics()

    def draw_patterns(self, patterns: List[UnifiedPattern]):
        """Draw patterns on the chart"""
        print(f"Drawing {len(patterns)} patterns")
        print(f"Data length: {len(self.data) if self.data is not None else 0}")
        print(f"Extremum points: {len(self.extremum_points)}")

        for i, pattern in enumerate(patterns):
            # Skip patterns with no points
            if not pattern.points:
                print(f"Pattern {pattern.name} has no points")
                continue

            # Debug output
            print(f"\nPattern {i}: {pattern.name}")
            for pname, pdata in pattern.points.items():
                print(f"  {pname}: index={pdata.index}, price={pdata.price}, time={pdata.time}")

            # Color based on direction and category - avoid green/red to prevent confusion with candlesticks
            if pattern.direction == PatternDirection.BULLISH:
                base_color = (100, 200, 255)  # Light blue for bullish patterns
            else:
                base_color = (255, 150, 100)  # Light orange/coral for bearish patterns

            # Adjust alpha based on category
            if pattern.category in [PatternCategory.FORMED_ABCD, PatternCategory.FORMED_XABCD]:
                alpha = 200
                line_width = 2
            else:
                alpha = 100
                line_width = 1

            color = (*base_color, alpha)

            # Determine which points to draw
            # For unformed patterns, we don't have D point - only projections
            is_unformed = pattern.category in [PatternCategory.UNFORMED_ABCD, PatternCategory.UNFORMED_XABCD]

            if is_unformed:
                # Unformed patterns only have points up to C
                if 'X' in pattern.points:
                    point_order = ['X', 'A', 'B', 'C']
                else:
                    point_order = ['A', 'B', 'C']
            else:
                # Formed patterns have all points including D
                if 'X' in pattern.points:
                    point_order = ['X', 'A', 'B', 'C', 'D']
                else:
                    point_order = ['A', 'B', 'C', 'D']

            # Build coordinates
            x_coords = []
            y_coords = []
            labels = []

            for point_name in point_order:
                if point_name in pattern.points:
                    point = pattern.points[point_name]
                    if point and point.index is not None and point.price is not None:
                        x_coords.append(point.index)
                        y_coords.append(point.price)
                        labels.append(point_name)

            print(f"Pattern {i}: {pattern.name} has {len(x_coords)} points: {labels}")
            if x_coords:
                print(f"  X range: {min(x_coords)} to {max(x_coords)}")
                print(f"  Y range: {min(y_coords)} to {max(y_coords)}")

            if len(x_coords) >= 2:
                # Draw pattern as connected lines
                pen = pg.mkPen(color=color, width=line_width, style=Qt.PenStyle.SolidLine)

                # Draw lines between consecutive points
                for j in range(len(x_coords) - 1):
                    line = pg.PlotDataItem(
                        [x_coords[j], x_coords[j+1]],
                        [y_coords[j], y_coords[j+1]],
                        pen=pen
                    )
                    self.chart.addItem(line)

                # Add points as circles
                point_pen = pg.mkPen(color=base_color, width=2)
                point_brush = pg.mkBrush(*base_color, 50)
                scatter = pg.ScatterPlotItem(
                    x_coords, y_coords,
                    pen=point_pen,
                    brush=point_brush,
                    size=10,  # Increased size
                    symbol='o'
                )
                self.chart.addItem(scatter)

                # Add individual point labels (A, B, C, D, X)
                for idx, (x, y, label) in enumerate(zip(x_coords, y_coords, labels)):
                    point_label = pg.TextItem(
                        label,  # 'A', 'B', 'C', 'D', or 'X'
                        color=(255, 255, 255),  # White text
                        anchor=(0.5, 0.5),  # Center the text on point
                        fill=pg.mkBrush(*base_color, 200)  # Background with pattern color
                    )
                    # Offset label slightly above the point
                    point_label.setPos(x, y + (max(y_coords) - min(y_coords)) * 0.02)
                    self.chart.addItem(point_label)

                # Add pattern label at first point
                if x_coords and y_coords:
                    label_text = pattern.name  # Removed score display
                    text = pg.TextItem(
                        label_text,
                        color=base_color,
                        anchor=(0, 1),
                        fill=pg.mkBrush(255, 255, 255, 180)
                    )
                    text.setPos(x_coords[0], y_coords[0])
                    self.chart.addItem(text)

            # Draw PRZ zones for unformed patterns - always show for unformed patterns
            if is_unformed:
                # Draw PRZ zones (for unformed ABCD)
                if pattern.prz_zones:
                    for zone_idx, zone in enumerate(pattern.prz_zones[:3]):  # Limit to 3 zones
                        if isinstance(zone, (list, tuple)) and len(zone) >= 2:
                            # Use bright colors for PRZ zones
                            if pattern.direction == PatternDirection.BULLISH:
                                # Bright lime green for bullish PRZ zones
                                zone_color = (50, 255, 50, 180)  # Lime green
                            else:
                                # Bright red-orange for bearish PRZ zones
                                zone_color = (255, 100, 50, 180)  # Red-orange

                            zone_pen = pg.mkPen(color=zone_color, width=2, style=Qt.PenStyle.DashLine)

                            # Get last point's x coordinate
                            if x_coords:
                                x_start = x_coords[-1]
                                x_end = min(x_start + 30, len(self.data) - 1)

                                # Draw top and bottom lines of zone
                                top_line = pg.PlotDataItem(
                                    [x_start, x_end],
                                    [zone[1], zone[1]],
                                    pen=zone_pen
                                )
                                bottom_line = pg.PlotDataItem(
                                    [x_start, x_end],
                                    [zone[0], zone[0]],
                                    pen=zone_pen
                                )
                                self.chart.addItem(top_line)
                                self.chart.addItem(bottom_line)

                                # Add zone label with price values - improved visibility
                                zone_label = f"PRZ {zone_idx+1}\n{zone[0]:.2f}-{zone[1]:.2f}"
                                zone_text = pg.TextItem(
                                    zone_label,
                                    color=(0, 0, 0),  # Black text for better contrast
                                    anchor=(0, 0.5),
                                    fill=pg.mkBrush(*zone_color[:3], 220)  # Use zone color as background
                                )
                                zone_text.setPos(x_end + 1, (zone[0] + zone[1]) / 2)
                                self.chart.addItem(zone_text)

                # Draw projection lines (for unformed XABCD)
                elif pattern.projections:
                    print(f"Drawing {len(pattern.projections)} projection lines for {pattern.name}")
                    for proj_idx, proj in enumerate(pattern.projections[:6]):  # Limit to 6 lines
                        if isinstance(proj, dict) and 'price' in proj:
                            print(f"  Projection {proj_idx}: price={proj['price']}")
                            # Use bright, contrasting colors for projection lines
                            if pattern.direction == PatternDirection.BULLISH:
                                # Bright cyan/aqua for bullish projections
                                proj_color = (0, 255, 255, 200)  # Cyan with high opacity
                            else:
                                # Bright magenta for bearish projections
                                proj_color = (255, 0, 255, 200)  # Magenta with high opacity

                            proj_pen = pg.mkPen(color=proj_color, width=2, style=Qt.PenStyle.DashLine)

                            if x_coords:
                                x_start = x_coords[-1]
                                x_end = min(x_start + 30, len(self.data) - 1)

                                print(f"    Drawing line from x={x_start} to x={x_end} at price={proj['price']}")

                                proj_line = pg.PlotDataItem(
                                    [x_start, x_end],
                                    [proj['price'], proj['price']],
                                    pen=proj_pen
                                )
                                self.chart.addItem(proj_line)

                                # Add price label for projection line - improved visibility
                                proj_label = f"{proj['price']:.2f}"
                                if 'ratio' in proj:
                                    proj_label = f"{proj['ratio']}: {proj['price']:.2f}"

                                proj_text = pg.TextItem(
                                    proj_label,
                                    color=(0, 0, 0),  # Black text for better contrast
                                    anchor=(0, 0.5),
                                    fill=pg.mkBrush(*proj_color[:3], 220)  # Use projection color as background
                                )
                                proj_text.setPos(x_end + 1, proj['price'])
                                self.chart.addItem(proj_text)
                                print(f"    Line and label added to chart")
                            else:
                                print(f"    WARNING: No x_coords available for drawing projection line")

    def update_statistics(self):
        """Update statistics display"""
        total = len(self.unified_patterns)
        filtered = len(self.filtered_patterns)

        # Get clustering mode for statistics
        cluster_modes = ["none", "point_sharing", "pattern_type"]
        cluster_mode = cluster_modes[self.cluster_combo.currentIndex()]

        if cluster_mode != "none" and cluster_mode != "point_sharing":
            clusters = PatternClusterer.cluster_patterns(self.filtered_patterns, mode=cluster_mode)
            cluster_count = len(clusters)
            cluster_info = f" ({self.cluster_combo.currentText()})"
        else:
            cluster_count = filtered
            cluster_info = ""

        # Count by category
        category_counts = {}
        for pattern in self.filtered_patterns:
            cat = pattern.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1

        stats_text = f"Total: {total} patterns\n"
        stats_text += f"Filtered: {filtered} patterns\n"
        stats_text += f"Groups: {cluster_count}{cluster_info}\n\n"

        for cat, count in category_counts.items():
            stats_text += f"{cat}: {count}\n"

        self.stats_label.setText(stats_text)

        # Update pattern details
        self.update_pattern_details()

    def previous_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_display()
            self.update_cluster_preview()

    def next_page(self):
        """Go to next page"""
        total_patterns = len(self.filtered_patterns)
        total_pages = max(1, (total_patterns + self.patterns_per_page - 1) // self.patterns_per_page)

        if self.current_page < total_pages - 1:
            self.current_page += 1
            self.update_display()
            self.update_cluster_preview()

    def on_per_page_changed(self, value):
        """Handle change in patterns per page"""
        self.patterns_per_page = value
        self.current_page = 0  # Reset to first page
        self.update_display()
        self.update_cluster_preview()

    def on_cluster_mode_changed(self):
        """Handle cluster mode change"""
        self.update_cluster_preview()
        self.update_display()

    def update_cluster_preview(self):
        """Update the cluster preview label with point sharing frequency analysis"""
        if not self.filtered_patterns:
            self.cluster_preview_label.setText("No patterns to analyze")
            return

        total = len(self.filtered_patterns)
        preview_text = f"<b>{total} patterns - Point Sharing Analysis:</b><br>"

        # Separate patterns by type
        abcd_patterns = []
        xabcd_patterns = []

        for pattern in self.filtered_patterns:
            try:
                points = pattern.get_point_indices()
                if 'X' in points:
                    xabcd_patterns.append(pattern)
                else:
                    abcd_patterns.append(pattern)
            except AttributeError:
                continue

        preview_lines = []

        # Analyze ABCD patterns (A, B, C, D points)
        if abcd_patterns:
            abcd_analysis = self._analyze_point_sharing(abcd_patterns, ['A', 'B', 'C', 'D'])
            preview_lines.append("<b>ABCD Patterns:</b>")
            for level, count in abcd_analysis.items():
                if count > 0:
                    preview_lines.append(f"&nbsp;&nbsp;{level}: {count} patterns")

        # Analyze XABCD patterns (X, A, B, C, D points)
        if xabcd_patterns:
            xabcd_analysis = self._analyze_point_sharing(xabcd_patterns, ['X', 'A', 'B', 'C', 'D'])
            preview_lines.append("<b>XABCD Patterns:</b>")
            for level, count in xabcd_analysis.items():
                if count > 0:
                    preview_lines.append(f"&nbsp;&nbsp;{level}: {count} patterns")

        if not preview_lines:
            preview_lines.append("&nbsp;&nbsp;No point sharing found")

        self.cluster_preview_label.setText(preview_text + "<br>".join(preview_lines))

    def _analyze_point_sharing(self, patterns, point_names):
        """Analyze how many patterns share different numbers of points"""
        from collections import defaultdict

        # Build index of patterns by their actual point indices
        pattern_points = {}
        for pattern in patterns:
            try:
                points = pattern.get_point_indices()
                pattern_points[id(pattern)] = {p: points[p] for p in point_names if p in points}
            except AttributeError:
                continue

        if not pattern_points:
            return {}

        # Initialize counts for each sharing level
        sharing_counts = {}
        for num_points in range(1, len(point_names) + 1):
            if num_points == 1:
                sharing_counts[f"{num_points} shared point"] = 0
            else:
                sharing_counts[f"{num_points} shared points"] = 0

        # Find groups of patterns that share exactly N points
        pattern_list = list(pattern_points.items())
        counted_patterns = set()  # Track which patterns we've already counted

        # Check each sharing level from highest to lowest
        for sharing_level in range(len(point_names), 0, -1):
            patterns_at_this_level = set()

            # Find all pairs that share exactly this many points
            for i, (pattern_id1, points1) in enumerate(pattern_list):
                if pattern_id1 in counted_patterns:
                    continue

                for j, (pattern_id2, points2) in enumerate(pattern_list):
                    if i >= j or pattern_id2 in counted_patterns:
                        continue

                    # Count shared points between these two patterns
                    shared_count = 0
                    for point_name in point_names:
                        if (point_name in points1 and point_name in points2 and
                            points1[point_name] == points2[point_name]):
                            shared_count += 1

                    # If they share exactly this many points, add both to this level
                    if shared_count == sharing_level:
                        patterns_at_this_level.add(pattern_id1)
                        patterns_at_this_level.add(pattern_id2)

            # Count patterns at this sharing level
            if patterns_at_this_level:
                if sharing_level == 1:
                    sharing_counts["1 shared point"] = len(patterns_at_this_level)
                else:
                    sharing_counts[f"{sharing_level} shared points"] = len(patterns_at_this_level)

                # Mark these patterns as counted so they don't appear in lower levels
                counted_patterns.update(patterns_at_this_level)

        return sharing_counts

    def update_pattern_details(self):
        """Update the pattern details table and dropdown selector"""
        # Update dropdown with current page patterns
        self.pattern_selector.blockSignals(True)
        self.pattern_selector.clear()

        # Get clustering mode
        cluster_modes = ["none", "point_sharing", "pattern_type"]
        cluster_mode = cluster_modes[self.cluster_combo.currentIndex()]

        if cluster_mode != "none" and cluster_mode != "point_sharing":
            # Cluster ALL filtered patterns first
            all_clusters = PatternClusterer.cluster_patterns(self.filtered_patterns, mode=cluster_mode)
            all_representatives = [PatternClusterer.get_cluster_representative(c) for c in all_clusters]

            # Apply pagination to the clustered results
            start_idx = self.current_page * self.patterns_per_page
            end_idx = min(start_idx + self.patterns_per_page, len(all_representatives))
            patterns_for_dropdown = all_representatives[start_idx:end_idx]
        else:
            # Get patterns for current page
            start_idx = self.current_page * self.patterns_per_page
            end_idx = min(start_idx + self.patterns_per_page, len(self.filtered_patterns))

            if start_idx >= len(self.filtered_patterns):
                self.pattern_selector.addItem("No patterns available")
                self.pattern_selector.setEnabled(False)
                self.pattern_selector.blockSignals(False)
                self.details_table.setRowCount(0)
                return

            patterns_for_dropdown = self.filtered_patterns[start_idx:end_idx]

        if not patterns_for_dropdown:
            self.pattern_selector.addItem("No patterns available")
            self.pattern_selector.setEnabled(False)
            self.pattern_selector.blockSignals(False)
            self.details_table.setRowCount(0)
            return

        # Add patterns to dropdown
        for i, pattern in enumerate(patterns_for_dropdown):
            # Create informative dropdown text
            dropdown_text = f"{i+1}. {pattern.name} ({pattern.direction.value})"
            self.pattern_selector.addItem(dropdown_text, pattern)

        self.pattern_selector.setEnabled(True)
        self.pattern_selector.blockSignals(False)

        # Show first pattern by default
        self.show_pattern_details(patterns_for_dropdown[0] if patterns_for_dropdown else None)

    def on_pattern_selected(self, index):
        """Handle pattern selection from dropdown"""
        if index >= 0:
            pattern = self.pattern_selector.itemData(index)
            if pattern:
                self.show_pattern_details(pattern)

    def show_pattern_details(self, pattern):
        """Show details for a specific pattern"""
        self.details_table.setRowCount(0)

        if not pattern:
            return

        # Add pattern header row
        row = self.details_table.rowCount()
        self.details_table.insertRow(row)
        self.details_table.setItem(row, 0, QTableWidgetItem(pattern.name))
        self.details_table.setItem(row, 3, QTableWidgetItem(pattern.category.value))
        self.details_table.setItem(row, 4, QTableWidgetItem(pattern.direction.value))
        self.details_table.setItem(row, 5, QTableWidgetItem(f"{pattern.score:.2f}"))

        # Add point rows
        for point_name in ['X', 'A', 'B', 'C', 'D']:
            if point_name in pattern.points:
                point = pattern.points[point_name]
                if point:
                    row = self.details_table.rowCount()
                    self.details_table.insertRow(row)
                    self.details_table.setItem(row, 0, QTableWidgetItem(f"  {point_name}"))
                    self.details_table.setItem(row, 1, QTableWidgetItem(f"{point.price:.2f}"))

        # Add PRZ/Projection info based on pattern type
        if pattern.category == PatternCategory.UNFORMED_XABCD and pattern.projections:
            # For unformed XABCD, show projection lines
            for i, proj in enumerate(pattern.projections[:4]):
                if isinstance(proj, dict) and 'price' in proj:
                    row = self.details_table.rowCount()
                    self.details_table.insertRow(row)
                    proj_label = f"  Projection {i+1}"
                    if 'ratio' in proj:
                        proj_label = f"  {proj.get('ratio', f'Proj {i+1}')}"
                    self.details_table.setItem(row, 0, QTableWidgetItem(proj_label))
                    self.details_table.setItem(row, 1, QTableWidgetItem(""))  # No point price
                    self.details_table.setItem(row, 2, QTableWidgetItem(f"→ {proj['price']:.2f}"))
        elif pattern.category == PatternCategory.UNFORMED_ABCD and pattern.prz_zones:
            # For unformed ABCD, show PRZ zones
            for i, zone in enumerate(pattern.prz_zones[:3]):
                if isinstance(zone, (list, tuple)) and len(zone) >= 2:
                    row = self.details_table.rowCount()
                    self.details_table.insertRow(row)
                    self.details_table.setItem(row, 0, QTableWidgetItem(f"  PRZ Zone {i+1}"))
                    self.details_table.setItem(row, 1, QTableWidgetItem(""))  # No point price
                    self.details_table.setItem(row, 2, QTableWidgetItem(f"{zone[0]:.2f} - {zone[1]:.2f}"))