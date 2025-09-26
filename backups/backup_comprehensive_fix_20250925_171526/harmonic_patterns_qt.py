"""
Harmonic Pattern Detection System
Built with PyQt6 and PyQtGraph for high-performance financial charting

Professional trading analysis tool for detecting harmonic patterns in financial data.
"""

# Configuration
DEBUG_MODE = True  # Set to False for production

import sys
import pandas as pd
import numpy as np
from datetime import datetime
import json
from typing import List, Tuple, Dict, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QDateEdit, QSpinBox,
    QCheckBox, QGroupBox, QTextEdit, QSplitter, QTabWidget,
    QMessageBox, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar, QStatusBar, QToolBar, QDockWidget,
    QDialog, QDialogButtonBox, QDoubleSpinBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal, QThread, QTimer, QPointF
from PyQt6.QtGui import QAction, QKeySequence, QFont, QColor, QPen

import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen, mkBrush

# PRZ Pattern color mapping for better visual identification
PRZ_PATTERN_COLORS = {
    '1a': '#FF0000',    # Red
    '1b': '#FF4500',    # Orange Red
    '2': '#FFA500',     # Orange
    '3': '#FFD700',     # Gold
    '4': '#ADFF2F',     # Green Yellow
    '5': '#00FF00',     # Green
    '6a': '#00CED1',    # Dark Turquoise
    '6b': '#0000FF',    # Blue
    '6c': '#4169E1',    # Royal Blue
    '6d': '#8A2BE2',    # Blue Violet
    '6e': '#FF1493',    # Deep Pink
}

def get_prz_color(pattern_source):
    """Get distinctive color for PRZ zone based on pattern source"""
    if not pattern_source:
        return '#808080'  # Gray for unknown

    # Extract pattern identifier
    for pattern_id, color in PRZ_PATTERN_COLORS.items():
        if pattern_id in pattern_source:
            return color

    return '#808080'  # Default gray

# Import pattern detection modules
from pattern_ratios_2_Final import (
    ABCD_PATTERN_RATIOS,
    XABCD_PATTERN_RATIOS,
    PATTERN_COLORS,
    PRZ_PROJECTION_PAIRS
)

# Unformed ABCD Pattern Detection
from unformed_abcd_patterns import detect_unformed_abcd_patterns
from legacy_pattern_detection import calculate_prz

# Formed/Unformed ABCD and XABCD Pattern Detection
from legacy_pattern_detection import detect_unformed_xabcd_patterns
from formed_and_unformed_patterns import (
    detect_abcd_patterns_fast as detect_formed_abcd_patterns,
    detect_xabcd_patterns_fast as detect_formed_xabcd_patterns,
    detect_unformed_xabcd_patterns_fast as detect_unformed_xabcd_patterns
)

# Import strict ABCD pattern detection
from strict_abcd_patterns import detect_strict_abcd_patterns
# Use the ultra-fast sliding window implementation
from strict_xabcd_patterns import detect_strict_xabcd_patterns
print("Using ULTRA-FAST strict XABCD detection (sliding window algorithm)")

# Import comprehensive ABCD pattern detection
from comprehensive_abcd_patterns import (
    detect_strict_abcd_patterns as detect_comprehensive_strict_abcd,
    detect_unformed_abcd_patterns_optimized as detect_comprehensive_unformed_abcd
)
print("Comprehensive ABCD pattern detection loaded")

# Import comprehensive XABCD pattern detection
from comprehensive_xabcd_patterns import detect_strict_unformed_xabcd_patterns as detect_comprehensive_unformed_xabcd
from backtesting_dialog import BacktestingDialog
print("Comprehensive XABCD pattern detection loaded")

# Import Binance data downloader
from binance_downloader import BinanceDataDownloader

# Import improved pattern display system
try:
    from improved_pattern_display import ImprovedAllPatternsWindow
    IMPROVED_DISPLAY_AVAILABLE = True
except ImportError:
    IMPROVED_DISPLAY_AVAILABLE = False
    print("Warning: Improved pattern display not available")

# Configure pyqtgraph for better appearance
pg.setConfigOptions(antialias=True)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class DateAxisItem(pg.AxisItem):
    """Custom axis item to display dates on X-axis"""

    def __init__(self, dates, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dates = dates

    def tickStrings(self, values, scale, spacing):
        """Convert tick values to date strings"""
        strings = []
        for value in values:
            try:
                # Convert index to date string
                idx = int(value)
                if 0 <= idx < len(self.dates):
                    date = self.dates[idx]
                    # Format date as MM/DD
                    strings.append(date.strftime('%m/%d'))
                else:
                    strings.append('')
            except (IndexError, ValueError):
                strings.append('')
        return strings


class CandlestickItem(pg.GraphicsObject):
    """Custom candlestick item for pyqtgraph"""

    def __init__(self, data):
        pg.GraphicsObject.__init__(self)
        self.data = data
        self.generatePicture()

    def generatePicture(self):
        """Generate the picture of candlesticks"""
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)

        # Set pen for drawing
        bullPen = pg.mkPen(color='g', width=1)
        bearPen = pg.mkPen(color='r', width=1)
        bullBrush = pg.mkBrush('g')
        bearBrush = pg.mkBrush('r')

        width = 0.6  # Width of candlestick body

        for i, (timestamp, row) in enumerate(self.data.iterrows()):
            # Skip invalid data points
            try:
                open_price = float(row['Open'])
                high = float(row['High'])
                low = float(row['Low'])
                close = float(row['Close'])

                # Validate data
                if pd.isna(open_price) or pd.isna(high) or pd.isna(low) or pd.isna(close):
                    continue
                if open_price <= 0 or high <= 0 or low <= 0 or close <= 0:
                    continue

                # Skip if data is inconsistent
                if high < low:
                    continue
                if high < open_price or high < close:
                    continue
                if low > open_price or low > close:
                    continue

            except (ValueError, TypeError):
                continue

            # Determine if bullish or bearish
            if close >= open_price:
                painter.setPen(bullPen)
                painter.setBrush(bullBrush)
            else:
                painter.setPen(bearPen)
                painter.setBrush(bearBrush)

            # Only draw if the candlestick has meaningful size
            if high - low > 0.001:  # Minimum threshold for visibility
                # Draw the high-low line
                painter.drawLine(pg.QtCore.QPointF(i, low), pg.QtCore.QPointF(i, high))

                # Draw the body
                body_height = abs(close - open_price)
                if body_height > 0.001:  # Minimum threshold for body
                    painter.drawRect(pg.QtCore.QRectF(i - width/2, min(open_price, close),
                                                      width, body_height))
                else:
                    # Draw a thin line for doji candlesticks
                    painter.drawLine(pg.QtCore.QPointF(i - width/2, open_price),
                                   pg.QtCore.QPointF(i + width/2, open_price))

        painter.end()

    def paint(self, painter, *args):
        painter.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return pg.QtCore.QRectF(self.picture.boundingRect())


class PatternDetectionWorker(QThread):
    """Background worker for pattern detection"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)

    def __init__(self, extremum_points, pattern_types, data=None, main_window=None):
        super().__init__()
        self.extremum_points = extremum_points
        self.pattern_types = pattern_types
        self.data = data  # Candlestick data for filtering unformed patterns
        self.main_window = main_window

    def run(self):
        """Run pattern detection in background"""
        results = {
            'abcd': [],
            'xabcd': [],
            'strict_abcd': [],
            'comprehensive_abcd': [],
            'comprehensive_xabcd': [],
            'unformed': [],
            'unformed_xabcd': []
        }

        try:
            if DEBUG_MODE: print(f"Starting pattern detection with types: {self.pattern_types}")
            if DEBUG_MODE: print(f"Number of extremum points: {len(self.extremum_points)}")

            # Detect patterns based on selected types
            if 'abcd' in self.pattern_types:
                self.status.emit("Detecting Basic ABCD patterns...")
                if DEBUG_MODE: print("Detecting Basic ABCD patterns...")
                results['abcd'] = self.detect_abcd_patterns()
                if DEBUG_MODE: print(f"Found {len(results['abcd'])} Basic ABCD patterns")
                self.progress.emit(20)

            if 'strict_abcd' in self.pattern_types:
                self.status.emit("Detecting Strict ABCD patterns (with price containment)...")
                if DEBUG_MODE: print("Detecting Strict ABCD patterns...")
                results['strict_abcd'] = self.detect_strict_abcd_patterns()
                if DEBUG_MODE: print(f"Found {len(results['strict_abcd'])} Strict ABCD patterns")
                self.progress.emit(30)

            if 'comprehensive_abcd' in self.pattern_types:
                self.status.emit("Detecting Unstrict ABCD patterns with comprehensive validation...")
                if DEBUG_MODE: print("Detecting Comprehensive ABCD patterns (unstrict only)...")
                results['comprehensive_abcd'] = self.detect_comprehensive_abcd_patterns()
                if DEBUG_MODE: print(f"Found {len(results['comprehensive_abcd'])} Unstrict ABCD patterns")
                self.progress.emit(35)

            if 'comprehensive_xabcd' in self.pattern_types:
                self.status.emit("Detecting Unstrict XABCD patterns with comprehensive validation...")
                if DEBUG_MODE: print("Detecting Comprehensive XABCD patterns (unstrict only)...")
                results['comprehensive_xabcd'] = self.detect_comprehensive_xabcd_patterns()
                if DEBUG_MODE: print(f"Found {len(results['comprehensive_xabcd'])} Unstrict XABCD patterns")
                self.progress.emit(40)

            if 'xabcd' in self.pattern_types:
                self.status.emit("Detecting Basic XABCD patterns...")
                if DEBUG_MODE: print("Detecting Basic XABCD patterns...")
                results['xabcd'] = self.detect_xabcd_patterns()
                if DEBUG_MODE: print(f"Found {len(results['xabcd'])} Basic XABCD patterns")
                self.progress.emit(50)

            if 'strict_xabcd' in self.pattern_types:
                self.status.emit("Detecting Strict XABCD patterns (with price containment)...")
                if DEBUG_MODE: print("Detecting Strict XABCD patterns...")
                results['strict_xabcd'] = self.detect_strict_xabcd_patterns()
                # Don't print count here - will print final count after deduplication
                self.progress.emit(55)

            if 'unstrict_abcd' in self.pattern_types:
                self.status.emit("Detecting Unstrict ABCD patterns...")
                if DEBUG_MODE: print("Detecting Unstrict ABCD patterns...")
                results['unformed'] = self.detect_unformed_patterns()
                if DEBUG_MODE: print(f"Found {len(results['unformed'])} Unstrict ABCD patterns")
                self.progress.emit(75)

            if 'unstrict_xabcd' in self.pattern_types:
                self.status.emit("Detecting Unstrict XABCD patterns...")
                if DEBUG_MODE: print("Detecting Unstrict XABCD patterns...")
                results['unformed_xabcd'] = self.detect_unformed_xabcd_patterns()
                if DEBUG_MODE: print(f"Found {len(results['unformed_xabcd'])} Unstrict XABCD patterns")
                self.progress.emit(100)

            # Validate that all results are lists of dictionaries
            for ptype, plist in results.items():
                if not isinstance(plist, list):
                    if DEBUG_MODE: print(f"Warning: {ptype} is not a list: {type(plist)}")
                    results[ptype] = []
                else:
                    # Filter out non-dictionary items
                    valid_patterns = []
                    for i, pattern in enumerate(plist):
                        if isinstance(pattern, dict):
                            valid_patterns.append(pattern)
                        else:
                            if DEBUG_MODE: print(f"Warning: {ptype}[{i}] is not a dict: {type(pattern)}")
                    results[ptype] = valid_patterns

            if DEBUG_MODE:
                total_before_dedup = sum(len(p) for p in results.values())
                print(f"Pattern detection complete. Total patterns before deduplication: {total_before_dedup}")

            if DEBUG_MODE:
                # Print final counts after deduplication
                for pattern_type, patterns in results.items():
                    if patterns:  # Only print non-empty pattern types
                        print(f"Found {len(patterns)} {pattern_type.replace('_', ' ').title()} patterns (after deduplication)")
                print(f"Total patterns after deduplication: {sum(len(p) for p in results.values())}")
            self.finished.emit(results)

        except Exception as e:
            import traceback
            if DEBUG_MODE: print(f"Error in pattern detection: {str(e)}")
            print(traceback.format_exc())
            self.status.emit(f"Error: {str(e)}")

    def detect_abcd_patterns(self):
        """Detect Formed ABCD patterns"""
        return detect_formed_abcd_patterns(self.extremum_points, log_details=True)

    def detect_strict_abcd_patterns(self):
        """Detect Strict Formed ABCD patterns with price containment validation"""
        # Pass optimization parameters for better performance
        return detect_strict_abcd_patterns(
            self.extremum_points,
            self.data,
            log_details=False,  # Disable detailed logging for speed
            max_patterns=None,   # No limit - detect ALL patterns
        )

    def detect_strict_xabcd_patterns(self):
        """Detect Strict Formed XABCD patterns with price containment validation"""
        return detect_strict_xabcd_patterns(
            self.extremum_points,
            self.data,
            log_details=False,  # Disable detailed logging for speed
            max_patterns=100,    # Increased limit to 100
            max_window=100  # Use the optimized sliding window algorithm
        )

    def detect_xabcd_patterns(self):
        """Detect Formed XABCD patterns"""
        return detect_formed_xabcd_patterns(self.extremum_points, log_details=True)

    def filter_unformed_patterns(self, patterns, is_xabcd=False):
        """Filter out unformed patterns where price has already crossed projected D"""
        if self.data is None:
            return patterns

        filtered = []
        for pattern in patterns:
            # Get C point time
            c_time = pattern['points']['C']['time']
            d_projected = pattern['points']['D_projected']
            is_bullish = pattern['type'] == 'bullish'

            # Get candlesticks after C
            try:
                c_idx = self.data.index.get_loc(c_time)
            except (KeyError, ValueError) as e:
                # Fallback to nearest time index
                try:
                    c_idx = np.argmin(np.abs(self.data.index - c_time))
                except Exception as e:
                    if DEBUG_MODE: print(f"Warning: Could not find index for time {c_time}: {e}")
                    continue  # Skip this pattern

            # Check all candlesticks from C to end
            data_after_c = self.data.iloc[c_idx:]

            # Check if price has crossed any PRZ zone
            price_crossed = False

            # Handle both old format (single price) and new format (PRZ zones)
            if 'prz_zones' in d_projected:
                # New format with PRZ zones
                for zone in d_projected['prz_zones']:
                    if is_bullish:
                        # For bullish, check if any low entered PRZ zone
                        if (data_after_c['Low'] <= zone['max']).any() and (data_after_c['Low'] >= zone['min']).any():
                            price_crossed = True
                            break
                    else:
                        # For bearish, check if any high entered PRZ zone
                        if (data_after_c['High'] >= zone['min']).any() and (data_after_c['High'] <= zone['max']).any():
                            price_crossed = True
                            break
            elif 'price' in d_projected:
                # Old format with single price (backward compatibility)
                projected_d = d_projected['price']
                if is_bullish:
                    if (data_after_c['Low'] <= projected_d).any():
                        price_crossed = True
                else:
                    if (data_after_c['High'] >= projected_d).any():
                        price_crossed = True

            # Only keep pattern if price hasn't crossed projected D
            if not price_crossed:
                filtered.append(pattern)

        return filtered

    def detect_unformed_patterns(self):
        """Detect Unformed ABCD patterns"""
        patterns = detect_unformed_abcd_patterns(self.extremum_points, log_details=False)
        return self.filter_unformed_patterns(patterns, is_xabcd=False)

    def detect_comprehensive_abcd_patterns(self):
        """Detect Comprehensive ABCD patterns (strict unformed only)"""
        # Detect strict unformed ABCD patterns
        unformed_patterns = detect_comprehensive_unformed_abcd(
            self.extremum_points,
            self.data,
            log_details=False,
            max_patterns=100,  # Increased limit since we're only getting unformed
            strict_validation=True
        )

        # Filter unformed patterns
        unformed_filtered = self.filter_unformed_patterns(unformed_patterns, is_xabcd=False)

        return unformed_filtered

    def detect_comprehensive_xabcd_patterns(self):
        """Detect Comprehensive XABCD patterns (strict unformed only)"""
        # Detect strict unformed XABCD patterns
        unformed_patterns = detect_comprehensive_unformed_xabcd(
            self.extremum_points,
            self.data,
            log_details=False,
            max_patterns=100    # Increased limit to 100
        )

        # Filter unformed patterns
        unformed_filtered = self.filter_unformed_patterns(unformed_patterns, is_xabcd=True)

        return unformed_filtered

    def detect_unformed_xabcd_patterns(self):
        """Detect Unformed XABCD patterns"""
        print(f"Detecting Unformed XABCD patterns with {len(self.extremum_points)} points")
        # Use ALL extremum points (no artificial limits whatsoever)
        extremums_to_use = self.extremum_points

        # DEBUG: Log which extremum points are being used
        print(f"Using {len(extremums_to_use)} of {len(self.extremum_points)} extremum points:")
        for i, (time, price, is_high) in enumerate(extremums_to_use[:5]):  # Show first 5
            point_type = "High" if is_high else "Low"
            print(f"  [{i}] {time}: {price:.2f} ({point_type})")
        if len(extremums_to_use) > 5:
            print(f"  ... and {len(extremums_to_use) - 5} more")

        patterns = detect_unformed_xabcd_patterns(extremums_to_use, df=self.data, log_details=True, max_patterns=100)

        # Ensure patterns is a list
        if not isinstance(patterns, list):
            print(f"Warning: detect_unformed_xabcd_patterns returned {type(patterns)} instead of list")
            patterns = []

        print(f"Found {len(patterns)} Unformed XABCD patterns")
        return self.filter_unformed_patterns(patterns, is_xabcd=True)


class AllPatternsWindow(QMainWindow):
    """Window for displaying all detected patterns simultaneously with filtering"""

    def __init__(self, parent, data, patterns, extremum_points):
        super().__init__()  # Don't pass parent to prevent auto-closing
        self.data = data
        self.patterns = patterns  # Keep original patterns dictionary
        self.extremum_points = extremum_points
        self.pattern_lines = []
        self.pattern_labels = []
        self.visible_patterns = {}  # Track which patterns are visible

        # Create mapping from extremum indices to data indices
        self.extremum_to_data_idx = {}
        for i, ext_point in enumerate(extremum_points):
            if isinstance(ext_point, tuple) and len(ext_point) >= 3:
                timestamp = ext_point[0]
                try:
                    # Convert to same format as data index if needed
                    if hasattr(timestamp, 'to_pydatetime'):
                        timestamp = timestamp.to_pydatetime()
                    # Find the index in the data
                    idx = self.data.index.get_loc(timestamp, method='nearest')
                    self.extremum_to_data_idx[i] = idx
                except:
                    self.extremum_to_data_idx[i] = i

        # Flatten all patterns into a single list with metadata
        self.all_patterns = []
        for ptype, plist in patterns.items():
            for pattern in plist:
                # Ensure pattern is a dictionary
                if not isinstance(pattern, dict):
                    if DEBUG_MODE:
                        print(f"Warning: Pattern in {ptype} is not a dictionary: {type(pattern)}, content: {pattern}")
                    continue
                try:
                    pattern_copy = pattern.copy()
                    pattern_copy['pattern_type'] = ptype

                    # Handle unformed patterns with D_projected zones/lines
                    if 'points' in pattern_copy:
                        points = pattern_copy['points']

                        # Ensure all points have indices
                        for point_name in ['A', 'B', 'C']:
                            if point_name in points:
                                point = points[point_name]
                                if isinstance(point, dict) and 'index' not in point and 'time' in point:
                                    point_time = point['time']
                                    try:
                                        if hasattr(point_time, 'to_pydatetime'):
                                            point_time = point_time.to_pydatetime()
                                        point['index'] = self.data.index.get_loc(point_time, method='nearest')
                                    except:
                                        pass  # Index will be set later if in indices dict

                        # Convert D_projected zones/lines to a displayable point
                        if 'D_projected' in points:
                            d_proj = points['D_projected']

                            # Get C point for time reference
                            c_point = points.get('C', {})
                            c_time = c_point.get('time')
                            c_index = c_point.get('index')

                            # If C doesn't have an index yet, calculate it
                            if c_index is None and c_time is not None:
                                try:
                                    # Convert timestamp if needed
                                    if hasattr(c_time, 'to_pydatetime'):
                                        c_time = c_time.to_pydatetime()
                                    c_index = self.data.index.get_loc(c_time, method='nearest')
                                    c_point['index'] = c_index
                                except:
                                    c_index = len(self.data) - 20  # Fallback

                            # Calculate D_projected point
                            d_price = None
                            d_time = None
                            d_index = None

                            # Handle prz_zones (for unformed ABCD)
                            if isinstance(d_proj, dict) and 'prz_zones' in d_proj:
                                zones = d_proj['prz_zones']
                                if zones:
                                    # Take the middle of the first zone
                                    first_zone = zones[0] if isinstance(zones, list) else zones
                                    if isinstance(first_zone, (list, tuple)) and len(first_zone) >= 2:
                                        d_price = (first_zone[0] + first_zone[1]) / 2
                                    elif isinstance(first_zone, (int, float)):
                                        d_price = first_zone

                            # Handle d_lines (for unformed XABCD)
                            elif isinstance(d_proj, dict) and 'd_lines' in d_proj:
                                lines = d_proj['d_lines']
                                if lines:
                                    # Take the average of all D lines
                                    if isinstance(lines, list) and lines:
                                        d_price = sum(lines) / len(lines)
                                    elif isinstance(lines, (int, float)):
                                        d_price = lines

                            # If we got a D price, create a proper D_projected point
                            if d_price is not None:
                                # Project D point forward in time from C
                                # Use 10 periods forward as projection (adjust as needed)
                                if c_index is not None:
                                    d_index = min(c_index + 10, len(self.data) - 1)
                                    d_time = self.data.index[d_index]
                                else:
                                    # Fallback: use last data point
                                    d_index = len(self.data) - 1
                                    d_time = self.data.index[-1]

                                # Replace D_projected with a proper point
                                points['D_projected'] = {
                                    'time': d_time,
                                    'price': d_price,
                                    'index': d_index
                                }

                                if DEBUG_MODE and ptype.startswith('unformed'):
                                    print(f"Created D_projected for {pattern_copy.get('name', 'unknown')}: index={d_index}, price={d_price:.2f}")

                    # Fix indices for XABCD patterns that use extremum indices
                    if 'indices' in pattern_copy:
                        indices = pattern_copy['indices']
                        if 'points' in pattern_copy:
                            points = pattern_copy['points']
                            # Map X, A, B, C, D indices to actual data indices
                            point_names = ['X', 'A', 'B', 'C', 'D'] if 'X' in indices else ['A', 'B', 'C', 'D']

                            # Check if this is an unformed pattern with D_projected
                            if 'D_projected' in points and 'D_projected' in indices:
                                # Add D_projected to the list if not already there
                                if 'D_projected' not in point_names:
                                    point_names.append('D_projected')

                            for point_name in point_names:
                                if point_name in indices and point_name in points:
                                    ext_idx = indices[point_name]
                                    data_idx = self.extremum_to_data_idx.get(ext_idx, ext_idx)
                                    points[point_name]['index'] = data_idx

                    self.all_patterns.append(pattern_copy)
                except Exception as e:
                    if DEBUG_MODE:
                        print(f"Error copying pattern in {ptype}: {e}, pattern: {pattern}")
                    continue

        # Initialize filtered patterns
        self.filtered_patterns = self.all_patterns.copy()

        # Get unique pattern names for checkboxes
        self.unique_pattern_names = self.getUniquePatternNames()

        # Debug: Show pattern counts by type
        if DEBUG_MODE:
            type_counts = {}
            for pattern in self.all_patterns:
                ptype = pattern.get('pattern_type', 'unknown')
                type_counts[ptype] = type_counts.get(ptype, 0) + 1
            print(f"AllPatternsWindow: Total patterns={len(self.all_patterns)}, by type: {type_counts}")
            print(f"Unique pattern names found: {self.unique_pattern_names}")

        self.setWindowTitle("All Patterns Viewer")
        self.setGeometry(200, 200, 1400, 900)

        self.initUI()

    def getUniquePatternNames(self):
        """Get all unique pattern names from all patterns"""
        unique_names = set()
        for pattern in self.all_patterns:
            # Extract base pattern name without bull/bear suffix
            name = pattern.get('name', '')
            # Remove _unformed suffix if present
            if '_unformed' in name:
                name = name.replace('_unformed', '')
            # Remove _bull or _bear suffix to get base name
            base_name = name
            for suffix in ['_bull', '_bear']:
                if suffix in base_name:
                    base_name = base_name.replace(suffix, '')
            if base_name:
                unique_names.add(base_name)
        return sorted(list(unique_names))

    def initUI(self):
        """Initialize the UI with chart and filter controls"""
        # Central widget with horizontal layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left side: Chart
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)

        # Chart widget
        self.chart = pg.PlotWidget()
        self.chart.showGrid(x=True, y=True, alpha=0.3)
        self.chart.setLabel('left', 'Price')
        self.chart.setLabel('bottom', 'Time')
        chart_layout.addWidget(self.chart)

        # Info label
        self.info_label = QLabel(f"Total: {len(self.all_patterns)} patterns")
        self.info_label.setStyleSheet("QLabel { padding: 10px; font-weight: bold; background-color: #f0f0f0; }")
        chart_layout.addWidget(self.info_label)

        main_layout.addWidget(chart_widget, 3)  # Chart gets 3/4 of space

        # Right side: Filter controls
        self.createFilterSidebar()
        main_layout.addWidget(self.filter_sidebar, 1)  # Sidebar gets 1/4 of space

        # Setup chart
        self.setupChart()

        # Initialize with filtered patterns to avoid showing too many
        self.filtered_patterns = []
        for pattern in self.all_patterns:
            ptype = pattern.get('pattern_type', '')
            # Only show formed patterns initially (unformed are unchecked by default)
            if ptype in ['abcd', 'xabcd']:
                self.filtered_patterns.append(pattern)

        # Display initial filtered patterns
        self.displayFilteredPatterns()

    def createFilterSidebar(self):
        """Create the filter sidebar with checkboxes"""
        self.filter_sidebar = QWidget()
        self.filter_sidebar.setMaximumWidth(350)
        self.filter_sidebar.setStyleSheet("QWidget { background-color: #ffffff; border-left: 2px solid #cccccc; }")

        filter_layout = QVBoxLayout(self.filter_sidebar)
        filter_layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title = QLabel("PATTERN FILTERS")
        title.setStyleSheet("font-weight: bold; font-size: 14px; color: #000000; margin-bottom: 10px; background-color: #ffffff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filter_layout.addWidget(title)

        # Count patterns by type and direction
        self.pattern_counts = {
            'abcd': 0,
            'xabcd': 0,
            'strict_abcd': 0,
            'strict_xabcd': 0,
            'comprehensive_abcd': 0,
            'comprehensive_xabcd': 0,
            'unformed': 0,
            'unformed_xabcd': 0,
            'bull': 0,
            'bear': 0
        }
        for pattern in self.all_patterns:
            ptype = pattern.get('pattern_type', '')
            if ptype in self.pattern_counts:
                self.pattern_counts[ptype] += 1

            # Count bull/bear patterns
            pattern_name = pattern.get('name', '').lower()
            if 'bull' in pattern_name:
                self.pattern_counts['bull'] += 1
            elif 'bear' in pattern_name:
                self.pattern_counts['bear'] += 1

        # Pattern Type Filter Section
        type_group = QGroupBox("Pattern Type")
        type_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 10px;
                color: #000000;
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #f0f0f0;
            }
        """)
        type_layout = QVBoxLayout(type_group)

        # Only show Strict and Unstrict pattern types (removed basic ABCD/XABCD)

        # Formed ABCD checkbox
        strict_count = self.pattern_counts.get('strict_abcd', 0)
        self.strict_abcd_checkbox = QCheckBox(f"Formed ABCD ({strict_count})")
        self.strict_abcd_checkbox.setChecked(True)  # Start checked
        self.strict_abcd_checkbox.setStyleSheet("QCheckBox { color: #000000; background-color: transparent; font-weight: bold; }")
        self.strict_abcd_checkbox.stateChanged.connect(self.onPatternTypeChanged)
        type_layout.addWidget(self.strict_abcd_checkbox)

        # Formed XABCD checkbox
        strict_xabcd_count = self.pattern_counts.get('strict_xabcd', 0)
        self.strict_xabcd_checkbox = QCheckBox(f"Formed XABCD ({strict_xabcd_count})")
        self.strict_xabcd_checkbox.setChecked(True)  # Start checked
        self.strict_xabcd_checkbox.setStyleSheet("QCheckBox { color: #000000; background-color: transparent; font-weight: bold; }")
        self.strict_xabcd_checkbox.stateChanged.connect(self.onPatternTypeChanged)
        type_layout.addWidget(self.strict_xabcd_checkbox)

        # Unformed ABCD checkbox
        comprehensive_count = self.pattern_counts.get('comprehensive_abcd', 0)
        self.comprehensive_abcd_checkbox = QCheckBox(f"Unformed ABCD ({comprehensive_count})")
        self.comprehensive_abcd_checkbox.setChecked(True)  # Start checked
        self.comprehensive_abcd_checkbox.setStyleSheet("QCheckBox { color: #000000; background-color: transparent; font-weight: bold; }")
        self.comprehensive_abcd_checkbox.stateChanged.connect(self.onPatternTypeChanged)
        type_layout.addWidget(self.comprehensive_abcd_checkbox)

        # Unformed XABCD checkbox
        comprehensive_xabcd_count = self.pattern_counts.get('comprehensive_xabcd', 0)
        self.comprehensive_xabcd_checkbox = QCheckBox(f"Unformed XABCD ({comprehensive_xabcd_count})")
        self.comprehensive_xabcd_checkbox.setChecked(True)  # Start checked
        self.comprehensive_xabcd_checkbox.setStyleSheet("QCheckBox { color: #000000; background-color: transparent; font-weight: bold; }")
        self.comprehensive_xabcd_checkbox.stateChanged.connect(self.onPatternTypeChanged)
        type_layout.addWidget(self.comprehensive_xabcd_checkbox)

        filter_layout.addWidget(type_group)

        # Bull/Bear Filter Section
        direction_group = QGroupBox("Direction")
        direction_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 10px;
                color: #000000;
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #f0f0f0;
            }
        """)
        direction_layout = QVBoxLayout(direction_group)

        self.bull_checkbox = QCheckBox(f"Bullish Patterns ({self.pattern_counts['bull']})")
        self.bull_checkbox.setChecked(True)
        self.bull_checkbox.setStyleSheet("QCheckBox { color: #006400; font-weight: bold; background-color: transparent; }")
        self.bull_checkbox.stateChanged.connect(self.applyFilters)
        direction_layout.addWidget(self.bull_checkbox)

        self.bear_checkbox = QCheckBox(f"Bearish Patterns ({self.pattern_counts['bear']})")
        self.bear_checkbox.setChecked(True)
        self.bear_checkbox.setStyleSheet("QCheckBox { color: #8B0000; font-weight: bold; background-color: transparent; }")
        self.bear_checkbox.stateChanged.connect(self.applyFilters)
        direction_layout.addWidget(self.bear_checkbox)

        filter_layout.addWidget(direction_group)

        # Specific Pattern Names Section
        patterns_group = QGroupBox("Specific Patterns")
        patterns_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                margin-top: 10px;
                color: #000000;
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #f0f0f0;
            }
        """)

        # Create scroll area for pattern checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #ffffff;
                border: 1px solid #dddddd;
            }
        """)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #ffffff;")
        patterns_layout = QVBoxLayout(scroll_content)

        # Add "Select All" / "Deselect All" buttons
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        select_all_btn.clicked.connect(self.selectAllPatterns)

        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        deselect_all_btn.clicked.connect(self.deselectAllPatterns)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        patterns_layout.addLayout(button_layout)

        # Create checkboxes for each unique pattern name
        self.pattern_checkboxes = {}
        for pattern_name in self.unique_pattern_names:
            checkbox = QCheckBox(pattern_name)
            checkbox.setChecked(True)
            checkbox.setStyleSheet("QCheckBox { color: #000000; background-color: transparent; }")
            checkbox.stateChanged.connect(self.applyFilters)
            self.pattern_checkboxes[pattern_name] = checkbox
            patterns_layout.addWidget(checkbox)

        scroll_area.setWidget(scroll_content)
        patterns_group_layout = QVBoxLayout(patterns_group)
        patterns_group_layout.addWidget(scroll_area)

        filter_layout.addWidget(patterns_group)

        # Add stretch at the bottom
        filter_layout.addStretch()

    def selectAllPatterns(self):
        """Select all pattern checkboxes"""
        for checkbox in self.pattern_checkboxes.values():
            checkbox.setChecked(True)

    def deselectAllPatterns(self):
        """Deselect all pattern checkboxes"""
        for checkbox in self.pattern_checkboxes.values():
            checkbox.setChecked(False)

    def onPatternTypeChanged(self):
        """Handle pattern type checkbox changes to sync specific patterns"""
        # Categorize patterns by type
        abcd_patterns = ['AB=CD']

        # Get all pattern names and categorize them
        for pattern_name in self.pattern_checkboxes.keys():
            # Check if it's an ABCD-type pattern
            if 'AB' in pattern_name or 'CD' in pattern_name:
                if pattern_name not in abcd_patterns:
                    abcd_patterns.append(pattern_name)

        # All other patterns are XABCD patterns
        xabcd_patterns = [name for name in self.pattern_checkboxes.keys()
                         if name not in abcd_patterns]

        # Block signals to prevent recursion
        for checkbox in self.pattern_checkboxes.values():
            checkbox.blockSignals(True)

        try:
            # All unstrict checkbox handlers removed
            pass

        finally:
            # Re-enable signals
            for checkbox in self.pattern_checkboxes.values():
                checkbox.blockSignals(False)

        # Apply filters after syncing
        self.applyFilters()

    def applyFilters(self):
        """Apply filters and redraw patterns"""
        # Filter patterns based on checkboxes
        self.filtered_patterns = []

        for pattern in self.all_patterns:
            # Check pattern type
            ptype = pattern.get('pattern_type', '')
            # Only keep strict and unstrict patterns
            if ptype == 'strict_abcd' and not hasattr(self, 'strict_abcd_checkbox'):
                continue
            if ptype == 'strict_abcd' and hasattr(self, 'strict_abcd_checkbox') and not self.strict_abcd_checkbox.isChecked():
                continue
            if ptype == 'strict_xabcd' and not hasattr(self, 'strict_xabcd_checkbox'):
                continue
            if ptype == 'strict_xabcd' and hasattr(self, 'strict_xabcd_checkbox') and not self.strict_xabcd_checkbox.isChecked():
                continue
            # Removed all unstrict pattern type checks

            # Check direction
            pattern_name = pattern.get('name', '').lower()
            is_bullish = 'bull' in pattern_name
            is_bearish = 'bear' in pattern_name

            if is_bullish and not self.bull_checkbox.isChecked():
                continue
            if is_bearish and not self.bear_checkbox.isChecked():
                continue

            # Check specific pattern name
            base_name = pattern.get('name', '')
            original_name = base_name
            if '_unformed' in base_name:
                base_name = base_name.replace('_unformed', '')
            for suffix in ['_bull', '_bear']:
                if suffix in base_name:
                    base_name = base_name.replace(suffix, '')

            # Debug unformed patterns
            if DEBUG_MODE and 'unformed' in ptype and len(self.filtered_patterns) < 3:
                print(f"  Checking unformed pattern: original={original_name}, base={base_name}, in checkboxes={base_name in self.pattern_checkboxes}")
                if base_name in self.pattern_checkboxes:
                    print(f"    Checkbox {base_name} is checked: {self.pattern_checkboxes[base_name].isChecked()}")

            # For unformed patterns, we don't require specific pattern checkbox
            # Only check specific pattern names for formed patterns
            if 'unformed' not in ptype:
                if base_name in self.pattern_checkboxes:
                    if not self.pattern_checkboxes[base_name].isChecked():
                        continue

            self.filtered_patterns.append(pattern)

        # Debug: Show filter results
        if DEBUG_MODE:
            formed_count = len([p for p in self.filtered_patterns if p.get('pattern_type', '') in ['abcd', 'xabcd']])
            unformed_count = len([p for p in self.filtered_patterns if 'unformed' in p.get('pattern_type', '')])
            print(f"applyFilters: Showing {len(self.filtered_patterns)} patterns (formed: {formed_count}, unformed: {unformed_count})")

        # Update info label
        self.info_label.setText(f"Displaying {len(self.filtered_patterns)} of {len(self.all_patterns)} patterns")

        # Redraw patterns
        self.clearPatternLines()
        self.displayFilteredPatterns()

    def clearPatternLines(self):
        """Clear all pattern lines and labels from chart"""
        for line in self.pattern_lines:
            self.chart.removeItem(line)
        self.pattern_lines = []

        for label in self.pattern_labels:
            self.chart.removeItem(label)
        self.pattern_labels = []

    def setupChart(self):
        """Setup the chart with candlestick data"""
        self.chart.setBackground('white')
        self.chart.setLabel('left', 'Price')
        self.chart.setLabel('bottom', 'Time')
        self.chart.showGrid(x=True, y=True)

        # Add candlestick data
        candlestick_item = CandlestickItem(self.data)
        self.chart.addItem(candlestick_item)

        # Add extremum points - properly aligned with candlestick indices
        if self.extremum_points:
            for point in self.extremum_points:
                # Handle both tuple and dict formats
                if isinstance(point, tuple):
                    # Format: (timestamp, price, is_high)
                    if len(point) >= 3:
                        # Find the correct index in the data
                        try:
                            timestamp = point[0]
                            # Convert to same format as data index if needed
                            if hasattr(timestamp, 'to_pydatetime'):
                                timestamp = timestamp.to_pydatetime()
                            # Find the index in the data
                            idx = self.data.index.get_loc(timestamp, method='nearest')

                            color = 'red' if point[2] else 'green'
                            scatter = pg.ScatterPlotItem([idx], [point[1]],
                                                       symbol='o', size=10,
                                                       brush=pg.mkBrush(color))
                            self.chart.addItem(scatter)
                        except:
                            pass  # Skip if we can't find the index
                elif isinstance(point, dict):
                    # Format: {'index': i, 'price': p, 'type': 'High'/'Low'}
                    color = 'red' if point.get('type') == 'High' else 'green'
                    scatter = pg.ScatterPlotItem([point.get('index', 0)], [point['price']],
                                               symbol='o', size=10,
                                               brush=pg.mkBrush(color))
                    self.chart.addItem(scatter)

    def displayAllPatterns(self):
        """Display all patterns on initial load"""
        self.displayFilteredPatterns()

    def displayFilteredPatterns(self):
        """Display filtered patterns on the chart with different colors"""
        # Display ALL patterns - no limits for 100% accuracy
        patterns_to_display = self.filtered_patterns

        # Update info label to show pattern count
        self.info_label.setText(f"Displaying {len(self.filtered_patterns)} of {len(self.all_patterns)} patterns")

        # First, add index values to all patterns if missing
        for pattern in patterns_to_display:
            if 'points' in pattern and isinstance(pattern['points'], dict):
                for point_name, point_data in pattern['points'].items():
                    if isinstance(point_data, dict):
                        # If we already have an index, skip
                        if 'index' in point_data and point_data['index'] is not None:
                            continue

                        # Try to find index from time
                        if 'time' in point_data:
                            try:
                                time_val = point_data['time']
                                # Convert numpy datetime64 to pandas timestamp if needed
                                if hasattr(time_val, 'item'):
                                    time_val = pd.Timestamp(time_val.item())
                                elif hasattr(time_val, 'to_pydatetime'):
                                    time_val = time_val.to_pydatetime()

                                # Find the closest index in the data
                                idx = self.data.index.get_indexer([time_val], method='nearest')[0]
                                point_data['index'] = idx
                                print(f"Mapped {point_name} time {time_val} to index {idx}")
                            except Exception as e:
                                print(f"Error mapping time to index for {point_name}: {e}")
                                # Try to use a sequential index based on point name
                                default_indices = {'X': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4, 'D_projected': 4}
                                point_data['index'] = default_indices.get(point_name, 0)

        # Define colors for different pattern types
        colors = {
            'abcd': {'bull': (0, 255, 0, 150),        # Green
                     'bear': (0, 200, 0, 150),        # Darker green
                     'default': (0, 255, 0, 150)},
            'xabcd': {'bull': (255, 107, 107, 150),   # Red
                      'bear': (200, 50, 50, 150),     # Darker red
                      'default': (255, 107, 107, 150)},
            'unformed': {'bull': (144, 238, 144, 150),  # Light green
                        'bear': (144, 200, 144, 150),   # Darker light green
                        'default': (144, 238, 144, 150)},
            'unformed_xabcd': {'bull': (255, 182, 182, 150),  # Light red
                              'bear': (200, 150, 150, 150),   # Darker light red
                              'default': (255, 182, 182, 150)}
        }

        pattern_count = 0
        for pattern in patterns_to_display:
            pattern_type = pattern.get('pattern_type', 'unknown')
            pattern_name = pattern.get('name', '').lower()
            is_bullish = 'bull' in pattern_name

            # Determine color
            if pattern_type in colors:
                color_set = colors[pattern_type]
                if is_bullish and 'bull' in color_set:
                    color = color_set['bull']
                elif not is_bullish and 'bear' in color_set:
                    color = color_set['bear']
                else:
                    color = color_set['default']
            else:
                color = (128, 128, 128, 150)  # Gray for unknown

            # Determine line style
            if 'unformed' in pattern_type:
                style = pg.QtCore.Qt.PenStyle.DashLine
            else:
                style = pg.QtCore.Qt.PenStyle.SolidLine

            # Draw pattern lines
            try:
                if 'points' in pattern and isinstance(pattern['points'], dict):
                    points = pattern['points']
                    point_names = ['X', 'A', 'B', 'C', 'D'] if 'X' in points else ['A', 'B', 'C', 'D']

                    # Handle projected D point for unformed patterns
                    if 'D_projected' in points:
                        # For unformed patterns, replace D with D_projected
                        if 'D' in point_names:
                            point_names = [p if p != 'D' else 'D_projected' for p in point_names]
                        elif 'D_projected' not in point_names:
                            point_names.append('D_projected')

                    # Debug: Print first few patterns' points, especially unformed ones
                    if pattern_count < 3 and 'unformed' in pattern.get('pattern_type', ''):
                        print(f"\nDEBUG - Pattern #{pattern_count} ({pattern.get('name', 'unknown')}, type={pattern.get('pattern_type', 'unknown')}):")
                        print(f"  Available points: {list(points.keys())}")
                        for pn in point_names:
                            if pn in points:
                                pt = points[pn]
                                print(f"  {pn}: index={pt.get('index')}, price={pt.get('price')}, time={pt.get('time')}")

                    # Draw lines between consecutive points
                    for i in range(len(point_names) - 1):
                        p1_name = point_names[i]
                        p2_name = point_names[i + 1]

                        if p1_name in points and p2_name in points:
                            p1 = points[p1_name]
                            p2 = points[p2_name]

                            if isinstance(p1, dict) and isinstance(p2, dict):
                                # Ensure we have valid indices for both points
                                idx1 = p1.get('index')
                                idx2 = p2.get('index')
                                price1 = p1.get('price')
                                price2 = p2.get('price')

                                if idx1 is not None and idx2 is not None and price1 is not None and price2 is not None:
                                    # Make sure indices are different for visible lines
                                    if idx1 != idx2:
                                        pen = pg.mkPen(color=color, width=3, style=style)
                                        line = pg.PlotDataItem([idx1, idx2],
                                                             [price1, price2],
                                                             pen=pen)
                                        self.chart.addItem(line)
                                        self.pattern_lines.append(line)
                                    else:
                                        print(f"Warning: Same index {idx1} for {p1_name} and {p2_name}")

                    # Add pattern labels
                    if 'A' in points and isinstance(points['A'], dict) and 'price' in points['A']:
                        label_text = f"{pattern.get('name', 'Unknown')}"
                        label_color = color[:3]  # Remove alpha for text
                        text_item = pg.TextItem(label_text, color=label_color, anchor=(0, 1))
                        text_item.setPos(points['A'].get('index', 0), points['A']['price'])
                        self.chart.addItem(text_item)
                        self.pattern_labels.append(text_item)
            except Exception as e:
                if DEBUG_MODE:
                    print(f"Error drawing pattern {pattern.get('name', 'unknown')}: {e}")

            pattern_count += 1


class PatternViewerWindow(QMainWindow):
    """Separate window for viewing detected patterns"""

    def __init__(self, parent, patterns, data, extremum_points):
        super().__init__(parent)
        self.patterns = patterns
        self.data = data
        self.extremum_points = extremum_points
        self.current_index = 0
        self.all_patterns = []

        # Flatten patterns
        for ptype, plist in patterns.items():
            for pattern in plist:
                pattern['pattern_type'] = ptype
                self.all_patterns.append(pattern)

        # No deduplication needed with exact pattern matching
        # Each XABCD combination maps to at most one specific pattern name

        # Initialize filtered patterns (will be updated by filters)
        self.filtered_patterns = self.all_patterns.copy()

        self.initUI()

        # Analyze patterns and update filter counts
        self.analyzePatterns()
        self.updateFilterCounts()

    def deduplicate_patterns(self, patterns):
        """Remove duplicate patterns based on ABCD points and pattern name"""
        unique_patterns = []
        seen_patterns = set()

        for pattern in patterns:
            # Create a unique identifier for each pattern based on key characteristics
            try:
                # Get pattern points - handle both regular and unformed patterns
                if 'points' in pattern:
                    points = pattern['points']
                    # For unformed patterns with projected D
                    if 'D_projected' in points:
                        pattern_key = (
                            pattern['name'],
                            round(points['A']['price'], 2),
                            round(points['B']['price'], 2),
                            round(points['C']['price'], 2),
                            round(points['D_projected']['price'], 2)
                        )
                    else:
                        # For regular patterns with actual D point
                        pattern_key = (
                            pattern['name'],
                            round(points['A']['price'], 2),
                            round(points['B']['price'], 2),
                            round(points['C']['price'], 2),
                            round(points['D']['price'], 2)
                        )
                else:
                    # Fallback: use entire pattern as key if structure is unexpected
                    pattern_key = str(pattern)

                if pattern_key not in seen_patterns:
                    seen_patterns.add(pattern_key)
                    unique_patterns.append(pattern)

            except (KeyError, TypeError) as e:
                # If we can't parse the pattern structure, include it to be safe
                unique_patterns.append(pattern)

        if len(patterns) != len(unique_patterns):
            print(f"Deduplication: Removed {len(patterns) - len(unique_patterns)} duplicate patterns")

        return unique_patterns

    def initUI(self):
        """Initialize the pattern viewer window UI"""
        self.setWindowTitle("Pattern Viewer")
        self.setGeometry(150, 150, 1200, 800)

        # Central widget with horizontal layout for chart and sidebar
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left side: Chart and navigation
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)

        # Chart widget
        self.chart = PlotWidget(title="Pattern Visualization")
        self.chart.showGrid(x=True, y=True, alpha=0.3)
        self.chart.setLabel('left', 'Price')
        self.chart.setLabel('bottom', 'Time')

        # Initialize crosshair functionality for pattern viewer
        self.setupPatternCrosshair()

        chart_layout.addWidget(self.chart)

        # Navigation controls
        nav_widget = QWidget()
        nav_layout = QHBoxLayout(nav_widget)

        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.previousPattern)
        nav_layout.addWidget(self.prev_btn)

        self.pattern_info = QLabel("No patterns")
        self.pattern_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_layout.addWidget(self.pattern_info)

        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.nextPattern)
        nav_layout.addWidget(self.next_btn)

        chart_layout.addWidget(nav_widget)

        # Pattern details text
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(120)
        chart_layout.addWidget(self.details_text)

        main_layout.addWidget(chart_widget, 3)  # Give chart area 3/4 of space

        # Right side: Filter controls sidebar
        filter_sidebar = QWidget()
        filter_sidebar.setMaximumWidth(300)
        filter_sidebar.setStyleSheet("QWidget { background-color: #ffffff; border-left: 2px solid #333; }")
        filter_layout = QVBoxLayout(filter_sidebar)
        filter_layout.setContentsMargins(10, 10, 10, 10)

        # Sidebar title
        sidebar_title = QLabel("PATTERN FILTERS")
        sidebar_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #333; margin-bottom: 10px;")
        sidebar_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        filter_layout.addWidget(sidebar_title)

        # Bull/Bear filter section
        bullbear_group = QGroupBox("Formation Type")
        bullbear_group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; color: #000; background-color: #fff; } QGroupBox::title { subcontrol-origin: margin; padding: 5px; color: #000; font-weight: bold; }")
        bullbear_layout = QVBoxLayout(bullbear_group)

        # Bulls row with light green background
        bulls_widget = QWidget()
        bulls_row = QHBoxLayout(bulls_widget)
        bulls_row.setSpacing(5)
        bulls_row.setContentsMargins(8, 4, 8, 4)
        bulls_widget.setStyleSheet("QWidget { background-color: #f0fff0; border-radius: 3px; }")  # Very light green

        self.bull_checkbox = QCheckBox("Bulls")
        self.bull_checkbox.setChecked(True)
        self.bull_checkbox.setStyleSheet("QCheckBox { color: #000; font-weight: bold; font-size: 13px; background-color: transparent; }")
        self.bull_checkbox.stateChanged.connect(self.applyFilters)
        self.bull_label = QLabel("(0)")
        self.bull_label.setStyleSheet("color: #228b22; font-weight: bold; font-size: 13px; margin-left: 5px; background-color: transparent;")  # Green for bulls
        self.bull_label.setFixedWidth(40)
        bulls_row.addWidget(self.bull_checkbox)
        bulls_row.addWidget(self.bull_label)
        bulls_row.addStretch()
        bullbear_layout.addWidget(bulls_widget)

        # Bears row with light red background
        bears_widget = QWidget()
        bears_row = QHBoxLayout(bears_widget)
        bears_row.setSpacing(5)
        bears_row.setContentsMargins(8, 4, 8, 4)
        bears_widget.setStyleSheet("QWidget { background-color: #fff0f0; border-radius: 3px; }")  # Very light red

        self.bear_checkbox = QCheckBox("Bears")
        self.bear_checkbox.setChecked(True)
        self.bear_checkbox.setStyleSheet("QCheckBox { color: #000; font-weight: bold; font-size: 13px; background-color: transparent; }")
        self.bear_checkbox.stateChanged.connect(self.applyFilters)
        self.bear_label = QLabel("(0)")
        self.bear_label.setStyleSheet("color: #dc143c; font-weight: bold; font-size: 13px; margin-left: 5px; background-color: transparent;")  # Red for bears
        self.bear_label.setFixedWidth(40)
        bears_row.addWidget(self.bear_checkbox)
        bears_row.addWidget(self.bear_label)
        bears_row.addStretch()
        bullbear_layout.addWidget(bears_widget)

        filter_layout.addWidget(bullbear_group)

        # Pattern type filter section
        pattern_group = QGroupBox("Pattern Variations")
        pattern_group.setStyleSheet("QGroupBox { font-weight: bold; margin-top: 10px; color: #000; background-color: #fff; } QGroupBox::title { subcontrol-origin: margin; padding: 5px; color: #000; font-weight: bold; }")
        pattern_layout = QVBoxLayout(pattern_group)

        # Initialize pattern type checkboxes and labels
        self.pattern_checkboxes = {}
        self.pattern_labels = {}

        # Common pattern types we expect to see
        pattern_types = ['1a', '1b', '2', '3', '4', '5', '6a', '6b', '6c', '6d', '6e']

        for i, ptype in enumerate(pattern_types):
            # Create a container widget for the row to apply background color
            row_widget = QWidget()
            pattern_row = QHBoxLayout(row_widget)
            pattern_row.setSpacing(5)  # Reduce spacing between elements
            pattern_row.setContentsMargins(8, 4, 8, 4)  # Add padding around the row

            # Alternate row colors - light blue and light gray
            if i % 2 == 0:
                row_widget.setStyleSheet("QWidget { background-color: #f0f8ff; border-radius: 3px; }")  # Light blue
            else:
                row_widget.setStyleSheet("QWidget { background-color: #f5f5f5; border-radius: 3px; }")  # Light gray

            # Create checkbox with pattern type name
            checkbox = QCheckBox(f"{ptype}")  # Just show the type (1a, 1b, etc.)
            checkbox.setChecked(True)
            checkbox.setStyleSheet("QCheckBox { color: #000; font-weight: bold; font-size: 13px; background-color: transparent; }")
            checkbox.stateChanged.connect(self.applyFilters)

            # Create count label with alternating colors to match row background
            label = QLabel("(0)")
            if i % 2 == 0:
                # Light blue rows get dark blue numbers for better contrast
                label.setStyleSheet("color: #0066cc; font-weight: bold; font-size: 13px; margin-left: 5px; background-color: transparent;")
            else:
                # Light gray rows get dark gray numbers for better contrast
                label.setStyleSheet("color: #666666; font-weight: bold; font-size: 13px; margin-left: 5px; background-color: transparent;")
            label.setFixedWidth(40)  # Fixed width for alignment

            self.pattern_checkboxes[ptype] = checkbox
            self.pattern_labels[ptype] = label

            # Add checkbox and immediately add its count label
            pattern_row.addWidget(checkbox)
            pattern_row.addWidget(label)
            pattern_row.addStretch()  # Push everything to the left

            # Add the row widget to the main layout
            pattern_layout.addWidget(row_widget)

        filter_layout.addWidget(pattern_group)

        filter_layout.addStretch()  # Push everything to top

        # Filter control buttons at bottom
        filter_buttons = QVBoxLayout()

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.selectAllFilters)
        self.select_all_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        filter_buttons.addWidget(self.select_all_btn)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self.clearAllFilters)
        self.clear_all_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")
        filter_buttons.addWidget(self.clear_all_btn)

        filter_layout.addLayout(filter_buttons)

        main_layout.addWidget(filter_sidebar, 1)  # Give sidebar 1/4 of space

        # Show first pattern
        if self.filtered_patterns:
            self.showPattern(0)

    def setupPatternCrosshair(self):
        """Setup crosshair functionality for the pattern chart"""
        # Set up mouse tracking with reduced update frequency to prevent screen flicker
        self.proxy = pg.SignalProxy(self.chart.scene().sigMouseMoved, rateLimit=15, slot=self.patternMouseMoved)
        self.chart.setMouseTracking(True)

        # Track last position to avoid unnecessary updates
        self.last_mouse_pos = None
        self.label_update_counter = 0

    def patternMouseMoved(self, evt):
        """Handle mouse movement for crosshair updates on pattern chart"""
        if not hasattr(self, 'vLine') or not hasattr(self, 'hLine'):
            return  # Crosshair not yet created

        pos = evt[0]  # SignalProxy provides position in a list

        # Check if position actually changed to avoid unnecessary updates
        if self.last_mouse_pos is not None and abs(pos.x() - self.last_mouse_pos.x()) < 2 and abs(pos.y() - self.last_mouse_pos.y()) < 2:
            return  # Position hasn't changed significantly

        self.last_mouse_pos = pos

        if self.chart.sceneBoundingRect().contains(pos):
            # Show crosshair elements only if not already visible
            if not self.vLine.isVisible():
                self.vLine.setVisible(True)
                self.hLine.setVisible(True)
                self.x_axis_label.setVisible(True)
                self.y_axis_label.setVisible(True)
                self.crosshair_label.setVisible(True)

            mousePoint = self.chart.plotItem.vb.mapSceneToView(pos)
            x, y = mousePoint.x(), mousePoint.y()

            # Update crosshair position efficiently
            self.vLine.setPos(x)
            self.hLine.setPos(y)

            # Update axis labels less frequently to reduce screen refresh
            self.label_update_counter += 1
            if self.label_update_counter % 3 == 0:  # Update labels every 3rd mouse move
                self.updatePatternAxisLabels(x, y)
                self.updatePatternCrosshairLabel(x, y)
        else:
            # Hide crosshair when mouse is outside chart area
            if self.vLine.isVisible():
                self.vLine.setVisible(False)
                self.hLine.setVisible(False)
                self.x_axis_label.setVisible(False)
                self.y_axis_label.setVisible(False)
                self.crosshair_label.setVisible(False)

    def updatePatternAxisLabels(self, x, y):
        """Update TradingView-style axis labels for pattern viewer"""
        try:
            # Get current data for date formatting
            if self.data is None or len(self.data) == 0:
                return

            # Get view range for positioning
            view_box = self.chart.plotItem.vb
            view_range = view_box.viewRange()

            # Format and position X-axis (time) label
            x_int = int(round(x))
            if 0 <= x_int < len(self.data):
                date = self.data.index[x_int]
                if hasattr(date, 'strftime'):
                    time_str = date.strftime('%Y-%m-%d %H:%M')
                else:
                    time_str = str(date)[:16]

                # Position near bottom of chart area, visible inside the chart
                x_label_y = view_range[1][0] + (view_range[1][1] - view_range[1][0]) * 0.05
                self.x_axis_label.setText(time_str)
                self.x_axis_label.setPos(x, x_label_y)

            # Format and position Y-axis (price) label
            price_str = f"${y:,.2f}"

            # Position at left edge of chart, centered on crosshair
            y_label_x = view_range[0][0] + (view_range[0][1] - view_range[0][0]) * 0.02
            self.y_axis_label.setText(price_str)
            self.y_axis_label.setPos(y_label_x, y)

        except Exception as e:
            if DEBUG_MODE: print(f"Pattern axis labels error: {str(e)}")

    def updatePatternCrosshairLabel(self, x, y):
        """Update crosshair label with current price and date for pattern viewer"""
        try:
            # Check if display_data is available (set when a pattern is displayed)
            if not hasattr(self, 'display_data') or self.display_data is None:
                # Fall back to using full data if display_data not available
                if self.data is None or len(self.data) == 0:
                    return
                data_to_use = self.data
                index_offset = 0
            else:
                # Use the display_data which corresponds to what's shown on the chart
                data_to_use = self.display_data
                # No offset needed as display_data is already reset_index(drop=True)
                index_offset = 0

            # Convert x position to integer index
            x_int = int(round(x))

            # Ensure x is within the displayed data bounds
            if 0 <= x_int < len(data_to_use):
                # Get date and OHLC data for this index
                # Note: display_data still has the original time index
                date = data_to_use.index[x_int]
                row = data_to_use.iloc[x_int]

                # Format date - handle different date types
                if hasattr(date, 'strftime'):
                    date_str = date.strftime('%Y-%m-%d %H:%M')
                else:
                    date_str = str(date)[:16]

                # Format price information
                open_price = float(row['Open'])
                high_price = float(row['High'])
                low_price = float(row['Low'])
                close_price = float(row['Close'])

                # Create label text with better formatting
                label_text = f"Time: {date_str}\n"
                label_text += f"Open:  ${open_price:,.2f}\n"
                label_text += f"High:  ${high_price:,.2f}\n"
                label_text += f"Low:   ${low_price:,.2f}\n"
                label_text += f"Close: ${close_price:,.2f}\n"
                label_text += f"Price: ${y:,.2f}"

                # Position label at top-left of visible chart area
                view_box = self.chart.plotItem.vb
                view_range = view_box.viewRange()

                # Calculate position with padding from edges
                x_range = view_range[0][1] - view_range[0][0]
                y_range = view_range[1][1] - view_range[1][0]

                label_x = view_range[0][0] + x_range * 0.02  # 2% from left edge
                label_y = view_range[1][1] - y_range * 0.05  # 5% from top edge

                # Update label
                self.crosshair_label.setText(label_text)
                self.crosshair_label.setPos(label_x, label_y)

                # Force label to be visible and on top
                self.crosshair_label.setVisible(True)
                self.crosshair_label.setZValue(1001)  # Bring to front

        except Exception as e:
            if DEBUG_MODE: print(f"Pattern crosshair label error: {str(e)}")

    def addPatternCrosshairAfterPlot(self):
        """Add crosshair elements after chart is plotted for pattern viewer"""
        try:
            # Re-create and add crosshair lines (they get cleared with chart.clear())
            self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('cyan', width=2, style=Qt.PenStyle.DashLine))
            self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('cyan', width=2, style=Qt.PenStyle.DashLine))

            self.chart.addItem(self.vLine, ignoreBounds=True)
            self.chart.addItem(self.hLine, ignoreBounds=True)

            # Create TradingView-style axis labels
            # X-axis (time) label
            self.x_axis_label = pg.TextItem('', anchor=(0.5, 0), color='white',
                                          fill=pg.mkBrush(0, 100, 255, 220),
                                          border=pg.mkPen('white', width=2))
            self.x_axis_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
            self.x_axis_label.setZValue(1000)  # Ensure it's on top
            self.chart.addItem(self.x_axis_label)

            # Y-axis (price) label
            self.y_axis_label = pg.TextItem('', anchor=(0, 0.5), color='white',
                                          fill=pg.mkBrush(0, 100, 255, 220),
                                          border=pg.mkPen('white', width=2))
            self.y_axis_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
            self.y_axis_label.setZValue(1000)  # Ensure it's on top
            self.chart.addItem(self.y_axis_label)

            # Create comprehensive OHLC data label
            self.crosshair_label = pg.TextItem('', anchor=(0, 0), color='white',
                                             fill=pg.mkBrush(0, 0, 0, 150),
                                             border=pg.mkPen('cyan', width=1))
            self.crosshair_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
            self.crosshair_label.setZValue(1001)  # On top of other elements
            self.chart.addItem(self.crosshair_label)

            # Initially hide crosshair (will show when mouse moves)
            self.vLine.setVisible(False)
            self.hLine.setVisible(False)
            self.x_axis_label.setVisible(False)
            self.y_axis_label.setVisible(False)
            self.crosshair_label.setVisible(False)

            # Ensure mouse tracking is enabled
            self.chart.setMouseTracking(True)

        except Exception as e:
            if DEBUG_MODE: print(f"Error setting up pattern crosshair: {str(e)}")

    def showPattern(self, index):
        """Display a specific pattern"""
        if not self.filtered_patterns:
            return

        self.current_index = index
        pattern = self.filtered_patterns[index]


        # Update info label
        self.pattern_info.setText(
            f"Pattern {index + 1} of {len(self.filtered_patterns)}: {pattern['name']}"
        )

        # Clear chart
        self.chart.clear()

        # Draw pattern
        self.drawPattern(pattern)

        # Add crosshair after plotting (since chart.clear() removes it)
        self.addPatternCrosshairAfterPlot()

        # Update details
        self.updateDetails(pattern)

    def drawPattern(self, pattern):
        """Draw pattern on chart with extremum points"""
        points = pattern['points']

        # Get all pattern dates for determining the range
        pattern_dates = []
        for point_name in ['X', 'A', 'B', 'C', 'D']:
            if point_name in points and 'time' in points[point_name]:
                pattern_dates.append(points[point_name]['time'])

        if not pattern_dates:
            return

        # Find the data range for this pattern
        min_date = min(pattern_dates)
        max_date = max(pattern_dates)

        # Get data indices
        try:
            min_idx = self.data.index.get_loc(min_date)
            max_idx = self.data.index.get_loc(max_date)
        except:
            # If exact date not found, find nearest
            min_idx = np.argmin(np.abs(self.data.index - min_date))
            max_idx = np.argmin(np.abs(self.data.index - max_date))

        # Expand the range for context
        display_min = max(0, min_idx - 20)
        display_max = min(len(self.data), max_idx + 20)

        # Get the data slice
        display_data = self.data.iloc[display_min:display_max]

        # Store the display data and range for crosshair access
        self.display_data = display_data
        self.display_min = display_min
        self.display_max = display_max

        # Create candlestick chart for the relevant range
        candles = CandlestickItem(display_data.reset_index(drop=True))
        self.chart.addItem(candles)

        # Set Y-axis range based on the actual data
        y_min = display_data['Low'].min() * 0.999  # Add 0.1% padding
        y_max = display_data['High'].max() * 1.001  # Add 0.1% padding
        self.chart.setYRange(y_min, y_max, padding=0)

        # Enable auto-range but keep Y fixed to our calculated range
        self.chart.enableAutoRange(axis='x')
        self.chart.setAutoVisible(y=True, x=True)

        # Plot ALL extremum points in the visible range as reference
        if self.extremum_points:
            for ep_time, ep_price, is_high in self.extremum_points:
                # Check if this extremum is in our display range
                try:
                    ep_idx = self.data.index.get_loc(ep_time)
                except (KeyError, ValueError):
                    try:
                        ep_idx = np.argmin(np.abs(self.data.index - ep_time))
                    except Exception as e:
                        print(f"Warning: Could not find index for extremum time {ep_time}: {e}")
                        continue  # Skip this extremum point

                display_ep_idx = ep_idx - display_min

                if 0 <= display_ep_idx < len(display_data):
                    # Plot extremum point
                    if is_high:
                        scatter = pg.ScatterPlotItem(
                            x=[display_ep_idx], y=[ep_price],
                            pen=pg.mkPen('#00BFFF', width=1),
                            brush=pg.mkBrush('#00BFFF'),
                            size=8,
                            symbol='t'
                        )
                    else:
                        scatter = pg.ScatterPlotItem(
                            x=[display_ep_idx], y=[ep_price],
                            pen=pg.mkPen('#FF8C00', width=1),
                            brush=pg.mkBrush('#FF8C00'),
                            size=8,
                            symbol='t1'
                        )
                    self.chart.addItem(scatter)

        # Now plot the pattern lines on top
        # Calculate relative positions within the display range
        x_coords = []
        y_coords = []
        labels = []

        if 'X' in points:
            point_order = ['X', 'A', 'B', 'C', 'D'] if 'D' in points else ['X', 'A', 'B', 'C']
        else:
            point_order = ['A', 'B', 'C', 'D'] if 'D' in points else ['A', 'B', 'C']

        for point_name in point_order:
            if point_name in points and 'time' in points[point_name]:
                point_time = points[point_name]['time']
                point_price = points[point_name]['price']

                # Find the position in our display data
                try:
                    actual_idx = self.data.index.get_loc(point_time)
                except:
                    actual_idx = np.argmin(np.abs(self.data.index - point_time))

                # Convert to display coordinates
                display_idx = actual_idx - display_min

                if 0 <= display_idx < len(display_data):
                    x_coords.append(display_idx)
                    y_coords.append(point_price)
                    labels.append(point_name)

        # Draw pattern lines
        if len(x_coords) >= 2:
            # Determine color based on pattern type
            is_bullish = 'bull' in pattern['name'].lower()
            color = '#00BFFF' if is_bullish else '#FF8C00'

            # Draw lines connecting pattern points with thicker line
            pen = pg.mkPen(color=color, width=3, style=Qt.PenStyle.SolidLine)
            # Use bright yellow for points with black border for maximum visibility
            point_pen = pg.mkPen('#000000', width=2)  # Black border
            point_brush = pg.mkBrush('#FFFF00')  # Bright yellow fill
            self.chart.plot(x_coords, y_coords, pen=pen, symbol='o',
                          symbolPen=point_pen, symbolBrush=point_brush, symbolSize=16)

            # Add labels for each point with better visibility, including price values
            for i, (x, y, label) in enumerate(zip(x_coords, y_coords, labels)):
                # Create label with point name and price value
                label_text = f"{label}\n{y:.2f}"
                text = pg.TextItem(label_text, color='#000000', anchor=(0.5, 1.2))
                text.setPos(x, y)
                # Set font without any background or border
                text.setFont(QFont('Arial', 11, QFont.Weight.Bold))
                self.chart.addItem(text)

        # Handle projected D point/zones for unformed patterns
        if 'D_projected' in points:
            d_projected = points['D_projected']
            if len(x_coords) > 0:
                last_x = x_coords[-1]
                color = '#00BFFF' if 'bull' in pattern['name'].lower() else '#FF8C00'

                # Handle both old format (single price) and new format (PRZ zones)
                if 'prz_zones' in d_projected:
                    # New format with PRZ zones
                    for i, zone in enumerate(d_projected['prz_zones'], 1):
                        # Draw zone as a shaded rectangle
                        zone_color = QColor(color)
                        zone_color.setAlpha(50 + i * 20)  # Different alpha for each zone
                        zone_brush = pg.mkBrush(zone_color)

                        # Create a rectangular zone
                        rect = pg.QtWidgets.QGraphicsRectItem(last_x + 2, zone['min'],
                                                             20, zone['max'] - zone['min'])
                        rect.setBrush(zone_brush)
                        rect.setPen(pg.mkPen(color, width=2))
                        self.chart.addItem(rect)

                        # Enhanced labels with pattern source identification
                        pattern_source = zone.get('pattern_source', 'Unknown')
                        # Add ABCD bull/bear prefix to pattern name for display
                        if 'AB=CD_bull_' in pattern_source:
                            simplified_name = 'ABCD Bull ' + pattern_source.replace('AB=CD_bull_', '')
                        elif 'AB=CD_bear_' in pattern_source:
                            simplified_name = 'ABCD Bear ' + pattern_source.replace('AB=CD_bear_', '')
                        else:
                            simplified_name = pattern_source

                        label_text = f"PRZ{i} ({simplified_name})\n{zone['min']:.2f}-{zone['max']:.2f}"
                        text = pg.TextItem(label_text, color=color, anchor=(0, 0.5))
                        # Simple positioning without overlap - back to center alignment
                        text.setPos(last_x + 25, (zone['min'] + zone['max']) / 2)
                        text.setFont(QFont('Arial', 8, QFont.Weight.Bold))
                        self.chart.addItem(text)

                elif 'd_lines' in d_projected:
                    # Enhanced XABCD format with 6-line tolerance system
                    d_lines = d_projected['d_lines']
                    for i, d_price in enumerate(d_lines, 1):
                        # Draw horizontal line for each D projection
                        line_pen = pg.mkPen(color=color, width=1.5, style=Qt.PenStyle.DashLine)
                        self.chart.plot([last_x, last_x + 15], [d_price, d_price], pen=line_pen)

                        # Add label for each line
                        text = pg.TextItem(f"D{i}: {d_price:.2f}", color=color, anchor=(0, 0.5))
                        text.setPos(last_x + 16, d_price)
                        text.setFont(QFont('Arial', 7))
                        self.chart.addItem(text)

                elif 'price' in d_projected:
                    # Old format with single price (backward compatibility)
                    proj_d = d_projected['price']
                    proj_pen = pg.mkPen(color=color, width=2, style=Qt.PenStyle.DashLine)
                    self.chart.plot([last_x, last_x + 10], [proj_d, proj_d], pen=proj_pen)
                    text = pg.TextItem(f"D target: {proj_d:.2f}", color=color)
                    text.setPos(last_x + 5, proj_d)
                    self.chart.addItem(text)

        # Set x-axis labels to show dates
        axis = self.chart.getAxis('bottom')
        date_labels = []
        for i in range(0, len(display_data), max(1, len(display_data)//10)):
            date_labels.append((i, str(display_data.index[i].date())))
        axis.setTicks([date_labels])

        self.chart.autoRange()

    def getIndexForDate(self, date):
        """Get index for date"""
        try:
            return self.data.index.get_loc(date)
        except:
            return np.argmin(np.abs(self.data.index - date))

    def updateDetails(self, pattern):
        """Update pattern details text"""
        # Count total patterns incorporated and show in header with all names
        total_patterns = 0
        pattern_name = pattern['name']
        if 'ratios' in pattern and 'matching_patterns' in pattern['ratios']:
            matching_patterns = pattern['ratios']['matching_patterns']
            total_patterns = len(matching_patterns)
            # Create a clean list of pattern names for display
            clean_names = []
            for p in matching_patterns:
                clean_name = p.replace('AB=CD_bull_', 'Bull ').replace('AB=CD_bear_', 'Bear ')
                clean_names.append(clean_name)
            pattern_names_str = ', '.join(clean_names)
            details = f"Pattern: {total_patterns} Patterns (ABCD {pattern_names_str})\n"
        else:
            # Clean up the single pattern name for display
            if 'AB=CD_bull_' in pattern_name:
                clean_name = 'ABCD Bull ' + pattern_name.replace('AB=CD_bull_', '').replace('_unformed', '')
            elif 'AB=CD_bear_' in pattern_name:
                clean_name = 'ABCD Bear ' + pattern_name.replace('AB=CD_bear_', '').replace('_unformed', '')
            else:
                clean_name = pattern_name
            details = f"Pattern: 1 Pattern ({clean_name})\n"
        details += f"Type: {pattern['type']}\n\n"

        # Show point values
        if 'points' in pattern:
            details += "Point Values:\n"
            points = pattern['points']
            # Determine which points to show based on pattern type
            if 'xabcd' in pattern.get('type', '').lower() or 'strict_xabcd' in pattern.get('type', ''):
                # XABCD patterns have all 5 points
                point_names = ['X', 'A', 'B', 'C', 'D']
            else:
                # ABCD patterns only have 4 points
                point_names = ['A', 'B', 'C', 'D']

            for point_name in point_names:
                if point_name in points and 'price' in points[point_name]:
                    details += f"  {point_name}: {points[point_name]['price']:.2f}\n"
            details += "\n"

        # Show retracement and projection ratios after point values
        if 'ratios' in pattern:
            details += "Retracement & Projection:\n"
            ratios = pattern['ratios']

            # Track which ratio keys have been processed
            processed_keys = set()

            # Handle ABCD patterns (Formed)
            if 'bc' in ratios and isinstance(ratios['bc'], (int, float)):
                details += f"  BC Retracement: {ratios['bc']:.1f}%\n"
                processed_keys.add('bc')
            if 'cd' in ratios and isinstance(ratios['cd'], (int, float)):
                details += f"  CD Projection: {ratios['cd']:.1f}%\n"
                processed_keys.add('cd')

            # Handle XABCD patterns (Formed and Unformed)
            if 'ab_xa' in ratios and isinstance(ratios['ab_xa'], (int, float)):
                details += f"  AB/XA Retracement: {ratios['ab_xa']:.1f}%\n"
                processed_keys.add('ab_xa')
            if 'bc_ab' in ratios and isinstance(ratios['bc_ab'], (int, float)):
                details += f"  BC/AB Retracement: {ratios['bc_ab']:.1f}%\n"
                processed_keys.add('bc_ab')
            if 'cd_bc' in ratios and isinstance(ratios['cd_bc'], (int, float)):
                details += f"  CD/BC Projection: {ratios['cd_bc']:.1f}%\n"
                processed_keys.add('cd_bc')
            if 'ad_xa' in ratios and isinstance(ratios['ad_xa'], (int, float)):
                details += f"  AD/XA Projection: {ratios['ad_xa']:.1f}%\n"
                processed_keys.add('ad_xa')

            # Handle unformed XABCD pattern ranges
            if 'ad_xa_range' in ratios and isinstance(ratios['ad_xa_range'], (list, tuple)):
                ad_range = ratios['ad_xa_range']
                details += f"  AD/XA Range: {ad_range[0]:.1f}% - {ad_range[1]:.1f}%\n"
                processed_keys.add('ad_xa_range')
            if 'cd_bc_range' in ratios and isinstance(ratios['cd_bc_range'], (list, tuple)):
                cd_range = ratios['cd_bc_range']
                details += f"  CD/BC Range: {cd_range[0]:.1f}% - {cd_range[1]:.1f}%\n"
                processed_keys.add('cd_bc_range')

            # Handle BC retracement if it appears with different key name
            if 'bc_retracement' in ratios and isinstance(ratios['bc_retracement'], (int, float)):
                details += f"  BC Retracement: {ratios['bc_retracement']:.1f}%\n"
                processed_keys.add('bc_retracement')

            details += "\n"

        # Show PRZ Zones
        if 'points' in pattern:
            points = pattern['points']
            # Handle D_projected specially
            if 'D_projected' in points:
                d_proj = points['D_projected']
                if 'prz_zones' in d_proj:
                    details += "PRZ Zones:\n"
                    for i, zone in enumerate(d_proj['prz_zones'], 1):
                        pattern_source = zone.get('pattern_source', 'Unknown')
                        # Add ABCD bull/bear prefix for details display
                        if 'AB=CD_bull_' in pattern_source:
                            simplified_name = 'ABCD Bull ' + pattern_source.replace('AB=CD_bull_', '')
                        elif 'AB=CD_bear_' in pattern_source:
                            simplified_name = 'ABCD Bear ' + pattern_source.replace('AB=CD_bear_', '')
                        else:
                            simplified_name = pattern_source
                        details += f"  PRZ{i} ({simplified_name}): {zone['min']:.2f} - {zone['max']:.2f}\n"
                        details += f"    Projection: {zone['proj_min']:.1f}% - {zone['proj_max']:.1f}%\n"
                elif 'd_lines' in d_proj:
                    # Enhanced XABCD with 6-line tolerance system
                    d_lines = d_proj['d_lines']
                    details += f"\nD Projections ({len(d_lines)} lines):\n"
                    for i, d_price in enumerate(d_lines, 1):
                        details += f"  D{i}: {d_price:.2f}\n"
                elif 'price' in d_proj:
                    details += f"  D_projected: {d_proj['price']:.2f}\n"
            details += "\n"


        self.details_text.setText(details)

    def previousPattern(self):
        """Show previous pattern"""
        if self.filtered_patterns:
            new_index = (self.current_index - 1) % len(self.filtered_patterns)
            self.showPattern(new_index)

    def nextPattern(self):
        """Show next pattern"""
        if self.filtered_patterns:
            new_index = (self.current_index + 1) % len(self.filtered_patterns)
            self.showPattern(new_index)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key.Key_Left:
            self.previousPattern()
        elif event.key() == Qt.Key.Key_Right:
            self.nextPattern()
        elif event.key() == Qt.Key.Key_Escape:
            self.close()

    def analyzePatterns(self):
        """Analyze all patterns to categorize them for filtering"""
        self.bull_count = 0
        self.bear_count = 0
        self.pattern_type_counts = {ptype: 0 for ptype in ['1a', '1b', '2', '3', '4', '5', '6a', '6b', '6c', '6d', '6e']}

        for pattern in self.all_patterns:
            # Count bull/bear
            if 'bull' in pattern['name'].lower():
                self.bull_count += 1
            elif 'bear' in pattern['name'].lower():
                self.bear_count += 1

            # Count pattern types (extract number/letter combinations from pattern name)
            pattern_name = pattern['name']
            for ptype in self.pattern_type_counts.keys():
                if ptype in pattern_name:
                    self.pattern_type_counts[ptype] += 1
                    break  # Only count first match to avoid double counting

    def updateFilterCounts(self):
        """Update the filter labels with current counts"""
        self.bull_label.setText(f"({self.bull_count})")
        self.bear_label.setText(f"({self.bear_count})")

        for ptype, count in self.pattern_type_counts.items():
            if ptype in self.pattern_labels:
                self.pattern_labels[ptype].setText(f"({count})")

    def applyFilters(self):
        """Apply current filter settings to patterns"""
        self.filtered_patterns = []

        # Get filter states
        show_bulls = self.bull_checkbox.isChecked()
        show_bears = self.bear_checkbox.isChecked()

        # Get selected pattern types
        selected_pattern_types = []
        for ptype, checkbox in self.pattern_checkboxes.items():
            if checkbox.isChecked():
                selected_pattern_types.append(ptype)

        # Filter patterns
        for pattern in self.all_patterns:
            pattern_name = pattern['name'].lower()

            # Check bull/bear filter
            is_bull = 'bull' in pattern_name
            is_bear = 'bear' in pattern_name

            bull_bear_pass = False
            if show_bulls and is_bull:
                bull_bear_pass = True
            elif show_bears and is_bear:
                bull_bear_pass = True
            elif not is_bull and not is_bear:  # Handle patterns that are neither
                bull_bear_pass = show_bulls or show_bears

            if not bull_bear_pass:
                continue

            # Check pattern type filter
            pattern_type_pass = False
            if not selected_pattern_types:  # If no types selected, show none
                pattern_type_pass = False
            else:
                for ptype in selected_pattern_types:
                    if ptype in pattern['name']:
                        pattern_type_pass = True
                        break

            if pattern_type_pass:
                self.filtered_patterns.append(pattern)

        # Update navigation
        if self.filtered_patterns:
            # Reset to first pattern if current index is out of bounds
            if self.current_index >= len(self.filtered_patterns):
                self.current_index = 0
            self.showPattern(self.current_index)
        else:
            # No patterns match filters
            self.chart.clear()
            self.addPatternCrosshairAfterPlot()
            self.pattern_info.setText("No patterns match current filters")
            self.details_text.setText("Adjust filters to see patterns")

        # Update filter counts for filtered results
        self.updateFilteredCounts()

    def updateFilteredCounts(self):
        """Update displayed counts based on filtered results"""
        bull_filtered = sum(1 for p in self.filtered_patterns if 'bull' in p['name'].lower())
        bear_filtered = sum(1 for p in self.filtered_patterns if 'bear' in p['name'].lower())

        self.bull_label.setText(f"Bulls: {bull_filtered}/{self.bull_count}")
        self.bear_label.setText(f"Bears: {bear_filtered}/{self.bear_count}")

        # Update pattern type counts
        pattern_filtered_counts = {ptype: 0 for ptype in self.pattern_type_counts.keys()}
        for pattern in self.filtered_patterns:
            for ptype in pattern_filtered_counts.keys():
                if ptype in pattern['name']:
                    pattern_filtered_counts[ptype] += 1
                    break

        for ptype, total_count in self.pattern_type_counts.items():
            filtered_count = pattern_filtered_counts[ptype]
            if ptype in self.pattern_labels:
                self.pattern_labels[ptype].setText(f"{ptype}: {filtered_count}/{total_count}")

    def selectAllFilters(self):
        """Select all filter checkboxes"""
        self.bull_checkbox.setChecked(True)
        self.bear_checkbox.setChecked(True)
        for checkbox in self.pattern_checkboxes.values():
            checkbox.setChecked(True)

    def clearAllFilters(self):
        """Clear all filter checkboxes"""
        self.bull_checkbox.setChecked(False)
        self.bear_checkbox.setChecked(False)
        for checkbox in self.pattern_checkboxes.values():
            checkbox.setChecked(False)


class HarmonicPatternDetector(QMainWindow):
    """Main application window for Harmonic Pattern Detection"""

    def __init__(self):
        super().__init__()
        self.data = None
        self.filtered_data = None
        self.extremum_points = []
        self.detected_patterns = {}
        self.selected_point = None  # For manual editing
        self.edit_mode = None  # 'add' or 'remove'

        self.initUI()

        # Auto-load BTC data on startup
        QTimer.singleShot(100, self.autoLoadBTCData)

    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle("Harmonic Pattern Detection System - PyQt6")
        self.setGeometry(100, 100, 1400, 900)

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create menu bar
        self.createMenuBar()

        # Create toolbar
        self.createToolBar()

        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # Make status bar text selectable (must be done after showMessage)
        status_label = self.status_bar.findChild(QLabel)
        if status_label:
            status_label.setTextInteractionFlags(status_label.textInteractionFlags() | 0x00000002)  # TextSelectableByMouse

        # Create main splitter for chart and controls
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Left side - Chart area
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)

        # Main chart with custom date axis
        self.date_axis = DateAxisItem([], orientation='bottom')
        self.main_chart = PlotWidget(title="Price Chart", axisItems={'bottom': self.date_axis})
        self.main_chart.showGrid(x=True, y=True, alpha=0.3)
        self.main_chart.setLabel('left', 'Price')
        self.main_chart.setLabel('bottom', 'Date')

        # Initialize crosshair functionality
        self.setupCrosshair()

        chart_layout.addWidget(self.main_chart)

        splitter.addWidget(chart_widget)

        # Right side - Controls with scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumWidth(450)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        controls_layout.setSpacing(10)  # Add spacing between groups

        # Binance Data Download group (moved to top)
        download_group = QGroupBox("Download Cryptocurrency Data")
        download_layout = QVBoxLayout()

        # Add instruction label
        instruction_label = QLabel("Select from dropdown or type any Binance symbol")
        instruction_label.setStyleSheet("color: gray; font-size: 10px;")
        download_layout.addWidget(instruction_label)

        # Symbol selection
        symbol_layout = QHBoxLayout()
        symbol_layout.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.setEditable(True)
        self.symbol_combo.setToolTip("Select from list or type any Binance symbol (e.g., DOTUSDT, NEARUSDT)")
        self.symbol_combo.setPlaceholderText("Type symbol...")
        # Add popular symbols
        popular_symbols = BinanceDataDownloader.POPULAR_SYMBOLS
        self.symbol_combo.addItems(popular_symbols)
        self.symbol_combo.setCurrentText("BTCUSDT")
        symbol_layout.addWidget(self.symbol_combo)
        download_layout.addLayout(symbol_layout)

        # Timeframe selection
        timeframe_layout = QHBoxLayout()
        timeframe_layout.addWidget(QLabel("Timeframe:"))
        self.timeframe_combo = QComboBox()
        timeframes = list(BinanceDataDownloader.TIMEFRAMES.keys())
        self.timeframe_combo.addItems(timeframes)
        self.timeframe_combo.setCurrentText("1d")
        timeframe_layout.addWidget(self.timeframe_combo)
        download_layout.addLayout(timeframe_layout)

        # Download date range with checkbox for all available data
        download_date_layout = QVBoxLayout()

        # Add checkbox for downloading all available data
        self.download_all_checkbox = QCheckBox("Download ALL available data")
        self.download_all_checkbox.setChecked(True)  # Default to downloading all data
        self.download_all_checkbox.setStyleSheet("QCheckBox { font-weight: bold; color: #2E7D32; }")
        self.download_all_checkbox.stateChanged.connect(self.onDownloadAllToggled)
        download_date_layout.addWidget(self.download_all_checkbox)

        download_date_layout.addWidget(QLabel("Custom Date Range:"))

        download_date_range_layout = QHBoxLayout()
        download_date_range_layout.addWidget(QLabel("From:"))
        self.download_start_date = QDateEdit()
        self.download_start_date.setCalendarPopup(True)
        # Set default to 1 year ago for custom range
        self.download_start_date.setDate(QDate.currentDate().addYears(-1))
        self.download_start_date.setEnabled(False)  # Disabled by default since "Download ALL" is checked
        download_date_range_layout.addWidget(self.download_start_date)

        download_date_range_layout.addWidget(QLabel("To:"))
        self.download_end_date = QDateEdit()
        self.download_end_date.setCalendarPopup(True)
        self.download_end_date.setDate(QDate.currentDate())
        self.download_end_date.setEnabled(False)  # Disabled by default since "Download ALL" is checked
        download_date_range_layout.addWidget(self.download_end_date)

        download_date_layout.addLayout(download_date_range_layout)
        download_layout.addLayout(download_date_layout)

        # Download button
        self.download_btn = QPushButton("Download Data")
        self.download_btn.clicked.connect(self.downloadBinanceData)
        download_layout.addWidget(self.download_btn)

        # Download progress bar
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        download_layout.addWidget(self.download_progress)

        # Download status label
        self.download_status = QLabel("")
        self.download_status.setWordWrap(True)
        download_layout.addWidget(self.download_status)

        download_group.setLayout(download_layout)
        controls_layout.addWidget(download_group)

        # Data loading group (moved below download group)
        data_group = QGroupBox("Data Management")
        data_layout = QVBoxLayout()

        self.load_btn = QPushButton("Load Data")
        self.load_btn.clicked.connect(self.loadData)
        data_layout.addWidget(self.load_btn)

        self.file_label = QLabel("No file loaded")
        data_layout.addWidget(self.file_label)

        # Date range selection
        date_range_layout = QHBoxLayout()
        date_range_layout.addWidget(QLabel("From:"))
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        # Set default start date to March 1, 2025
        self.start_date_edit.setDate(QDate(2025, 3, 1))
        date_range_layout.addWidget(self.start_date_edit)

        date_range_layout.addWidget(QLabel("To:"))
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        date_range_layout.addWidget(self.end_date_edit)

        data_layout.addLayout(date_range_layout)

        self.clip_btn = QPushButton("Clip Data to Range")
        self.clip_btn.clicked.connect(self.clipData)
        self.clip_btn.setEnabled(False)
        data_layout.addWidget(self.clip_btn)

        data_group.setLayout(data_layout)
        controls_layout.addWidget(data_group)

        # Extremum detection group
        extremum_group = QGroupBox("Extremum Detection")
        extremum_layout = QVBoxLayout()

        length_layout = QHBoxLayout()
        length_layout.addWidget(QLabel("Length:"))
        self.length_spinbox = QSpinBox()
        self.length_spinbox.setMinimum(1)
        self.length_spinbox.setMaximum(20)
        self.length_spinbox.setValue(2)
        length_layout.addWidget(self.length_spinbox)
        extremum_layout.addLayout(length_layout)

        self.detect_extremums_btn = QPushButton("Detect Extremums")
        self.detect_extremums_btn.clicked.connect(self.detectExtremums)
        self.detect_extremums_btn.setEnabled(False)
        extremum_layout.addWidget(self.detect_extremums_btn)

        self.manual_edit_checkbox = QCheckBox("Enable Manual Editing")
        self.manual_edit_checkbox.stateChanged.connect(self.toggleManualEdit)
        extremum_layout.addWidget(self.manual_edit_checkbox)

        # Manual editing buttons
        edit_layout = QHBoxLayout()
        self.add_extremum_btn = QPushButton("Add")
        self.add_extremum_btn.setCheckable(True)
        self.add_extremum_btn.clicked.connect(self.toggleAddMode)
        self.add_extremum_btn.setEnabled(False)
        edit_layout.addWidget(self.add_extremum_btn)

        self.remove_extremum_btn = QPushButton("Remove")
        self.remove_extremum_btn.setCheckable(True)
        self.remove_extremum_btn.clicked.connect(self.toggleRemoveMode)
        self.remove_extremum_btn.setEnabled(False)
        edit_layout.addWidget(self.remove_extremum_btn)

        self.clear_extremums_btn = QPushButton("Clear All")
        self.clear_extremums_btn.clicked.connect(self.clearAllExtremums)
        self.clear_extremums_btn.setEnabled(False)
        edit_layout.addWidget(self.clear_extremums_btn)

        extremum_layout.addLayout(edit_layout)

        # Save/Load buttons
        button_layout = QHBoxLayout()
        self.save_extremums_btn = QPushButton("Save")
        self.save_extremums_btn.clicked.connect(self.saveExtremums)
        button_layout.addWidget(self.save_extremums_btn)

        self.load_extremums_btn = QPushButton("Load")
        self.load_extremums_btn.clicked.connect(self.loadExtremums)
        button_layout.addWidget(self.load_extremums_btn)

        extremum_layout.addLayout(button_layout)

        extremum_group.setLayout(extremum_layout)
        controls_layout.addWidget(extremum_group)

        # Pattern detection group
        pattern_group = QGroupBox("Pattern Detection")
        pattern_layout = QVBoxLayout()

        # Removed basic formed patterns - only keeping strict and unstrict

        # Removed unstrict ABCD and XABCD patterns as requested

        self.strict_abcd_checkbox = QCheckBox("Formed ABCD")
        self.strict_abcd_checkbox.setToolTip("Detect ABCD patterns with strict price containment validation")
        pattern_layout.addWidget(self.strict_abcd_checkbox)

        self.strict_xabcd_checkbox = QCheckBox("Formed XABCD")
        self.strict_xabcd_checkbox.setToolTip("Detect XABCD patterns with strict price containment validation")
        pattern_layout.addWidget(self.strict_xabcd_checkbox)

        self.comprehensive_abcd_checkbox = QCheckBox("Unformed ABCD")
        self.comprehensive_abcd_checkbox.setToolTip("Detect unformed ABCD patterns with strict price containment validation and optimized algorithms")
        pattern_layout.addWidget(self.comprehensive_abcd_checkbox)

        self.comprehensive_xabcd_checkbox = QCheckBox("Unformed XABCD")
        self.comprehensive_xabcd_checkbox.setToolTip("Detect unformed XABCD patterns with strict price containment validation and horizontal D lines")
        pattern_layout.addWidget(self.comprehensive_xabcd_checkbox)

        # Add separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        pattern_layout.addWidget(separator)

        # Removed Show All Patterns checkbox - patterns now open in PatternViewerWindow by default

        self.detect_patterns_btn = QPushButton("Detect Patterns")
        self.detect_patterns_btn.clicked.connect(self.detectPatterns)
        self.detect_patterns_btn.setEnabled(False)
        pattern_layout.addWidget(self.detect_patterns_btn)

        # Add Backtesting button
        self.backtest_btn = QPushButton("Run Backtesting")
        self.backtest_btn.clicked.connect(self.openBacktestDialog)
        self.backtest_btn.setEnabled(False)
        self.backtest_btn.setToolTip("Run backtesting simulation on detected patterns")
        pattern_layout.addWidget(self.backtest_btn)

        # Progress bar for pattern detection
        self.progress_bar = QProgressBar()
        pattern_layout.addWidget(self.progress_bar)

        pattern_group.setLayout(pattern_layout)
        controls_layout.addWidget(pattern_group)

        # Statistics display
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout()

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMaximumHeight(150)
        stats_layout.addWidget(self.stats_text)

        stats_group.setLayout(stats_layout)
        controls_layout.addWidget(stats_group)


        controls_layout.addStretch()

        # Set the controls widget as the scroll area's widget
        scroll_area.setWidget(controls_widget)
        splitter.addWidget(scroll_area)

        # Set splitter proportions (70% chart, 30% controls)
        splitter.setSizes([980, 450])

        # Initialize keyboard shortcuts
        self.setupKeyboardShortcuts()

    def createMenuBar(self):
        """Create menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu('File')

        load_action = QAction('Load Data', self)
        load_action.setShortcut('Ctrl+O')
        load_action.triggered.connect(self.loadData)
        file_menu.addAction(load_action)

        save_patterns_action = QAction('Save Patterns', self)
        save_patterns_action.setShortcut('Ctrl+S')
        save_patterns_action.triggered.connect(self.savePatterns)
        file_menu.addAction(save_patterns_action)

        file_menu.addSeparator()

        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu('View')

        reset_view_action = QAction('Reset View', self)
        reset_view_action.setShortcut('R')
        reset_view_action.triggered.connect(self.resetView)
        view_menu.addAction(reset_view_action)

        # Help menu
        help_menu = menubar.addMenu('Help')

        about_action = QAction('About', self)
        about_action.triggered.connect(self.showAbout)
        help_menu.addAction(about_action)

    def createToolBar(self):
        """Create toolbar"""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        toolbar.addAction('Load', self.loadData)
        toolbar.addAction('Clip', self.clipData)
        toolbar.addSeparator()
        toolbar.addAction('Detect Extremums', self.detectExtremums)
        toolbar.addAction('Detect Patterns', self.detectPatterns)
        toolbar.addSeparator()
        toolbar.addAction('Reset View', self.resetView)

    def setupKeyboardShortcuts(self):
        """Setup keyboard shortcuts"""
        # Arrow keys for pattern navigation
        QKeySequence("Left")
        QKeySequence("Right")

    def autoLoadBTCData(self):
        """Auto-load BTC data file on startup"""
        try:
            # Check if btcusdt_1d.csv exists
            import os
            btc_file = os.path.join(os.path.dirname(__file__), 'btcusdt_1d.csv')

            if os.path.exists(btc_file):
                # Load and standardize the data
                raw_data = pd.read_csv(btc_file)
                self.data = self.standardizeDataFormat(raw_data)

                # Update UI
                self.file_label.setText(f"File: btcusdt_1d.csv")
                self.status_bar.showMessage(f"Auto-loaded BTC data: {len(self.data)} rows")

                # Update chart title for default data
                self.main_chart.setTitle("BTCUSDT - Daily Candlestick Chart")

                # Update date range
                # Set start date to March 1, 2025 (or data start if later)
                data_start = self.data.index[0]
                march_2025 = pd.Timestamp('2025-03-01')

                if data_start <= march_2025 and self.data.index[-1] >= march_2025:
                    # If data contains March 1, 2025, use it as start
                    self.start_date_edit.setDate(QDate(2025, 3, 1))
                else:
                    # Otherwise use data's actual start date
                    self.start_date_edit.setDate(QDate(data_start.year, data_start.month, data_start.day))

                end_date = self.data.index[-1]
                self.end_date_edit.setDate(QDate(end_date.year, end_date.month, end_date.day))

                # Enable buttons
                self.clip_btn.setEnabled(True)
                self.detect_extremums_btn.setEnabled(True)
                self.backtest_btn.setEnabled(True)  # Enable backtesting immediately after data loads

                # Auto-clip to date range
                QTimer.singleShot(200, self.clipData)

        except Exception as e:
            if DEBUG_MODE: print(f"Could not auto-load BTC data: {str(e)}")
            # Silent fail - user can manually load data if needed

    def standardizeDataFormat(self, data):
        """
        Standardize data format: handle date columns, timezone, column names, and sorting.
        This method eliminates code duplication across loading methods.
        """
        if data is None or data.empty:
            raise ValueError("Data is None or empty")

        # Handle different possible column names for the date/time column
        date_columns = ['time', 'Date', 'date', 'timestamp', 'datetime']
        date_col_found = None

        for col in date_columns:
            if col in data.columns:
                date_col_found = col
                break

        if date_col_found:
            data[date_col_found] = pd.to_datetime(data[date_col_found])
            data.set_index(date_col_found, inplace=True)
        else:
            # If no recognized date column found, try to use the first column as date
            first_col = data.columns[0]
            try:
                data[first_col] = pd.to_datetime(data[first_col])
                data.set_index(first_col, inplace=True)
            except Exception:
                raise ValueError(f"Could not convert '{first_col}' to datetime format")

        # Remove timezone information to avoid comparison issues
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)

        # Standardize column names to expected format (handle case variations)
        column_mapping = {}
        for col in data.columns:
            col_lower = col.lower()
            if col_lower == 'open':
                column_mapping[col] = 'Open'
            elif col_lower == 'high':
                column_mapping[col] = 'High'
            elif col_lower == 'low':
                column_mapping[col] = 'Low'
            elif col_lower == 'close':
                column_mapping[col] = 'Close'
            elif col_lower == 'volume':
                column_mapping[col] = 'Volume'

        data.rename(columns=column_mapping, inplace=True)

        # Ensure all required columns exist
        required_cols = ['Open', 'High', 'Low', 'Close']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")

        # Ensure data is sorted by date
        data = data.sort_index()

        # Validate data types
        for col in required_cols:
            data[col] = pd.to_numeric(data[col], errors='coerce')

        # Remove any rows with NaN values in OHLC columns
        data = data.dropna(subset=required_cols)

        if data.empty:
            raise ValueError("No valid data rows after cleaning")

        return data

    def setupCrosshair(self):
        """Setup crosshair functionality for the chart"""
        # Set up mouse tracking with reduced update frequency to prevent screen flicker
        self.proxy = pg.SignalProxy(self.main_chart.scene().sigMouseMoved, rateLimit=15, slot=self.mouseMoved)
        self.main_chart.setMouseTracking(True)

        # Track last position to avoid unnecessary updates
        self.last_mouse_pos = None
        self.label_update_counter = 0

    def mouseMoved(self, evt):
        """Handle mouse movement for crosshair updates"""
        if not hasattr(self, 'vLine') or not hasattr(self, 'hLine'):
            return  # Crosshair not yet created

        pos = evt[0]  # SignalProxy provides position in a list

        # Check if position actually changed to avoid unnecessary updates
        if self.last_mouse_pos is not None and abs(pos.x() - self.last_mouse_pos.x()) < 2 and abs(pos.y() - self.last_mouse_pos.y()) < 2:
            return  # Position hasn't changed significantly

        self.last_mouse_pos = pos

        if self.main_chart.sceneBoundingRect().contains(pos):
            # Show crosshair elements only if not already visible
            if not self.vLine.isVisible():
                self.vLine.setVisible(True)
                self.hLine.setVisible(True)
                self.x_axis_label.setVisible(True)
                self.y_axis_label.setVisible(True)
                self.crosshair_label.setVisible(True)

            mousePoint = self.main_chart.plotItem.vb.mapSceneToView(pos)
            x, y = mousePoint.x(), mousePoint.y()

            # Update crosshair position efficiently
            self.vLine.setPos(x)
            self.hLine.setPos(y)

            # Update axis labels less frequently to reduce screen refresh
            self.label_update_counter += 1
            if self.label_update_counter % 3 == 0:  # Update labels every 3rd mouse move
                self.updateAxisLabels(x, y)
                self.updateCrosshairLabel(x, y)
        else:
            # Hide crosshair when mouse is outside chart area
            if self.vLine.isVisible():
                self.vLine.setVisible(False)
                self.hLine.setVisible(False)
                self.x_axis_label.setVisible(False)
                self.y_axis_label.setVisible(False)
                self.crosshair_label.setVisible(False)


    def updateCrosshairLabel(self, x, y):
        """Update crosshair label with current price and date"""
        try:
            # Get current data
            data_to_use = self.filtered_data if self.filtered_data is not None else self.data
            if data_to_use is None or len(data_to_use) == 0:
                return

            # Convert x position to integer index
            x_int = int(round(x))

            # Ensure x is within data bounds
            if 0 <= x_int < len(data_to_use):
                # Get date and OHLC data for this index
                date = data_to_use.index[x_int]
                row = data_to_use.iloc[x_int]

                # Format date - handle different date types
                if hasattr(date, 'strftime'):
                    date_str = date.strftime('%Y-%m-%d %H:%M')
                else:
                    date_str = str(date)[:16]

                # Format price information
                open_price = float(row['Open'])
                high_price = float(row['High'])
                low_price = float(row['Low'])
                close_price = float(row['Close'])

                # Create label text with better formatting
                label_text = f"Time: {date_str}\n"
                label_text += f"Open:  ${open_price:,.2f}\n"
                label_text += f"High:  ${high_price:,.2f}\n"
                label_text += f"Low:   ${low_price:,.2f}\n"
                label_text += f"Close: ${close_price:,.2f}\n"
                label_text += f"Price: ${y:,.2f}"

                # Position label at top-left of visible chart area
                view_box = self.main_chart.plotItem.vb
                view_range = view_box.viewRange()

                # Calculate position with padding from edges
                x_range = view_range[0][1] - view_range[0][0]
                y_range = view_range[1][1] - view_range[1][0]

                label_x = view_range[0][0] + x_range * 0.02  # 2% from left edge
                label_y = view_range[1][1] - y_range * 0.05  # 5% from top edge

                # Update label
                self.crosshair_label.setText(label_text)
                self.crosshair_label.setPos(label_x, label_y)

                # Force label to be visible and on top
                self.crosshair_label.setVisible(True)
                self.crosshair_label.setZValue(1000)  # Bring to front

        except Exception as e:
            # Debug: print error to see what's happening
            print(f"Crosshair label error: {str(e)}")
            # Fallback: show simple text
            try:
                self.crosshair_label.setText(f"Price: ${y:,.2f}")
                self.crosshair_label.setPos(x + 5, y)
                self.crosshair_label.setVisible(True)
            except:
                pass

    def updateAxisLabels(self, x, y):
        """Update TradingView-style axis labels"""
        try:
            # Get current data for date formatting
            data_to_use = self.filtered_data if self.filtered_data is not None else self.data
            if data_to_use is None or len(data_to_use) == 0:
                return

            # Get view range for positioning
            view_box = self.main_chart.plotItem.vb
            view_range = view_box.viewRange()

            # Format and position X-axis (time) label
            x_int = int(round(x))
            if 0 <= x_int < len(data_to_use):
                date = data_to_use.index[x_int]
                if hasattr(date, 'strftime'):
                    time_str = date.strftime('%Y-%m-%d %H:%M')
                else:
                    time_str = str(date)[:16]

                # Position near bottom of chart area, visible inside the chart
                x_label_y = view_range[1][0] + (view_range[1][1] - view_range[1][0]) * 0.05
                self.x_axis_label.setText(time_str)
                self.x_axis_label.setPos(x, x_label_y)

            # Format and position Y-axis (price) label
            price_str = f"${y:,.2f}"

            # Position at left edge of chart, centered on crosshair
            y_label_x = view_range[0][0] + (view_range[0][1] - view_range[0][0]) * 0.02
            self.y_axis_label.setText(price_str)
            self.y_axis_label.setPos(y_label_x, y)

        except Exception as e:
            print(f"Axis labels error: {str(e)}")

    def addCrosshairAfterPlot(self, data):
        """Add crosshair elements after chart is plotted"""
        if data is None or len(data) == 0:
            return

        # Re-create and add crosshair lines (they get cleared with chart.clear())
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('cyan', width=2, style=Qt.PenStyle.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('cyan', width=2, style=Qt.PenStyle.DashLine))

        self.main_chart.addItem(self.vLine, ignoreBounds=True)
        self.main_chart.addItem(self.hLine, ignoreBounds=True)

        # Create TradingView-style axis labels
        # X-axis (time) label
        self.x_axis_label = pg.TextItem('', anchor=(0.5, 0), color='white',
                                      fill=pg.mkBrush(0, 100, 255, 220),
                                      border=pg.mkPen('white', width=2))
        self.x_axis_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        self.x_axis_label.setZValue(1000)  # Ensure it's on top
        self.main_chart.addItem(self.x_axis_label)

        # Y-axis (price) label
        self.y_axis_label = pg.TextItem('', anchor=(0, 0.5), color='white',
                                      fill=pg.mkBrush(0, 100, 255, 220),
                                      border=pg.mkPen('white', width=2))
        self.y_axis_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        self.y_axis_label.setZValue(1000)  # Ensure it's on top
        self.main_chart.addItem(self.y_axis_label)

        # Create comprehensive OHLC data label
        self.crosshair_label = pg.TextItem('', anchor=(0, 0), color='white',
                                         fill=pg.mkBrush(0, 0, 0, 150),
                                         border=pg.mkPen('cyan', width=1))
        self.crosshair_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        self.crosshair_label.setZValue(1001)  # On top of other elements
        self.main_chart.addItem(self.crosshair_label)

        # Initially hide crosshair (will show when mouse moves)
        self.vLine.setVisible(False)
        self.hLine.setVisible(False)
        self.x_axis_label.setVisible(False)
        self.y_axis_label.setVisible(False)
        self.crosshair_label.setVisible(False)

        # Ensure mouse tracking is enabled
        self.main_chart.setMouseTracking(True)

    def loadData(self):
        """Load CSV data file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            try:
                # Load and standardize the data
                raw_data = pd.read_csv(file_path)
                self.data = self.standardizeDataFormat(raw_data)

                # Update UI
                filename = file_path.split('/')[-1] if '/' in file_path else file_path.split('\\')[-1]
                self.file_label.setText(f"File: {filename}")
                self.status_bar.showMessage(f"Loaded {len(self.data)} rows")

                # Update chart title with filename
                symbol_name = filename.replace('.csv', '').upper()
                self.main_chart.setTitle(f"{symbol_name} - Candlestick Chart")

                # Update date range
                # Set start date to March 1, 2025 (or data start if later)
                data_start = self.data.index[0]
                march_2025 = pd.Timestamp('2025-03-01')

                if data_start <= march_2025 and self.data.index[-1] >= march_2025:
                    # If data contains March 1, 2025, use it as start
                    self.start_date_edit.setDate(QDate(2025, 3, 1))
                else:
                    # Otherwise use data's actual start date
                    self.start_date_edit.setDate(QDate(data_start.year, data_start.month, data_start.day))

                end_date = self.data.index[-1]
                self.end_date_edit.setDate(QDate(end_date.year, end_date.month, end_date.day))

                # Clear any existing filtered data
                self.filtered_data = None

                # Clear existing patterns and extremums
                self.extremum_points = []
                self.detected_patterns = {}

                # Enable buttons
                self.clip_btn.setEnabled(True)
                self.detect_extremums_btn.setEnabled(True)
                self.backtest_btn.setEnabled(True)  # Enable backtesting after loading data

                # Plot initial data
                self.plotData()

                # Update statistics
                self.updateStatistics()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")

    def onDownloadAllToggled(self):
        """Handle the download all checkbox toggle"""
        if self.download_all_checkbox.isChecked():
            # Disable date fields when downloading all data
            self.download_start_date.setEnabled(False)
            self.download_end_date.setEnabled(False)
        else:
            # Enable date fields for custom range
            self.download_start_date.setEnabled(True)
            self.download_end_date.setEnabled(True)

    def downloadBinanceData(self):
        """Download data from Binance API"""
        try:
            # Get parameters
            symbol = self.symbol_combo.currentText().strip().upper()
            timeframe = self.timeframe_combo.currentText()

            # Check if downloading all available data
            if self.download_all_checkbox.isChecked():
                # Use earliest possible date (Binance launch) to current date
                start_date = datetime(2017, 7, 1)  # Binance launch date
                end_date = datetime.now()
            else:
                # Use custom date range
                start_date = self.download_start_date.date().toPyDate()
                end_date = self.download_end_date.date().toPyDate()
                # Convert to datetime
                start_date = datetime.combine(start_date, datetime.min.time())
                end_date = datetime.combine(end_date, datetime.max.time())

            # Validate dates
            if start_date >= end_date:
                QMessageBox.warning(self, "Warning", "Start date must be before end date")
                return

            # Disable button and show progress
            self.download_btn.setEnabled(False)
            self.download_progress.setVisible(True)
            self.download_progress.setValue(0)
            self.download_status.setText(f"Downloading {symbol} data...")

            # Create downloader
            downloader = BinanceDataDownloader()

            # Define progress callback
            def update_progress(percent, message):
                self.download_progress.setValue(percent)
                self.download_status.setText(message)
                QApplication.processEvents()  # Update UI

            # Download data
            df = downloader.download_data(
                symbol=symbol,
                interval=timeframe,
                start_date=start_date,
                end_date=end_date,
                progress_callback=update_progress
            )

            # Save to CSV
            filename = f"{symbol.lower()}_{timeframe}.csv"
            downloader.save_to_csv(df, filename)

            # Load and standardize the downloaded data
            self.data = self.standardizeDataFormat(df.copy())

            # Update UI
            self.file_label.setText(f"Data: {symbol} {timeframe}")
            self.status_bar.showMessage(f"Downloaded {len(self.data)} candles for {symbol}")

            # Update chart title
            self.main_chart.setTitle(f"{symbol} - {timeframe.upper()} Candlestick Chart")

            # Update date range controls
            self.start_date_edit.setDate(QDate(self.data.index[0].year,
                                              self.data.index[0].month,
                                              self.data.index[0].day))
            self.end_date_edit.setDate(QDate(self.data.index[-1].year,
                                            self.data.index[-1].month,
                                            self.data.index[-1].day))

            # Enable controls
            self.clip_btn.setEnabled(True)
            self.detect_extremums_btn.setEnabled(True)
            self.backtest_btn.setEnabled(True)  # Enable backtesting after downloading data

            # Clear existing patterns and extremums
            self.extremum_points = []
            self.detected_patterns = {}

            # Plot initial data
            self.plotData()

            # Update statistics
            self.updateStatistics()

            # Success message
            self.download_status.setText(f"Successfully downloaded {len(df)} candles and saved to {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to download data: {str(e)}")
            self.download_status.setText(f"Error: {str(e)}")

        finally:
            # Re-enable button and hide progress after a delay
            self.download_btn.setEnabled(True)
            QTimer.singleShot(3000, lambda: self.download_progress.setVisible(False))

    def clipData(self):
        """Clip data to selected date range"""
        if self.data is None:
            return

        start_date = self.start_date_edit.date().toPyDate()
        end_date = self.end_date_edit.date().toPyDate()

        # Convert to pandas datetime
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        # Filter data
        self.filtered_data = self.data.loc[start_date:end_date].copy()

        if len(self.filtered_data) == 0:
            QMessageBox.warning(self, "Warning", "No data in selected range")
            return

        self.status_bar.showMessage(
            f"Data clipped: {len(self.data)} -> {len(self.filtered_data)} rows"
        )

        # Re-plot with filtered data
        self.plotData()
        self.updateStatistics()

    def plotData(self):
        """Plot candlestick chart"""
        self.main_chart.clear()

        data_to_plot = self.filtered_data if self.filtered_data is not None else self.data

        if data_to_plot is None or len(data_to_plot) == 0:
            return

        # Update date axis with current data dates
        self.date_axis.dates = data_to_plot.index

        # Create candlestick item
        candles = CandlestickItem(data_to_plot)
        self.main_chart.addItem(candles)

        # Set proper view range to prevent artifacts
        self.main_chart.setXRange(0, len(data_to_plot) - 1, padding=0.02)

        # Re-add crosshair after clearing chart
        self.addCrosshairAfterPlot(data_to_plot)

        # Calculate y range with some padding
        y_min = data_to_plot['Low'].min()
        y_max = data_to_plot['High'].max()
        y_padding = (y_max - y_min) * 0.1
        self.main_chart.setYRange(y_min - y_padding, y_max + y_padding, padding=0)

        # Enable auto-range for zoom functionality
        self.main_chart.getViewBox().enableAutoRange(enable=False)

        # Force update the view
        self.main_chart.getViewBox().updateAutoRange()

        # Process events to ensure immediate update
        QApplication.processEvents()

    def detectExtremums(self):
        """Detect extremum points"""
        if self.filtered_data is None and self.data is None:
            return

        data = self.filtered_data if self.filtered_data is not None else self.data
        length = self.length_spinbox.value()

        # OPTIMIZED pivot detection using vectorized operations
        self.extremum_points = []

        # Convert to numpy arrays for vectorized operations (10x faster)
        highs = data['High'].values
        lows = data['Low'].values
        timestamps = data.index.values
        n = len(data)

        # Vectorized pivot detection - O(n) instead of O(n²)
        for i in range(length, n - length):
            # Use numpy operations for window comparisons
            left_window = slice(i-length, i)
            right_window = slice(i+1, i+length+1)

            # Check for high pivot
            is_high_pivot = (
                highs[i] >= np.max(highs[left_window]) and
                highs[i] >= np.max(highs[right_window]) and
                highs[i] >= highs[i-1] and highs[i] >= highs[i+1]
            )

            # Check for low pivot
            is_low_pivot = (
                lows[i] <= np.min(lows[left_window]) and
                lows[i] <= np.min(lows[right_window]) and
                lows[i] <= lows[i-1] and lows[i] <= lows[i+1]
            )

            # Add BOTH high and low pivots if they exist
            # This ensures we capture ALL extremum points (not just alternating ones)
            if is_high_pivot:
                self.extremum_points.append((timestamps[i], highs[i], True))

            # Use separate if (not elif) to capture both high and low on same candle
            if is_low_pivot:
                self.extremum_points.append((timestamps[i], lows[i], False))

        # Sort by date
        self.extremum_points.sort(key=lambda x: x[0])

        # Count highs and lows separately for detailed reporting
        high_count = sum(1 for _, _, is_high in self.extremum_points if is_high)
        low_count = len(self.extremum_points) - high_count

        # Log detailed counts
        print(f"Extremum detection complete:")
        print(f"  - High points: {high_count}")
        print(f"  - Low points: {low_count}")
        print(f"  - Total: {len(self.extremum_points)} points (ALL highs and lows)")

        self.status_bar.showMessage(f"Found {len(self.extremum_points)} extremum points ({high_count} highs, {low_count} lows)")

        # Plot extremums
        self.plotExtremums()

        # Enable pattern detection
        self.detect_patterns_btn.setEnabled(True)
        self.backtest_btn.setEnabled(True)

        # Update statistics
        self.updateStatistics()

    def cleanupExtremums(self, extremums):
        """
        Clean up extremum points to ensure alternating high/low pattern.
        When consecutive highs or lows are found, keep the most extreme one.
        """
        if len(extremums) <= 1:
            return extremums

        cleaned = []
        i = 0

        while i < len(extremums):
            current = extremums[i]
            cleaned.append(current)

            # Look ahead for consecutive points of the same type
            j = i + 1
            while j < len(extremums) and extremums[j][2] == current[2]:
                # Same type (both highs or both lows)
                if current[2]:  # Both are highs
                    # Keep the higher high
                    if extremums[j][1] > current[1]:
                        cleaned[-1] = extremums[j]  # Replace with higher high
                        current = extremums[j]
                else:  # Both are lows
                    # Keep the lower low
                    if extremums[j][1] < current[1]:
                        cleaned[-1] = extremums[j]  # Replace with lower low
                        current = extremums[j]
                j += 1

            i = j  # Skip the consecutive points we just processed

        return cleaned

    def plotExtremums(self):
        """Plot extremum points on chart"""
        # Remove existing extremum plots
        for item in self.main_chart.listDataItems():
            if isinstance(item, pg.ScatterPlotItem):
                self.main_chart.removeItem(item)

        if not self.extremum_points:
            return

        data = self.filtered_data if self.filtered_data is not None else self.data

        # Separate highs and lows
        highs = [(i, ep[1]) for i, ep in enumerate(self.extremum_points) if ep[2]]
        lows = [(i, ep[1]) for i, ep in enumerate(self.extremum_points) if not ep[2]]

        # Plot highs
        if highs:
            high_x = [self.getIndexForDate(self.extremum_points[h[0]][0], data) for h in highs]
            high_y = [h[1] for h in highs]
            high_scatter = pg.ScatterPlotItem(
                x=high_x, y=high_y,
                pen=pg.mkPen('#00BFFF', width=2),
                brush=pg.mkBrush('#00BFFF'),
                size=10,
                symbol='t'
            )
            self.main_chart.addItem(high_scatter)

        # Plot lows
        if lows:
            low_x = [self.getIndexForDate(self.extremum_points[l[0]][0], data) for l in lows]
            low_y = [l[1] for l in lows]
            low_scatter = pg.ScatterPlotItem(
                x=low_x, y=low_y,
                pen=pg.mkPen('#FF8C00', width=2),
                brush=pg.mkBrush('#FF8C00'),
                size=10,
                symbol='t1'
            )
            self.main_chart.addItem(low_scatter)

    def getIndexForDate(self, date, data):
        """Get index position for a given date"""
        try:
            return data.index.get_loc(date)
        except:
            # Find nearest date
            return np.argmin(np.abs(data.index - date))

    def toggleManualEdit(self, state):
        """Toggle manual extremum editing"""
        enabled = state == Qt.CheckState.Checked.value

        # Enable/disable manual editing buttons
        self.add_extremum_btn.setEnabled(enabled)
        self.remove_extremum_btn.setEnabled(enabled)
        self.clear_extremums_btn.setEnabled(enabled)

        if enabled:
            self.main_chart.scene().sigMouseClicked.connect(self.onChartClick)
            self.status_bar.showMessage("Manual edit enabled: Select Add/Remove mode then click on chart")
        else:
            try:
                self.main_chart.scene().sigMouseClicked.disconnect(self.onChartClick)
            except:
                pass
            self.edit_mode = None
            self.add_extremum_btn.setChecked(False)
            self.remove_extremum_btn.setChecked(False)
            self.selected_point = None
            self.plotExtremums()
            self.status_bar.showMessage("Manual edit disabled")

    def onChartClick(self, event):
        """Handle chart clicks for manual extremum editing"""
        if not self.manual_edit_checkbox.isChecked() or self.edit_mode is None:
            return

        # Get click position
        pos = event.scenePos()
        vb = self.main_chart.plotItem.vb
        mouse_point = vb.mapSceneToView(pos)

        if self.edit_mode == 'add':
            self.addManualExtremum(mouse_point)
        elif self.edit_mode == 'remove':
            self.removeNearestExtremum(mouse_point)

    def addManualExtremum(self, point):
        """Add manual extremum at clicked point"""
        if self.filtered_data is None and self.data is None:
            return

        data = self.filtered_data if self.filtered_data is not None else self.data

        # Find nearest candlestick
        x_index = int(round(point.x()))
        if x_index < 0 or x_index >= len(data):
            return

        # Get the date and candlestick data
        date = data.index[x_index]
        candle = data.iloc[x_index]

        # Determine if click is closer to high or low
        high_dist = abs(point.y() - candle['High'])
        low_dist = abs(point.y() - candle['Low'])

        if high_dist < low_dist:
            # Add as high
            price = candle['High']
            is_high = True
            self.status_bar.showMessage(f"Added HIGH at {date.strftime('%Y-%m-%d')}: {price:.2f}")
        else:
            # Add as low
            price = candle['Low']
            is_high = False
            self.status_bar.showMessage(f"Added LOW at {date.strftime('%Y-%m-%d')}: {price:.2f}")

        # Check if extremum already exists at this date
        for ep in self.extremum_points:
            if ep[0] == date:
                self.extremum_points.remove(ep)
                break

        # Add new extremum
        self.extremum_points.append((date, price, is_high))
        self.extremum_points.sort(key=lambda x: x[0])

        # Update display
        self.plotExtremums()
        self.updateStatistics()

    def removeNearestExtremum(self, point):
        """Remove extremum nearest to clicked point"""
        if not self.extremum_points:
            self.status_bar.showMessage("No extremum points to remove")
            return

        data = self.filtered_data if self.filtered_data is not None else self.data
        if data is None:
            return

        # Find nearest extremum
        min_dist = float('inf')
        nearest_ep = None

        # Click position in chart coordinates
        click_x = point.x()  # This is the index
        click_y = point.y()  # This is the price

        print(f"Remove click at: x={click_x:.2f}, y={click_y:.2f}")

        for ep in self.extremum_points:
            # Get index for the extremum date
            try:
                ep_index = data.index.get_loc(ep[0])
            except:
                # If exact date not found, find nearest
                distances = np.abs(data.index - ep[0])
                ep_index = np.argmin(distances)
                if distances[ep_index] > pd.Timedelta(days=1):
                    continue  # Skip if date is too far off

            # Calculate distance in chart coordinates
            x_dist = abs(ep_index - click_x)
            y_dist = abs(ep[1] - click_y)

            # Scale the distances appropriately
            # Since we're clicking on visual points, we need to consider the visual scale
            # X axis spans the number of data points, Y axis spans the price range
            y_range = data['High'].max() - data['Low'].min()
            if y_range > 0:
                # Normalize y distance to be comparable to x distance
                # A typical click tolerance might be ~3 candlesticks horizontally
                # and a similar visual distance vertically
                normalized_y_dist = y_dist / y_range * len(data)
                dist = (x_dist ** 2 + normalized_y_dist ** 2) ** 0.5
            else:
                dist = x_dist

            date_str = str(ep[0])[:10] if hasattr(ep[0], 'strftime') else str(ep[0])[:10]
            print(f"  Extremum at index {ep_index} ({date_str}), price={ep[1]:.2f}: dist={dist:.2f} (x_dist={x_dist:.2f}, y_dist={y_dist:.2f})")

            if dist < min_dist:
                min_dist = dist
                nearest_ep = ep

        # Remove if within reasonable distance
        # Threshold of 3 means roughly 3 candlesticks distance
        threshold = 3.0
        print(f"Nearest extremum distance: {min_dist:.2f}, threshold: {threshold}")

        if nearest_ep and min_dist < threshold:
            self.extremum_points.remove(nearest_ep)
            self.plotExtremums()
            self.updateStatistics()
            date_str = str(nearest_ep[0])[:10]
            self.status_bar.showMessage(f"Removed {'HIGH' if nearest_ep[2] else 'LOW'} at {date_str}: {nearest_ep[1]:.2f}")
            print(f"Removed extremum at {date_str}")
        else:
            self.status_bar.showMessage("No extremum point found near click location (click closer to a point)")
            if DEBUG_MODE: print("No extremum within threshold distance")

    def detectPatterns(self):
        """Detect harmonic patterns"""
        if DEBUG_MODE: print("detectPatterns called")

        # Show immediate feedback
        self.status_bar.showMessage("Starting pattern detection...")
        QApplication.processEvents()  # Force UI update

        if not self.extremum_points:
            QMessageBox.warning(self, "Warning", "Please detect extremums first")
            return

        if len(self.extremum_points) < 4:
            QMessageBox.warning(self, "Warning", "Need at least 4 extremum points to detect patterns")
            return

        if DEBUG_MODE: print(f"Have {len(self.extremum_points)} extremum points")

        # Get selected pattern types
        pattern_types = []
        # Strict and comprehensive patterns (removed only unstrict patterns)
        if hasattr(self, 'strict_abcd_checkbox') and self.strict_abcd_checkbox.isChecked():
            pattern_types.append('strict_abcd')
        if hasattr(self, 'strict_xabcd_checkbox') and self.strict_xabcd_checkbox.isChecked():
            pattern_types.append('strict_xabcd')
        if hasattr(self, 'comprehensive_abcd_checkbox') and self.comprehensive_abcd_checkbox.isChecked():
            pattern_types.append('comprehensive_abcd')
        if hasattr(self, 'comprehensive_xabcd_checkbox') and self.comprehensive_xabcd_checkbox.isChecked():
            pattern_types.append('comprehensive_xabcd')

        # If no individual patterns are selected, automatically enable all pattern types
        if not pattern_types:
            pattern_types = ['strict_abcd', 'strict_xabcd', 'comprehensive_abcd', 'comprehensive_xabcd']
            if DEBUG_MODE: print("No patterns selected - detecting all pattern types")

        if DEBUG_MODE: print(f"Selected pattern types: {pattern_types}")

        if not pattern_types:
            QMessageBox.warning(self, "Warning", "Please select at least one pattern type")
            return

        # Clean up any existing worker thread
        if hasattr(self, 'pattern_worker') and self.pattern_worker is not None and self.pattern_worker.isRunning():
            self.pattern_worker.quit()
            self.pattern_worker.wait()

        # Create and start worker thread
        if DEBUG_MODE: print("Creating pattern worker thread...")
        # Pass the data (filtered or original) to the worker
        data_to_use = self.filtered_data if self.filtered_data is not None else self.data
        self.pattern_worker = PatternDetectionWorker(self.extremum_points, pattern_types, data_to_use, self)
        self.pattern_worker.progress.connect(self.progress_bar.setValue)
        self.pattern_worker.status.connect(self.status_bar.showMessage)
        self.pattern_worker.finished.connect(self.onPatternsDetected)

        # Disable button during detection and change text
        self.detect_patterns_btn.setEnabled(False)
        self.detect_patterns_btn.setText("Detecting... Please Wait")
        self.progress_bar.setVisible(True)  # Make sure progress bar is visible
        if DEBUG_MODE: print("Starting pattern worker thread...")
        self.pattern_worker.start()

    def onPatternsDetected(self, patterns):
        """Handle detected patterns"""
        self.detected_patterns = patterns
        self.detect_patterns_btn.setEnabled(True)
        self.backtest_btn.setEnabled(True)
        self.detect_patterns_btn.setText("Detect Patterns")  # Restore original text
        self.progress_bar.setValue(0)

        # Clean up the worker thread
        if hasattr(self, 'pattern_worker'):
            self.pattern_worker.deleteLater()
            self.pattern_worker = None

        # Count total patterns
        total_patterns = sum(len(p) for p in patterns.values())
        self.status_bar.showMessage(f"Detected {total_patterns} patterns")

        # Show message box with results
        pattern_counts = []
        for ptype, plist in patterns.items():
            if plist:
                pattern_counts.append(f"{ptype.upper()}: {len(plist)} patterns")

        if total_patterns > 0:
            # Always open pattern viewer window (removed show all patterns option)
            QMessageBox.information(
                self,
                "Pattern Detection Complete",
                f"Found {total_patterns} patterns!\n\n" + "\n".join(pattern_counts) +
                "\n\nOpening Pattern Viewer window..."
            )

            data_to_use = self.filtered_data if self.filtered_data is not None else self.data
            self.pattern_window = PatternViewerWindow(
                self,
                patterns,
                data_to_use,
                self.extremum_points
            )
            self.pattern_window.showMaximized()

        else:
            QMessageBox.information(
                self,
                "Pattern Detection Complete",
                "No patterns found with current settings.\n\nTry adjusting extremum detection length or date range."
            )

        self.updateStatistics()

    def displayAllPatternsOnMainChart(self, patterns):
        """Display all detected patterns on the main chart"""
        # Clear any existing pattern lines
        if hasattr(self, 'pattern_lines'):
            for line in self.pattern_lines:
                self.main_chart.removeItem(line)
        self.pattern_lines = []

        # Flatten all patterns into a single list
        all_patterns = []
        for ptype, plist in patterns.items():
            for pattern in plist:
                pattern['pattern_type'] = ptype
                all_patterns.append(pattern)

        # Define colors for different pattern types
        colors = {
            'abcd': {'formed': (0, 255, 0, 100),      # Green with transparency
                     'bull': (0, 255, 0, 100),
                     'bear': (0, 200, 0, 100)},        # Darker green
            'xabcd': {'formed': (255, 107, 107, 100), # Red with transparency
                      'bull': (255, 107, 107, 100),
                      'bear': (200, 50, 50, 100)},     # Darker red
            'unformed': {'bull': (144, 238, 144, 100),  # Light green
                        'bear': (144, 200, 144, 100)},   # Darker light green
            'unformed_xabcd': {'bull': (255, 182, 182, 100),  # Light red
                              'bear': (200, 150, 150, 100)}    # Darker light red
        }

        # Draw each pattern on the main chart
        pattern_count = 0
        for pattern in all_patterns:
            pattern_type = pattern.get('pattern_type', 'unknown')
            is_bullish = 'bull' in pattern.get('name', '').lower()

            # Determine color
            if pattern_type in colors:
                if is_bullish and 'bull' in colors[pattern_type]:
                    color = colors[pattern_type]['bull']
                elif not is_bullish and 'bear' in colors[pattern_type]:
                    color = colors[pattern_type]['bear']
                else:
                    color = colors[pattern_type].get('formed', (128, 128, 128, 100))
            else:
                color = (128, 128, 128, 100)  # Gray for unknown

            # Determine line style
            if 'unformed' in pattern_type:
                style = pg.QtCore.Qt.PenStyle.DashLine
            else:
                style = pg.QtCore.Qt.PenStyle.SolidLine

            # Draw pattern lines
            if 'points' in pattern:
                points = pattern['points']
                point_names = ['X', 'A', 'B', 'C', 'D'] if 'X' in points else ['A', 'B', 'C', 'D']

                # Handle projected D point
                if 'D_projected' in points:
                    point_names = [p for p in point_names if p != 'D']
                    point_names.append('D_projected')

                # Draw lines between consecutive points
                for i in range(len(point_names) - 1):
                    p1_name = point_names[i]
                    p2_name = point_names[i + 1]

                    if p1_name in points and p2_name in points:
                        p1 = points[p1_name]
                        p2 = points[p2_name]

                        if 'index' in p1 and 'price' in p1 and 'index' in p2 and 'price' in p2:
                            pen = pg.mkPen(color=color, width=1.5, style=style)
                            line = pg.PlotDataItem([p1['index'], p2['index']],
                                                 [p1['price'], p2['price']],
                                                 pen=pen)
                            self.main_chart.addItem(line)
                            self.pattern_lines.append(line)

            pattern_count += 1

        # Update status bar
        self.status_bar.showMessage(f"Displaying {pattern_count} patterns on main chart")

        # Show legend info in statistics
        legend_text = f"Pattern Overlay - {pattern_count} patterns displayed\n"
        legend_text += "=" * 40 + "\n"
        legend_text += "Color Legend:\n"
        legend_text += "  Green: Formed ABCD (Bulls lighter)\n"
        legend_text += "  Red: Formed XABCD (Bulls lighter)\n"
        legend_text += "  Light Green: Unformed ABCD\n"
        legend_text += "  Light Red: Unformed XABCD\n"
        legend_text += "  Solid lines: Formed patterns\n"
        legend_text += "  Dashed lines: Unformed patterns\n"

        current_stats = self.stats_text.toPlainText()
        self.stats_text.setText(current_stats + "\n\n" + legend_text)

    def showAllPatternsWindow(self, patterns):
        """Create and show a new window displaying all patterns"""
        try:
            print("=== showAllPatternsWindow called ===")
            print(f"Creating AllPatternsWindow...")

            # Debug: Check the structure of patterns
            print(f"Pattern keys: {patterns.keys()}")
            for ptype, plist in patterns.items():
                print(f"  {ptype}: {type(plist)}, length: {len(plist) if isinstance(plist, list) else 'not a list'}")
                if isinstance(plist, list) and len(plist) > 0:
                    print(f"    First item type: {type(plist[0])}")
                    if not isinstance(plist[0], dict):
                        print(f"    WARNING: First item is not a dict: {plist[0]}")

            # Count total patterns
            total_patterns = sum(len(plist) if isinstance(plist, list) else 0 for plist in patterns.values())
            print(f"Total patterns to display: {total_patterns}")

            # Create all patterns window with original patterns dictionary
            data_to_use = self.filtered_data if self.filtered_data is not None else self.data
            print(f"Data shape: {data_to_use.shape}")
            print(f"Extremum points count: {len(self.extremum_points)}")

            # Use improved window if available, otherwise fallback to original
            print(f"IMPROVED_DISPLAY_AVAILABLE = {IMPROVED_DISPLAY_AVAILABLE}")
            if IMPROVED_DISPLAY_AVAILABLE:
                print("Using ImprovedAllPatternsWindow...")
                print("About to create ImprovedAllPatternsWindow...")
                self.all_patterns_window = ImprovedAllPatternsWindow(
                    self,
                    data_to_use,
                    patterns,  # Pass original patterns dictionary
                    self.extremum_points
                )
                print("ImprovedAllPatternsWindow created successfully")
            else:
                print("Using original AllPatternsWindow...")
                self.all_patterns_window = AllPatternsWindow(
                    self,
                    data_to_use,
                    patterns,  # Pass original patterns dictionary
                    self.extremum_points
                )

            print("Showing AllPatternsWindow...")
            self.all_patterns_window.show()
            print("AllPatternsWindow should be visible now")

        except Exception as e:
            import traceback
            print(f"ERROR in showAllPatternsWindow: {e}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error args: {e.args}")
            print(f"Full traceback:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "Error", f"Failed to create All Patterns window:\n{str(e)}")

    # Dead code removed - pattern display is handled by PatternViewerWindow

    def saveExtremums(self):
        """Save extremums to file"""
        if not self.extremum_points:
            QMessageBox.warning(self, "Warning", "No extremums to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Extremums",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            extremums_data = [
                {
                    'date': str(ep[0]),
                    'price': ep[1],
                    'is_high': ep[2]
                }
                for ep in self.extremum_points
            ]

            with open(file_path, 'w') as f:
                json.dump(extremums_data, f, indent=2)

            self.status_bar.showMessage(f"Extremums saved to {file_path}")

    def loadExtremums(self):
        """Load extremums from file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Extremums",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            try:
                with open(file_path, 'r') as f:
                    extremums_data = json.load(f)

                self.extremum_points = [
                    (
                        pd.to_datetime(ep['date']),
                        ep['price'],
                        ep['is_high']
                    )
                    for ep in extremums_data
                ]

                self.plotExtremums()
                self.detect_patterns_btn.setEnabled(True)
                self.backtest_btn.setEnabled(True)
                self.status_bar.showMessage(f"Loaded {len(self.extremum_points)} extremums")
                self.updateStatistics()

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load extremums: {str(e)}")

    def toggleAddMode(self):
        """Toggle add extremum mode"""
        if self.add_extremum_btn.isChecked():
            self.edit_mode = 'add'
            self.remove_extremum_btn.setChecked(False)
            self.status_bar.showMessage("Add mode: Click on candlestick top for HIGH, bottom for LOW")
        else:
            self.edit_mode = None
            self.status_bar.showMessage("Add mode disabled")

    def toggleRemoveMode(self):
        """Toggle remove extremum mode"""
        if self.remove_extremum_btn.isChecked():
            self.edit_mode = 'remove'
            self.add_extremum_btn.setChecked(False)
            self.status_bar.showMessage("Remove mode: Click on extremum point to remove it")
        else:
            self.edit_mode = None
            self.status_bar.showMessage("Remove mode disabled")

    def clearAllExtremums(self):
        """Clear all extremum points"""
        if not self.manual_edit_checkbox.isChecked():
            return

        reply = QMessageBox.question(
            self, "Clear All Extremums",
            "Are you sure you want to clear all extremum points?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.extremum_points = []
            self.selected_point = None
            self.plotExtremums()
            self.updateStatistics()
            self.detect_patterns_btn.setEnabled(False)
            self.status_bar.showMessage("All extremum points cleared")

    def savePatterns(self):
        """Save detected patterns"""
        if not self.detected_patterns:
            QMessageBox.warning(self, "Warning", "No patterns to save")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Patterns",
            "",
            "CSV Files (*.csv);;JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            # Implementation for saving patterns
            self.status_bar.showMessage(f"Patterns saved to {file_path}")

    def resetView(self):
        """Reset chart view"""
        self.main_chart.autoRange()

    def showAbout(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About",
            "Harmonic Pattern Detection System\n\n"
            "Built with PyQt6 and PyQtGraph\n"
            "High-performance financial pattern analysis"
        )

    def openBacktestDialog(self):
        """Open the backtesting dialog window"""
        from PyQt6.QtWidgets import QMessageBox

        # Get current settings
        current_extremum = self.length_spinbox.value()
        start_date = self.start_date_edit.date()
        end_date = self.end_date_edit.date()

        # Create informative message
        msg = QMessageBox()
        msg.setWindowTitle("Backtesting Configuration")
        msg.setText("<b>Before proceeding with backtesting:</b>")

        info_text = (
            f"<p>Your current GUI settings will be used:</p>"
            f"<ul>"
            f"<li><b>Extremum Length:</b> {current_extremum}</li>"
            f"<li><b>Date Range:</b> {start_date.toString('yyyy-MM-dd')} to {end_date.toString('yyyy-MM-dd')}</li>"
            f"</ul>"
            f"<p>The backtesting will inherit these settings for consistency.</p>"
            f"<p><b>Recommendations:</b><br>"
            f"• Use <b>Extremum Length = 1</b> for maximum pattern detection<br>"
            f"• Select a specific <b>date range</b> for reproducible results<br>"
            f"• Smaller date ranges (50-200 bars) allow complete pattern analysis</p>"
            f"<p>Do you want to continue with these settings?</p>"
        )
        msg.setInformativeText(info_text)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        # Style the message box
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #f9f9f9;
            }
            QMessageBox QLabel {
                color: #333333;
                font-size: 12px;
            }
        """)

        # Show message and get response
        response = msg.exec()

        if response == QMessageBox.StandardButton.Yes:
            # Proceed with opening the dialog
            if not hasattr(self, 'backtesting_dialog'):
                self.backtesting_dialog = BacktestingDialog(self, self.data)
            else:
                # Update data if it has changed
                self.backtesting_dialog.data = self.data
            self.backtesting_dialog.show()
        # If No, user can adjust settings before trying again

    def updateStatistics(self):
        """Update statistics display"""
        stats = []

        # Data statistics
        if self.data is not None:
            stats.append(f"Total data: {len(self.data)} rows")

        if self.filtered_data is not None:
            stats.append(f"Filtered data: {len(self.filtered_data)} rows")
            stats.append(f"Date range: {self.filtered_data.index[0].date()} to {self.filtered_data.index[-1].date()}")

        # Extremum statistics
        if self.extremum_points:
            highs = sum(1 for ep in self.extremum_points if ep[2])
            lows = sum(1 for ep in self.extremum_points if not ep[2])
            stats.append(f"Extremums: {highs} highs, {lows} lows")

        # Pattern statistics
        if self.detected_patterns:
            for pattern_type, patterns in self.detected_patterns.items():
                if patterns:
                    stats.append(f"{pattern_type.upper()}: {len(patterns)} patterns")

        self.stats_text.setText("\n".join(stats))

    def closeEvent(self, event):
        """Handle application close event - ensure proper cleanup"""
        try:
            # Clean up any running threads
            if hasattr(self, 'pattern_worker') and self.pattern_worker is not None:
                if self.pattern_worker.isRunning():
                    self.pattern_worker.quit()
                    self.pattern_worker.wait(3000)  # Wait up to 3 seconds
                self.pattern_worker.deleteLater()
                self.pattern_worker = None

            # Clean up crosshair proxy
            if hasattr(self, 'proxy') and self.proxy is not None:
                self.proxy.disconnect()
                self.proxy = None

            if DEBUG_MODE: print("Application cleanup completed")
            event.accept()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle('Fusion')

    # Create and show main window
    window = HarmonicPatternDetector()
    window.showMaximized()  # Show window maximized by default

    sys.exit(app.exec())


if __name__ == '__main__':
    main()