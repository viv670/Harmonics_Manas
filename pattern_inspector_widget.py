"""
Pattern Inspector Widget - Visual pattern-by-pattern analyzer
Shows individual patterns with price charts, similar to main GUI
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import pyqtgraph as pg
import numpy as np


class PatternInspectorWidget(QWidget):
    """Widget for inspecting individual patterns visually"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.backtester = None
        self.data = None
        self.filtered_patterns = []
        self.current_index = 0
        self.initUI()

    def initUI(self):
        """Initialize the pattern inspector interface"""
        layout = QVBoxLayout()

        # Top controls
        controls_layout = QHBoxLayout()

        # Filter dropdown
        filter_label = QLabel("Filter by Status:")
        controls_layout.addWidget(filter_label)

        self.status_filter = QComboBox()
        self.status_filter.addItems([
            'All Patterns',
            'Success ✅',
            'Failed ❌',
            'In Zone 🎯',
            'Dismissed 🚫',
            'Pending ⏳'
        ])
        self.status_filter.currentTextChanged.connect(self.onFilterChanged)
        controls_layout.addWidget(self.status_filter)

        controls_layout.addStretch()

        # Pattern counter
        self.pattern_counter = QLabel("Pattern 0 of 0")
        self.pattern_counter.setStyleSheet("font-weight: bold; font-size: 12px;")
        controls_layout.addWidget(self.pattern_counter)

        # Navigation buttons
        self.prev_button = QPushButton("◀ Previous")
        self.prev_button.clicked.connect(self.showPreviousPattern)
        self.prev_button.setEnabled(False)
        controls_layout.addWidget(self.prev_button)

        self.next_button = QPushButton("Next ▶")
        self.next_button.clicked.connect(self.showNextPattern)
        self.next_button.setEnabled(False)
        controls_layout.addWidget(self.next_button)

        layout.addLayout(controls_layout)

        # Pattern info group
        info_group = QGroupBox("Pattern Information")
        info_layout = QVBoxLayout()

        self.pattern_info = QLabel("No pattern selected")
        self.pattern_info.setWordWrap(True)
        self.pattern_info.setStyleSheet("padding: 10px;")
        info_layout.addWidget(self.pattern_info)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Price chart
        chart_group = QGroupBox("Price Chart with Pattern")
        chart_layout = QVBoxLayout()

        self.price_chart = pg.PlotWidget()
        self.price_chart.setBackground('w')
        self.price_chart.showGrid(x=True, y=True, alpha=0.3)
        self.price_chart.setLabel('left', 'Price')
        self.price_chart.setLabel('bottom', 'Bar Index')
        self.price_chart.addLegend()

        chart_layout.addWidget(self.price_chart)
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)

        # Status message
        self.status_label = QLabel("Load backtest data to inspect patterns")
        self.status_label.setStyleSheet("color: gray; font-style: italic; padding: 5px;")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def loadData(self, backtester):
        """Load backtest data for pattern inspection"""
        self.backtester = backtester
        if backtester and hasattr(backtester, 'data'):
            self.data = backtester.data

            # Debug: Check what we have
            if hasattr(backtester, 'pattern_tracker'):
                tracker = backtester.pattern_tracker
                total_patterns = len(tracker.tracked_patterns)
                print(f"DEBUG Inspector: Found {total_patterns} tracked patterns")

                # Show status breakdown
                for status in ['success', 'failed', 'in_zone', 'dismissed', 'pending']:
                    count = sum(1 for p in tracker.tracked_patterns.values() if p.status == status)
                    print(f"  - {status}: {count}")

            self.onFilterChanged(self.status_filter.currentText())
            self.status_label.setText(f"Loaded {len(self.data)} bars of price data, {total_patterns} patterns")

    def onFilterChanged(self, filter_text):
        """Filter patterns based on selected status"""
        if not self.backtester:
            print("DEBUG: No backtester in onFilterChanged")
            return

        if not hasattr(self.backtester, 'pattern_tracker'):
            print("DEBUG: No pattern_tracker in backtester")
            return

        tracker = self.backtester.pattern_tracker
        all_patterns = tracker.tracked_patterns

        print(f"DEBUG: onFilterChanged called with '{filter_text}'")
        print(f"DEBUG: Total patterns available: {len(all_patterns)}")

        # Map filter text to status
        status_map = {
            'All Patterns': None,
            'Success ✅': 'success',
            'Failed ❌': 'failed',
            'In Zone 🎯': 'in_zone',
            'Dismissed 🚫': 'dismissed',
            'Pending ⏳': 'pending'
        }

        status = status_map.get(filter_text)
        print(f"DEBUG: Filtering by status: {status}")

        # Filter patterns
        if status is None:
            self.filtered_patterns = list(all_patterns.items())
        else:
            self.filtered_patterns = [
                (pid, p) for pid, p in all_patterns.items()
                if p.status == status
            ]

        print(f"DEBUG: Filtered patterns count: {len(self.filtered_patterns)}")

        # Update UI
        self.current_index = 0
        self.updateNavigationButtons()
        self.showCurrentPattern()

    def updateNavigationButtons(self):
        """Update navigation button states"""
        total = len(self.filtered_patterns)
        self.prev_button.setEnabled(self.current_index > 0)
        self.next_button.setEnabled(self.current_index < total - 1)

        if total > 0:
            self.pattern_counter.setText(f"Pattern {self.current_index + 1} of {total}")
        else:
            self.pattern_counter.setText("No patterns match filter")

    def showPreviousPattern(self):
        """Show previous pattern"""
        if self.current_index > 0:
            self.current_index -= 1
            self.updateNavigationButtons()
            self.showCurrentPattern()

    def showNextPattern(self):
        """Show next pattern"""
        if self.current_index < len(self.filtered_patterns) - 1:
            self.current_index += 1
            self.updateNavigationButtons()
            self.showCurrentPattern()

    def showCurrentPattern(self):
        """Display the current pattern on chart"""
        print(f"DEBUG: showCurrentPattern called, filtered_patterns: {len(self.filtered_patterns)}, data is None: {self.data is None}")

        if not self.filtered_patterns:
            self.pattern_info.setText("No patterns match the selected filter")
            self.price_chart.clear()
            return

        if self.data is None:
            self.pattern_info.setText("No price data available")
            self.price_chart.clear()
            return

        pattern_id, pattern = self.filtered_patterns[self.current_index]

        print(f"DEBUG: Showing pattern {self.current_index + 1}/{len(self.filtered_patterns)}: {pattern.subtype}")

        # Update pattern info
        info_text = self.formatPatternInfo(pattern)
        self.pattern_info.setText(info_text)

        # Draw pattern on chart
        self.drawPatternOnChart(pattern)

    def formatPatternInfo(self, pattern):
        """Format pattern information for display"""
        info = f"<b>Pattern Type:</b> {pattern.pattern_type}<br>"
        info += f"<b>Pattern Name:</b> {pattern.subtype}<br>"

        # Status with emoji
        status_emoji = {
            'success': '✅ Success',
            'failed': '❌ Failed',
            'in_zone': '🎯 In PRZ Zone',
            'dismissed': '🚫 Dismissed',
            'pending': '⏳ Pending'
        }
        info += f"<b>Status:</b> {status_emoji.get(pattern.status, pattern.status)}<br><br>"

        # Points
        if pattern.x_point:
            info += f"<b>X Point:</b> Bar {pattern.x_point[0]}, Price {pattern.x_point[1]:.2f}<br>"
        if pattern.a_point:
            info += f"<b>A Point:</b> Bar {pattern.a_point[0]}, Price {pattern.a_point[1]:.2f}<br>"
        if pattern.b_point:
            info += f"<b>B Point:</b> Bar {pattern.b_point[0]}, Price {pattern.b_point[1]:.2f}<br>"
        if pattern.c_point:
            info += f"<b>C Point:</b> Bar {pattern.c_point[0]}, Price {pattern.c_point[1]:.2f}<br>"
        if pattern.d_point:
            info += f"<b>D Point:</b> Bar {pattern.d_point[0]}, Price {pattern.d_point[1]:.2f}<br>"

        # Additional details
        info += f"<br><b>First Seen:</b> Bar {pattern.first_seen_bar}<br>"

        if pattern.zone_entry_bar:
            info += f"<b>PRZ Entry:</b> Bar {pattern.zone_entry_bar}<br>"

        if pattern.reversal_bar:
            info += f"<b>Reversal:</b> Bar {pattern.reversal_bar}<br>"

        # PRZ info
        if pattern.prz_min and pattern.prz_max:
            info += f"<br><b>PRZ Zone:</b> {pattern.prz_min:.2f} - {pattern.prz_max:.2f}<br>"

        return info

    def drawPatternOnChart(self, pattern):
        """Draw the pattern on the price chart"""
        self.price_chart.clear()

        if self.data is None:
            return

        # Get pattern point indices
        points = []
        if pattern.x_point:
            points.append(('X', pattern.x_point[0], pattern.x_point[1]))
        if pattern.a_point:
            points.append(('A', pattern.a_point[0], pattern.a_point[1]))
        if pattern.b_point:
            points.append(('B', pattern.b_point[0], pattern.b_point[1]))
        if pattern.c_point:
            points.append(('C', pattern.c_point[0], pattern.c_point[1]))
        if pattern.d_point:
            points.append(('D', pattern.d_point[0], pattern.d_point[1]))

        if not points:
            return

        # Calculate chart range
        all_indices = [p[1] for p in points]
        min_idx = min(all_indices)
        max_idx = max(all_indices)

        # Add padding
        padding = max(20, (max_idx - min_idx) // 4)
        start_idx = max(0, min_idx - padding)
        end_idx = min(len(self.data) - 1, max_idx + padding)

        # Plot price data (candlesticks)
        price_data = self.data.iloc[start_idx:end_idx + 1]
        x_range = np.arange(start_idx, end_idx + 1)

        # Plot high/low as line
        self.price_chart.plot(
            x_range, price_data['High'].values,
            pen=pg.mkPen(color='gray', width=1, style=Qt.PenStyle.DotLine)
        )
        self.price_chart.plot(
            x_range, price_data['Low'].values,
            pen=pg.mkPen(color='gray', width=1, style=Qt.PenStyle.DotLine)
        )

        # Plot close price
        self.price_chart.plot(
            x_range, price_data['Close'].values,
            pen=pg.mkPen(color='black', width=2),
            name='Price'
        )

        # Draw pattern lines
        colors = {
            'X': QColor(128, 0, 128),   # Purple
            'A': QColor(255, 0, 0),     # Red
            'B': QColor(0, 128, 0),     # Green
            'C': QColor(0, 0, 255),     # Blue
            'D': QColor(255, 165, 0)    # Orange
        }

        # Draw lines connecting points
        for i in range(len(points) - 1):
            label1, idx1, price1 = points[i]
            label2, idx2, price2 = points[i + 1]

            # Draw line
            line = pg.PlotCurveItem(
                [idx1, idx2], [price1, price2],
                pen=pg.mkPen(color=QColor(52, 152, 219), width=3)
            )
            self.price_chart.addItem(line)

        # Draw points and labels
        for label, idx, price in points:
            # Point marker
            scatter = pg.ScatterPlotItem(
                [idx], [price],
                size=15,
                brush=pg.mkBrush(colors[label]),
                pen=pg.mkPen('k', width=2),
                symbol='o'
            )
            self.price_chart.addItem(scatter)

            # Label
            text = pg.TextItem(label, color='k', anchor=(0.5, 1.5))
            text.setPos(idx, price)
            self.price_chart.addItem(text)

        # Draw PRZ zone
        if pattern.prz_min and pattern.prz_max:
            # Find D point index or use last point
            d_idx = pattern.d_point[0] if pattern.d_point else points[-1][1]

            # Draw PRZ zone as filled region
            prz_region = pg.LinearRegionItem(
                values=[pattern.prz_min, pattern.prz_max],
                orientation='horizontal',
                brush=pg.mkBrush(255, 255, 0, 50),  # Yellow transparent
                movable=False
            )
            self.price_chart.addItem(prz_region)

        # Set chart range
        self.price_chart.setXRange(start_idx, end_idx)

        # Set Y range with padding
        all_prices = [p[2] for p in points]
        min_price = min(all_prices)
        max_price = max(all_prices)
        price_padding = (max_price - min_price) * 0.1
        self.price_chart.setYRange(min_price - price_padding, max_price + price_padding)

        # Add title
        status_color = {
            'success': 'green',
            'failed': 'red',
            'in_zone': 'orange',
            'dismissed': 'gray',
            'pending': 'blue'
        }
        title = f'<span style="color: {status_color.get(pattern.status, "black")};">{pattern.subtype} - {pattern.status.upper()}</span>'
        self.price_chart.setTitle(title)
