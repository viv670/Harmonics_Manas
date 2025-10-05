"""
Interactive PyQt Charts for Pattern Completion Analysis
Uses pyqtgraph for high-performance interactive visualizations
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QPen
import pyqtgraph as pg
import numpy as np


class PatternCompletionChartsWidget(QWidget):
    """Widget containing all pattern completion analysis charts"""

    pattern_clicked = pyqtSignal(str, str)  # status, pattern_type

    def __init__(self, parent=None):
        super().__init__(parent)
        self.stats_data = None
        self.initUI()

    def initUI(self):
        """Initialize the chart interface"""
        layout = QVBoxLayout()

        # Top row: Two charts side by side
        top_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Chart 1: Stacked Bar Chart - Status Breakdown
        self.status_chart_widget = QWidget()
        status_layout = QVBoxLayout()
        status_label = QLabel("📊 Status Breakdown (ABCD vs XABCD)")
        status_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        status_layout.addWidget(status_label)

        self.status_chart = pg.PlotWidget()
        self.status_chart.setBackground('w')
        self.status_chart.showGrid(x=True, y=False, alpha=0.3)
        self.status_chart.setLabel('left', 'Status')
        self.status_chart.setLabel('bottom', 'Count')
        status_layout.addWidget(self.status_chart)
        self.status_chart_widget.setLayout(status_layout)

        # Chart 2: Pie Chart - Success Composition
        self.pie_chart_widget = QWidget()
        pie_layout = QVBoxLayout()
        pie_label = QLabel("🥧 Success Composition")
        pie_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        pie_layout.addWidget(pie_label)

        self.pie_chart = pg.PlotWidget()
        self.pie_chart.setBackground('w')
        self.pie_chart.setAspectLocked(True)
        self.pie_chart.hideAxis('bottom')
        self.pie_chart.hideAxis('left')
        pie_layout.addWidget(self.pie_chart)
        self.pie_chart_widget.setLayout(pie_layout)

        top_splitter.addWidget(self.status_chart_widget)
        top_splitter.addWidget(self.pie_chart_widget)
        top_splitter.setStretchFactor(0, 6)
        top_splitter.setStretchFactor(1, 4)

        layout.addWidget(top_splitter)

        # Bottom: Success Rate Comparison
        rate_widget = QWidget()
        rate_layout = QVBoxLayout()
        rate_label = QLabel("📈 Success Rate Comparison")
        rate_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        rate_layout.addWidget(rate_label)

        self.rate_chart = pg.PlotWidget()
        self.rate_chart.setBackground('w')
        self.rate_chart.showGrid(x=False, y=True, alpha=0.3)
        self.rate_chart.setLabel('left', 'Success Rate (%)')
        self.rate_chart.setLabel('bottom', 'Pattern Type')
        rate_layout.addWidget(self.rate_chart)
        rate_widget.setLayout(rate_layout)

        layout.addWidget(rate_widget)

        # Info label
        self.info_label = QLabel("Click on charts to explore data")
        self.info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def updateCharts(self, stats):
        """Update all charts with new statistics data"""
        self.stats_data = stats

        # Extract data
        success = stats.get('patterns_success', 0)
        success_abcd = stats.get('patterns_success_abcd', 0)
        success_xabcd = stats.get('patterns_success_xabcd', 0)

        failed = stats.get('patterns_failed', 0)
        failed_abcd = stats.get('patterns_failed_abcd', 0)
        failed_xabcd = stats.get('patterns_failed_xabcd', 0)

        in_zone = stats.get('patterns_in_zone', 0)
        in_zone_abcd = stats.get('patterns_in_zone_abcd', 0)
        in_zone_xabcd = stats.get('patterns_in_zone_xabcd', 0)

        dismissed = stats.get('patterns_dismissed', 0)
        pending = stats.get('patterns_pending', 0)

        # Update Chart 1: Stacked Bar Chart
        self.updateStatusChart(success_abcd, success_xabcd, failed_abcd, failed_xabcd,
                              in_zone_abcd, in_zone_xabcd, dismissed, pending)

        # Update Chart 2: Pie Chart
        self.updatePieChart(success_abcd, success_xabcd)

        # Update Chart 3: Success Rate Chart
        self.updateSuccessRateChart(success_abcd, success_xabcd, failed_abcd, failed_xabcd)

        # Update info
        total = success + failed + in_zone + dismissed + pending
        self.info_label.setText(
            f"Total Tracked: {total} | Success: {success} | Failed: {failed} | "
            f"In Zone: {in_zone} | Dismissed: {dismissed} | Pending: {pending}"
        )

    def updateStatusChart(self, success_abcd, success_xabcd, failed_abcd, failed_xabcd,
                         in_zone_abcd, in_zone_xabcd, dismissed, pending):
        """Create horizontal stacked bar chart for status breakdown"""
        self.status_chart.clear()

        # Data for stacked bars
        statuses = ['Success', 'Failed', 'In Zone', 'Dismissed', 'Pending']
        y_positions = np.arange(len(statuses))

        # ABCD values (left stack)
        abcd_values = [success_abcd, failed_abcd, in_zone_abcd, dismissed, pending]

        # XABCD values (right stack, offset by ABCD)
        xabcd_values = [success_xabcd, failed_xabcd, in_zone_xabcd, 0, 0]

        # Colors
        abcd_color = QColor(52, 152, 219)  # Blue
        xabcd_color = QColor(230, 126, 34)  # Orange

        # Create horizontal bar graphs
        bar_height = 0.6

        for i, (status, abcd_val, xabcd_val) in enumerate(zip(statuses, abcd_values, xabcd_values)):
            # ABCD bar
            if abcd_val > 0:
                bar1 = pg.BarGraphItem(
                    x0=[0], y0=[i - bar_height/2],
                    height=[bar_height], width=[abcd_val],
                    brush=abcd_color, pen=pg.mkPen(color='k', width=1)
                )
                self.status_chart.addItem(bar1)

                # Add text label
                text_item = pg.TextItem(str(abcd_val), anchor=(0.5, 0.5), color='w')
                text_item.setPos(abcd_val/2, i)
                self.status_chart.addItem(text_item)

            # XABCD bar (stacked on top of ABCD)
            if xabcd_val > 0:
                bar2 = pg.BarGraphItem(
                    x0=[abcd_val], y0=[i - bar_height/2],
                    height=[bar_height], width=[xabcd_val],
                    brush=xabcd_color, pen=pg.mkPen(color='k', width=1)
                )
                self.status_chart.addItem(bar2)

                # Add text label
                text_item = pg.TextItem(str(xabcd_val), anchor=(0.5, 0.5), color='w')
                text_item.setPos(abcd_val + xabcd_val/2, i)
                self.status_chart.addItem(text_item)

            # Total label at end
            total = abcd_val + xabcd_val
            if total > 0:
                total_text = pg.TextItem(f'{total}', anchor=(0, 0.5), color='k')
                total_text.setPos(total + 2, i)
                self.status_chart.addItem(total_text)

        # Set y-axis labels
        y_axis = self.status_chart.getAxis('left')
        y_axis.setTicks([[(i, status) for i, status in enumerate(statuses)]])

        # Add legend
        legend = self.status_chart.addLegend(offset=(10, 10))
        legend.addItem(pg.BarGraphItem(brush=abcd_color), 'ABCD')
        legend.addItem(pg.BarGraphItem(brush=xabcd_color), 'XABCD')

        # Set range
        max_val = max([a + x for a, x in zip(abcd_values, xabcd_values)]) * 1.15
        self.status_chart.setXRange(0, max_val)
        self.status_chart.setYRange(-0.5, len(statuses) - 0.5)

    def updatePieChart(self, success_abcd, success_xabcd):
        """Create pie chart for success composition"""
        self.pie_chart.clear()

        total = success_abcd + success_xabcd
        if total == 0:
            # Show message when no data
            text = pg.TextItem("No successful patterns yet", anchor=(0.5, 0.5), color='gray')
            text.setPos(0, 0)
            self.pie_chart.addItem(text)
            return

        # Calculate percentages
        abcd_pct = (success_abcd / total) * 100
        xabcd_pct = (success_xabcd / total) * 100

        # Colors
        abcd_color = QColor(52, 152, 219)  # Blue
        xabcd_color = QColor(230, 126, 34)  # Orange

        # Draw pie slices
        radius = 1.0
        start_angle = 0

        # ABCD slice
        if success_abcd > 0:
            abcd_angle = (success_abcd / total) * 360
            self.drawPieSlice(0, 0, radius, start_angle, abcd_angle, abcd_color)

            # Add label
            label_angle = start_angle + abcd_angle / 2
            label_x = 0.6 * radius * np.cos(np.radians(label_angle))
            label_y = 0.6 * radius * np.sin(np.radians(label_angle))
            text = pg.TextItem(f'ABCD\n{success_abcd}\n({abcd_pct:.1f}%)',
                             anchor=(0.5, 0.5), color='w')
            text.setPos(label_x, label_y)
            self.pie_chart.addItem(text)

            start_angle += abcd_angle

        # XABCD slice
        if success_xabcd > 0:
            xabcd_angle = (success_xabcd / total) * 360
            self.drawPieSlice(0, 0, radius, start_angle, xabcd_angle, xabcd_color)

            # Add label
            label_angle = start_angle + xabcd_angle / 2
            label_x = 0.6 * radius * np.cos(np.radians(label_angle))
            label_y = 0.6 * radius * np.sin(np.radians(label_angle))
            text = pg.TextItem(f'XABCD\n{success_xabcd}\n({xabcd_pct:.1f}%)',
                             anchor=(0.5, 0.5), color='w')
            text.setPos(label_x, label_y)
            self.pie_chart.addItem(text)

        # Set range to show full pie
        self.pie_chart.setXRange(-1.2, 1.2)
        self.pie_chart.setYRange(-1.2, 1.2)

    def drawPieSlice(self, cx, cy, radius, start_angle, span_angle, color):
        """Draw a pie slice using polygon"""
        num_points = max(int(span_angle / 2), 3)  # At least 3 points
        angles = np.linspace(start_angle, start_angle + span_angle, num_points)

        # Create points for the slice
        points = [(cx, cy)]  # Center point
        for angle in angles:
            x = cx + radius * np.cos(np.radians(angle))
            y = cy + radius * np.sin(np.radians(angle))
            points.append((x, y))
        points.append((cx, cy))  # Close the slice

        # Create polygon
        x_points = [p[0] for p in points]
        y_points = [p[1] for p in points]

        poly = pg.PlotCurveItem(
            x_points, y_points,
            fillLevel=0,
            brush=pg.mkBrush(color),
            pen=pg.mkPen(color='k', width=2)
        )
        self.pie_chart.addItem(poly)

    def updateSuccessRateChart(self, success_abcd, success_xabcd, failed_abcd, failed_xabcd):
        """Create bar chart comparing success rates"""
        self.rate_chart.clear()

        # Calculate success rates
        total_abcd = success_abcd + failed_abcd
        total_xabcd = success_xabcd + failed_xabcd

        abcd_rate = (success_abcd / total_abcd * 100) if total_abcd > 0 else 0
        xabcd_rate = (success_xabcd / total_xabcd * 100) if total_xabcd > 0 else 0

        # Data
        pattern_types = ['ABCD', 'XABCD']
        rates = [abcd_rate, xabcd_rate]
        x_positions = [0, 1]

        # Colors based on performance
        colors = []
        for rate in rates:
            if rate >= 70:
                colors.append(QColor(46, 204, 113))  # Green
            elif rate >= 50:
                colors.append(QColor(241, 196, 15))  # Yellow
            else:
                colors.append(QColor(231, 76, 60))   # Red

        # Create bars
        bar_width = 0.4
        for x, rate, color, ptype, success, total in zip(
            x_positions, rates, colors, pattern_types,
            [success_abcd, success_xabcd], [total_abcd, total_xabcd]
        ):
            # Bar
            bar = pg.BarGraphItem(
                x=[x], height=[rate], width=bar_width,
                brush=color, pen=pg.mkPen(color='k', width=1)
            )
            self.rate_chart.addItem(bar)

            # Percentage label on top
            text = pg.TextItem(f'{rate:.1f}%', anchor=(0.5, 1), color='k')
            text.setPos(x, rate + 2)
            self.rate_chart.addItem(text)

            # Count label inside bar
            if rate > 20:  # Only show if bar is tall enough
                count_text = pg.TextItem(
                    f'{success}/{total}',
                    anchor=(0.5, 0.5), color='w'
                )
                count_text.setPos(x, rate/2)
                self.rate_chart.addItem(count_text)

        # Set x-axis labels
        x_axis = self.rate_chart.getAxis('bottom')
        x_axis.setTicks([[(i, ptype) for i, ptype in enumerate(pattern_types)]])

        # Set range
        self.rate_chart.setXRange(-0.5, 1.5)
        self.rate_chart.setYRange(0, 105)

        # Add reference line at 50%
        ref_line = pg.InfiniteLine(pos=50, angle=0, pen=pg.mkPen('gray', style=Qt.PenStyle.DashLine))
        self.rate_chart.addItem(ref_line)


class PatternDetailsTableWidget(QWidget):
    """Table showing detailed pattern information with filtering"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        """Initialize the table interface"""
        layout = QVBoxLayout()

        # Header
        header_label = QLabel("📋 Pattern Details")
        header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(header_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            'Type', 'Pattern Name', 'Status', 'A', 'B', 'C', 'D'
        ])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        # Style
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #d0d0d0;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        layout.addWidget(self.table)

        # Info label
        self.info_label = QLabel("No data loaded")
        self.info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def updateTable(self, backtester):
        """Update table with pattern data from backtester"""
        if not backtester or not hasattr(backtester, 'pattern_tracker'):
            return

        tracker = backtester.pattern_tracker
        patterns = tracker.tracked_patterns

        self.table.setRowCount(len(patterns))

        row = 0
        for pattern_id, pattern in patterns.items():
            # Type
            type_item = QTableWidgetItem(pattern.pattern_type)
            self.table.setItem(row, 0, type_item)

            # Name
            name_item = QTableWidgetItem(pattern.subtype)
            self.table.setItem(row, 1, name_item)

            # Status
            status_item = QTableWidgetItem(pattern.status)
            # Color code by status
            if pattern.status == 'success':
                status_item.setBackground(QBrush(QColor(46, 204, 113, 100)))
            elif pattern.status == 'failed':
                status_item.setBackground(QBrush(QColor(231, 76, 60, 100)))
            elif pattern.status == 'in_zone':
                status_item.setBackground(QBrush(QColor(241, 196, 15, 100)))
            self.table.setItem(row, 2, status_item)

            # Points
            if pattern.a_point:
                self.table.setItem(row, 3, QTableWidgetItem(str(pattern.a_point[0])))
            if pattern.b_point:
                self.table.setItem(row, 4, QTableWidgetItem(str(pattern.b_point[0])))
            if pattern.c_point:
                self.table.setItem(row, 5, QTableWidgetItem(str(pattern.c_point[0])))
            if pattern.d_point:
                self.table.setItem(row, 6, QTableWidgetItem(str(pattern.d_point[0])))

            row += 1

        self.info_label.setText(f"Showing {len(patterns)} patterns")

    def filterByStatus(self, status):
        """Filter table to show only patterns with given status"""
        for row in range(self.table.rowCount()):
            status_item = self.table.item(row, 2)
            if status_item:
                should_show = status_item.text() == status
                self.table.setRowHidden(row, not should_show)

    def clearFilter(self):
        """Show all rows"""
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row, False)
