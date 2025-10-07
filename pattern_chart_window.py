"""
Pattern Chart Window - Interactive visual display of harmonic pattern

Shows:
- Interactive candlestick chart (like main GUI)
- Pattern lines (X-A-B-C-D points with labels)
- PRZ zone highlighted
- Fibonacci retracement levels
- Harmonic points marked
- Crosshair with OHLC info
- Date/time on X-axis
"""

import sys
import pandas as pd
import numpy as np
import json
from typing import Dict, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QFont, QColor

import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen, mkBrush


class DateAxisItem(pg.AxisItem):
    """Custom axis item to display dates on X-axis (same as backtesting dialog)"""

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
                    # Format date as dd MMM YYYY
                    strings.append(date.strftime('%d %b %Y'))
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
        """Generate the picture of candlesticks (same as backtesting dialog)"""
        self.picture = pg.QtGui.QPicture()
        painter = pg.QtGui.QPainter(self.picture)

        # Set pen for drawing
        bullPen = pg.mkPen(color='g', width=1)
        bearPen = pg.mkPen(color='r', width=1)
        bullBrush = pg.mkBrush('g')
        bearBrush = pg.mkBrush('r')

        width = 0.6  # Width of candlestick body (works with integer indices)

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
                # Draw the high-low line (use integer index i)
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


class PatternChartWindow(QMainWindow):
    """Window to display pattern chart with interactive visualization"""

    def __init__(self, signal: Dict, parent=None):
        super().__init__(parent)

        self.signal = signal
        self.df = None
        self.display_data = None
        self.display_min = 0
        self.display_max = 0
        self.is_redrawing = False  # Flag to prevent multiple simultaneous redraws

        self.initUI()
        self.loadAndPlotChart()

    def initUI(self):
        """Initialize the user interface"""
        pattern_name = self.signal['pattern_name'].replace('_', ' ').title()
        direction = self.signal['direction'].title()

        self.setWindowTitle(f"Pattern Chart - {self.signal['symbol']} {self.signal['timeframe']} - {pattern_name} {direction}")
        self.setGeometry(100, 100, 1400, 900)
        self.showMaximized()  # Open maximized by default

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel(f"📊 {self.signal['symbol']} {self.signal['timeframe']} - {pattern_name} ({direction})")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Pattern info
        info_text = f"Status: {self.signal['status'].title()} | "
        info_text += f"Current: ${self.signal['current_price']:.2f} | "
        info_text += f"PRZ: ${self.signal['prz_min']:.2f}-${self.signal['prz_max']:.2f} | "
        info_text += f"Entry: ${self.signal['entry_price']:.2f} | "
        info_text += f"SL: ${self.signal['stop_loss']:.2f}"

        info_label = QLabel(info_text)
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(info_label)

        main_layout.addLayout(header_layout)

        # Chart options
        options_layout = QHBoxLayout()

        self.show_fibonacci_checkbox = QCheckBox("Show Fibonacci Levels")
        self.show_fibonacci_checkbox.setChecked(True)
        self.show_fibonacci_checkbox.stateChanged.connect(self.redrawChart)
        options_layout.addWidget(self.show_fibonacci_checkbox)

        self.show_harmonic_checkbox = QCheckBox("Show Harmonic Points (A, B, C)")
        self.show_harmonic_checkbox.setChecked(True)
        self.show_harmonic_checkbox.stateChanged.connect(self.redrawChart)
        options_layout.addWidget(self.show_harmonic_checkbox)

        self.show_trade_levels_checkbox = QCheckBox("Show Trade Levels (Entry, SL, TPs)")
        self.show_trade_levels_checkbox.setChecked(True)
        self.show_trade_levels_checkbox.stateChanged.connect(self.redrawChart)
        options_layout.addWidget(self.show_trade_levels_checkbox)

        self.show_all_prz_checkbox = QCheckBox("Show All PRZ Zones (ABCD only)")
        self.show_all_prz_checkbox.setChecked(False)
        self.show_all_prz_checkbox.stateChanged.connect(self.redrawChart)
        options_layout.addWidget(self.show_all_prz_checkbox)

        options_layout.addStretch()
        main_layout.addLayout(options_layout)

        # Chart widget (PyQtGraph) - create ONCE with DateAxisItem (same as backtesting dialog)
        self.date_axis = DateAxisItem([], orientation='bottom')
        self.chart = pg.PlotWidget(axisItems={'bottom': self.date_axis})
        self.chart.setBackground('w')
        self.chart.showGrid(x=False, y=False)  # Disable grid to avoid mixing with levels
        self.chart.setLabel('left', 'Price ($)')
        self.chart.setMouseTracking(True)

        # Initialize crosshair (will be created after data loads)
        self.vLine = None
        self.hLine = None
        self.x_axis_label = None
        self.y_axis_label = None
        self.crosshair_label = None
        self.proxy = None

        main_layout.addWidget(self.chart)

        # Footer with targets
        footer_layout = QHBoxLayout()

        targets = json.loads(self.signal['targets_json'])
        targets_text = "Targets: "
        for i, target in enumerate(targets, 1):
            targets_text += f"TP{i}: ${target:.2f}  "

        targets_label = QLabel(targets_text)
        targets_label.setStyleSheet("color: #1976D2; font-weight: bold;")
        footer_layout.addWidget(targets_label)

        footer_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        footer_layout.addWidget(close_btn)

        main_layout.addLayout(footer_layout)

    def loadAndPlotChart(self):
        """Load data and plot the chart with pattern"""
        try:
            # Load chart data from file_path
            file_path = self.findChartFile()

            if not file_path:
                QMessageBox.warning(self, "Data Not Found",
                    f"Could not find data file for {self.signal['symbol']} {self.signal['timeframe']}")
                return

            # Load data
            self.df = pd.read_csv(file_path)

            # Ensure datetime index
            if 'Timestamp' in self.df.columns:
                # Convert timestamp - could be milliseconds or seconds
                timestamps = self.df['Timestamp']
                # Check if values are large (likely milliseconds)
                if timestamps.iloc[0] > 1e10:
                    self.df['Timestamp'] = pd.to_datetime(timestamps, unit='ms')
                else:
                    self.df['Timestamp'] = pd.to_datetime(timestamps, unit='s')
                self.df.set_index('Timestamp', inplace=True)
            elif 'Date' in self.df.columns:
                self.df['Date'] = pd.to_datetime(self.df['Date'])
                self.df.set_index('Date', inplace=True)
            else:
                # No timestamp column found - use the first column as index if it looks like dates
                if pd.api.types.is_numeric_dtype(self.df.iloc[:, 0]):
                    # Numeric - treat as timestamp
                    timestamps = self.df.iloc[:, 0]
                    if timestamps.iloc[0] > 1e10:
                        self.df.index = pd.to_datetime(timestamps, unit='ms')
                    else:
                        self.df.index = pd.to_datetime(timestamps, unit='s')
                    self.df = self.df.iloc[:, 1:]  # Remove the timestamp column
                else:
                    # Try to parse as datetime
                    self.df.index = pd.to_datetime(self.df.iloc[:, 0])
                    self.df = self.df.iloc[:, 1:]

            # Standardize column names
            column_mapping = {}
            for col in self.df.columns:
                if col.lower() in ['open', 'high', 'low', 'close', 'volume']:
                    column_mapping[col] = col.capitalize()

            if column_mapping:
                self.df.rename(columns=column_mapping, inplace=True)

            print(f"Loaded data with {len(self.df)} rows")
            print(f"Index type: {type(self.df.index)}")
            print(f"First index: {self.df.index[0]}")
            print(f"Columns: {self.df.columns.tolist()}")

            # Plot chart
            self.plotPattern()

        except Exception as e:
            print(f"Error loading chart data: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load chart: {e}")

    def findChartFile(self) -> Optional[str]:
        """Find the data file for this symbol/timeframe from watchlist"""
        import os

        watchlist_path = "data/watchlist.json"

        if os.path.exists(watchlist_path):
            with open(watchlist_path, 'r') as f:
                data = json.load(f)
                charts = data.get('charts', [])

                for chart in charts:
                    if (chart['symbol'] == self.signal['symbol'] and
                        chart['timeframe'] == self.signal['timeframe']):
                        return chart['file_path']

        # Fallback: try standard paths
        standard_paths = [
            f"data/{self.signal['symbol'].lower()}_{self.signal['timeframe']}.csv",
            f"{self.signal['symbol'].lower()}_{self.signal['timeframe']}.csv"
        ]

        for path in standard_paths:
            if os.path.exists(path):
                return path

        return None

    def redrawChart(self):
        """Redraw chart when options change - preserve view range"""
        if self.df is not None and not self.is_redrawing:
            try:
                self.is_redrawing = True
                print(f"Redrawing chart - Fib: {self.show_fibonacci_checkbox.isChecked()}, Harmonic: {self.show_harmonic_checkbox.isChecked()}")

                # Save current view range before clearing
                view_range = self.chart.viewRange()

                # Clear chart and re-plot (crosshair will be recreated)
                self.chart.clear()
                self.plotPattern()

                # Restore view range to prevent auto-adjustment
                self.chart.setRange(xRange=view_range[0], yRange=view_range[1], padding=0)

            except Exception as e:
                print(f"Error redrawing chart: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.is_redrawing = False

    def plotPattern(self):
        """Plot the chart with pattern overlay (same as main GUI)"""
        # Get pattern points from signal
        points_json = self.signal['points_json']
        print(f"DEBUG: points_json = {points_json}")
        points_dict = json.loads(points_json)
        print(f"DEBUG: points_dict = {points_dict}")

        # The points might be stored as simple integers (bar indices) in the format:
        # {"A": 164, "B": 165, "C": 166} where these are bar indices in the ORIGINAL full dataset
        # We need to map these bar indices to actual prices and times

        # Convert points format to match main GUI
        points = {}
        for point_name, point_data in points_dict.items():
            if point_data is not None:
                # point_data is likely just an integer (bar index from original detection)
                if isinstance(point_data, (int, float)):
                    # This is a bar index from the original detection
                    # We need to find this bar in our loaded dataframe
                    bar_idx = int(point_data)

                    # The bar_idx might be from the original full dataset
                    # Our self.df might not have that many bars
                    # So we need to get the actual price/time differently

                    # For now, let's see if we can extract from pattern detection results
                    # stored in the signal itself
                    print(f"DEBUG: Point {point_name} has bar index {bar_idx}")

                    # Try to use the bar index if it's within range
                    if 0 <= bar_idx < len(self.df):
                        timestamp = self.df.index[bar_idx]
                        if not isinstance(timestamp, pd.Timestamp):
                            timestamp = pd.to_datetime(timestamp)

                        points[point_name] = {
                            'bar': bar_idx,
                            'time': timestamp,
                            'price': float(self.df.iloc[bar_idx]['Close'])
                        }
                        print(f"DEBUG: Mapped to time={timestamp}, price={self.df.iloc[bar_idx]['Close']}")
                    else:
                        print(f"WARNING: Bar index {bar_idx} out of range (df has {len(self.df)} bars)")

                elif isinstance(point_data, dict):
                    # If it's a dict, check if 'time' is a bar index or actual timestamp
                    if 'time' in point_data and 'price' in point_data:
                        time_val = point_data['time']

                        # Check if time_val is a bar index (small integer) or actual timestamp (large number)
                        if isinstance(time_val, (int, float)):
                            # If it's a small number (< 10000), it's likely a bar index
                            if time_val < 10000:
                                # Treat as bar index
                                bar_idx = int(time_val)
                                print(f"DEBUG: Point {point_name} has bar index {bar_idx} in dict format")

                                if 0 <= bar_idx < len(self.df):
                                    timestamp = self.df.index[bar_idx]
                                    if not isinstance(timestamp, pd.Timestamp):
                                        timestamp = pd.to_datetime(timestamp)

                                    points[point_name] = {
                                        'bar': bar_idx,
                                        'time': timestamp,
                                        'price': point_data['price']
                                    }
                                    print(f"DEBUG: Mapped to time={timestamp}, price={point_data['price']}")
                                else:
                                    print(f"WARNING: Bar index {bar_idx} out of range (df has {len(self.df)} bars)")
                            else:
                                # It's a Unix timestamp
                                if time_val > 1e10:
                                    time_val = pd.to_datetime(time_val, unit='ms')
                                else:
                                    time_val = pd.to_datetime(time_val, unit='s')
                                point_data['time'] = time_val
                                points[point_name] = point_data
                        elif not isinstance(time_val, pd.Timestamp):
                            # Try to convert string or other format
                            time_val = pd.to_datetime(time_val)
                            point_data['time'] = time_val
                            points[point_name] = point_data
                        else:
                            # Already a Timestamp
                            points[point_name] = point_data

        print(f"DEBUG: Final points = {points}")

        # Get all pattern dates for determining the range
        pattern_dates = []
        for point_name in ['X', 'A', 'B', 'C', 'D']:
            if point_name in points and 'time' in points[point_name]:
                pattern_dates.append(points[point_name]['time'])

        if not pattern_dates:
            QMessageBox.warning(self, "Pattern Error", "Could not extract pattern points from signal data.")
            return

        # Find the data range for this pattern
        min_date = min(pattern_dates)
        max_date = max(pattern_dates)

        # Get data indices
        try:
            min_idx = self.df.index.get_loc(min_date)
            max_idx = self.df.index.get_loc(max_date)
        except:
            # If exact date not found, find nearest
            min_idx = np.argmin(np.abs(self.df.index - min_date))
            max_idx = np.argmin(np.abs(self.df.index - max_date))

        # Expand the range for context
        display_min = max(0, min_idx - 50)
        display_max = min(len(self.df), max_idx + 50)

        # Get the data slice
        display_data = self.df.iloc[display_min:display_max]

        # Store for crosshair
        self.display_data = display_data
        self.display_min = display_min
        self.display_max = display_max

        # Update date axis with current data dates (like backtesting dialog)
        self.date_axis.dates = display_data.index.tolist()

        # Setup crosshair (re-create after clear)
        self.setupCrosshair()

        # Create candlestick chart (reset index for integer x-coordinates)
        candles = CandlestickItem(display_data.reset_index(drop=True))
        self.chart.addItem(candles)

        # Set Y-axis range
        y_min = display_data['Low'].min() * 0.999
        y_max = display_data['High'].max() * 1.001
        self.chart.setYRange(y_min, y_max, padding=0)

        # Set X-axis range and disable auto-range (like backtesting dialog)
        self.chart.setXRange(0, len(display_data) - 1, padding=0.02)
        self.chart.disableAutoRange()

        # Plot pattern lines
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

                # Find the position in display data (integer index)
                try:
                    actual_idx = self.df.index.get_loc(point_time)
                except:
                    actual_idx = np.argmin(np.abs(self.df.index - point_time))

                # Convert to display coordinates (relative to display_min)
                display_idx = actual_idx - display_min

                if 0 <= display_idx < len(display_data):
                    x_coords.append(display_idx)
                    y_coords.append(point_price)
                    labels.append(point_name)

        # Draw pattern lines
        if len(x_coords) >= 2:
            is_bullish = self.signal['direction'] == 'bullish'
            color = '#00BFFF' if is_bullish else '#FF8C00'

            # Draw lines connecting pattern points
            pen = pg.mkPen(color=color, width=3, style=Qt.PenStyle.SolidLine)
            point_pen = pg.mkPen('#000000', width=2)
            point_brush = pg.mkBrush('#FFFF00')
            self.chart.plot(x_coords, y_coords, pen=pen, symbol='o',
                          symbolPen=point_pen, symbolBrush=point_brush, symbolSize=16)

            # Add labels for each point
            for i, (x, y, label) in enumerate(zip(x_coords, y_coords, labels)):
                point_name = label
                if point_name in points and 'time' in points[point_name]:
                    point_time = points[point_name]['time']

                    # Convert to pandas timestamp if needed
                    if not isinstance(point_time, pd.Timestamp):
                        point_time = pd.to_datetime(point_time)

                    # Format date properly
                    if point_time.hour == 0 and point_time.minute == 0 and point_time.second == 0:
                        datetime_str = point_time.strftime('%d %b %Y')
                    else:
                        datetime_str = point_time.strftime('%d %b %Y %H:%M')

                    label_text = f"{label}\n${y:.2f}\n{datetime_str}"
                else:
                    label_text = f"{label}\n${y:.2f}"

                text = pg.TextItem(label_text, color='#000000', anchor=(0.5, 1.2))
                text.setPos(x, y)
                text.setFont(QFont('Arial', 12, QFont.Weight.Bold))  # Increased from 10 to 12
                self.chart.addItem(text)

            # Draw harmonic point horizontal lines if enabled
            if self.show_harmonic_checkbox.isChecked():
                harmonic_points = ['A', 'B', 'C']
                # Use dark purple to avoid confusion with red candlesticks
                harmonic_colors = {'A': '#9370DB', 'B': '#9370DB', 'C': '#9370DB'}  # Dark purple

                for point_name in harmonic_points:
                    if point_name in labels:
                        idx = labels.index(point_name)
                        price = y_coords[idx]
                        color = harmonic_colors.get(point_name, '#888888')

                        # Draw horizontal line with thicker width
                        point_pen = mkPen(color=color, width=3, style=Qt.PenStyle.SolidLine)
                        self.chart.plot([0, len(display_data)-1], [price, price], pen=point_pen)

                        # Add label on the RIGHT side (like Fib levels) - larger font
                        point_text = pg.TextItem(f"Point {point_name}", color=color, anchor=(0, 0.5))
                        # Offset Y position slightly above the line for better readability
                        price_offset = price + (display_data['High'].max() - display_data['Low'].min()) * 0.01
                        point_text.setPos(len(display_data) - 5, price_offset)
                        point_text.setFont(QFont('Arial', 12, QFont.Weight.Bold))
                        self.chart.addItem(point_text)

            # Draw Fibonacci levels if enabled
            if self.show_fibonacci_checkbox.isChecked():
                self.drawFibonacciLevels(points, x_coords, y_coords, labels, is_bullish)

        # Draw PRZ zone(s)
        # If "Show All PRZ" is checked, draw all individual zones
        # Otherwise, if "Show Trade Levels" is checked, draw the combined PRZ
        if self.show_all_prz_checkbox.isChecked():
            prz_zones_json = self.signal.get('prz_zones_json', '[]')
            if prz_zones_json:
                try:
                    prz_zones = json.loads(prz_zones_json)
                    if prz_zones and len(x_coords) > 0:
                        last_x = x_coords[-1]
                        prz_color_hex = '#FF8C00'

                        for i, zone in enumerate(prz_zones, 1):
                            zone_min = zone.get('min') or zone.get('zone_min', 0)
                            zone_max = zone.get('max') or zone.get('zone_max', 0)

                            if zone_min > 0 and zone_max > 0:
                                # Draw zone as shaded rectangle
                                zone_color = QColor(prz_color_hex)
                                zone_color.setAlpha(80)
                                zone_brush = pg.mkBrush(zone_color)

                                rect = pg.QtWidgets.QGraphicsRectItem(last_x - 10, zone_min,
                                                                     20, zone_max - zone_min)
                                rect.setBrush(zone_brush)
                                rect.setPen(pg.mkPen(prz_color_hex, width=2))
                                rect.setZValue(-10)
                                self.chart.addItem(rect)

                                # Add label
                                label_text = f"PRZ{i}\n{zone_min:.2f}-{zone_max:.2f}"
                                text = pg.TextItem(label_text, color=prz_color_hex, anchor=(0, 0.5))
                                text.setPos(last_x + 12, (zone_min + zone_max) / 2)
                                text.setFont(QFont('Arial', 11, QFont.Weight.Bold))
                                self.chart.addItem(text)
                except:
                    pass
        elif self.show_trade_levels_checkbox.isChecked():
            # Draw only the specific PRZ zone for this pattern (not all combined)
            prz_zones_json = self.signal.get('prz_zones_json', '[]')
            prz_min = None
            prz_max = None
            prz_number = None  # Track which PRZ zone this is

            # Try to find the matching PRZ zone for this specific pattern
            if prz_zones_json:
                try:
                    prz_zones = json.loads(prz_zones_json)
                    pattern_name = self.signal['pattern_name']

                    # Remove "_unformed" or "_formed" suffix to match with pattern_source
                    pattern_base = pattern_name.replace('_unformed', '').replace('_formed', '')

                    # Find matching zone by pattern_source
                    for i, zone in enumerate(prz_zones, 1):
                        zone_source = zone.get('pattern_source', '')
                        if zone_source and pattern_base in zone_source or zone_source in pattern_base:
                            prz_min = zone.get('min') or zone.get('zone_min', 0)
                            prz_max = zone.get('max') or zone.get('zone_max', 0)
                            prz_number = i  # Store the zone number (1-indexed)
                            break
                except:
                    pass

            # Fallback to signal's prz_min/prz_max if no specific zone found
            if prz_min is None or prz_max is None:
                prz_min = self.signal['prz_min']
                prz_max = self.signal['prz_max']

            # Use orange color for PRZ
            prz_color_hex = '#FF8C00'

            # Get last X position from pattern points
            display_data_len = len(self.display_data)
            last_x = display_data_len - 1

            # If we have pattern points, use the last one
            if len(x_coords) > 0:
                last_x = x_coords[-1]

            # Draw PRZ as shaded rectangle
            prz_qcolor = QColor(prz_color_hex)
            prz_qcolor.setAlpha(80)
            prz_brush = pg.mkBrush(prz_qcolor)

            rect = pg.QtWidgets.QGraphicsRectItem(last_x - 10, prz_min, 20, prz_max - prz_min)
            rect.setBrush(prz_brush)
            rect.setPen(pg.mkPen(prz_color_hex, width=2))
            rect.setZValue(-10)
            self.chart.addItem(rect)

            # Add PRZ label with zone number if found
            if prz_number:
                label_text = f"PRZ{prz_number}\n{prz_min:.2f}-{prz_max:.2f}"
            else:
                label_text = f"PRZ\n{prz_min:.2f}-{prz_max:.2f}"
            prz_text = pg.TextItem(label_text, color=prz_color_hex, anchor=(0, 0.5))
            prz_text.setPos(last_x + 12, (prz_min + prz_max) / 2)
            prz_text.setFont(QFont('Arial', 11, QFont.Weight.Bold))
            self.chart.addItem(prz_text)

        # Draw Entry, SL, TPs, Current if "Show Trade Levels" is checked
        if self.show_trade_levels_checkbox.isChecked():
            # Draw Entry, SL, TPs with colored labels
            entry_line = pg.InfiniteLine(pos=self.signal['entry_price'], angle=0,
                                         pen=pg.mkPen('#00AA00', width=2, style=Qt.PenStyle.DashLine))
            entry_label = pg.InfLineLabel(entry_line, text=f"Entry: ${self.signal['entry_price']:.2f}",
                                          position=0.95, color='#00AA00', movable=False)
            self.chart.addItem(entry_line)

            sl_line = pg.InfiniteLine(pos=self.signal['stop_loss'], angle=0,
                                      pen=pg.mkPen('#FF0000', width=2, style=Qt.PenStyle.DashLine))
            sl_label = pg.InfLineLabel(sl_line, text=f"SL: ${self.signal['stop_loss']:.2f}",
                                       position=0.95, color='#FF0000', movable=False)
            self.chart.addItem(sl_line)

            targets = json.loads(self.signal['targets_json'])
            tp_colors = ['#4CAF50', '#8BC34A', '#CDDC39', '#FFC107', '#FF9800']
            for i, target in enumerate(targets):
                tp_line = pg.InfiniteLine(pos=target, angle=0,
                                         pen=pg.mkPen(tp_colors[i % len(tp_colors)], width=1.5,
                                                     style=Qt.PenStyle.DotLine))
                tp_label = pg.InfLineLabel(tp_line, text=f"TP{i+1}: ${target:.2f}",
                                           position=0.95, color=tp_colors[i % len(tp_colors)], movable=False)
                self.chart.addItem(tp_line)

            # Current price
            current_line = pg.InfiniteLine(pos=self.signal['current_price'], angle=0,
                                           pen=pg.mkPen('#0000FF', width=2, style=Qt.PenStyle.SolidLine))
            current_label = pg.InfLineLabel(current_line, text=f"Current: ${self.signal['current_price']:.2f}",
                                            position=0.95, color='#0000FF', movable=False)
            self.chart.addItem(current_line)

    def drawFibonacciLevels(self, points, x_coords, y_coords, labels, is_bullish):
        """Draw Fibonacci retracement levels (same as backtesting dialog)"""
        fib_levels = [0, 23.6, 38.2, 50, 61.8, 78.6, 88.6, 100, 112.8, 127.2, 141.4, 161.8]

        # Get A, C, D prices for Fibonacci calculation
        a_price = None
        c_price = None
        d_price = None

        if 'A' in labels:
            a_idx = labels.index('A')
            a_price = y_coords[a_idx]
        if 'C' in labels:
            c_idx = labels.index('C')
            c_price = y_coords[c_idx]
        if 'D' in labels:
            d_idx = labels.index('D')
            d_price = y_coords[d_idx]

        # If no D, use zone_entry_price from signal
        if d_price is None:
            d_price = self.signal.get('zone_entry_price') or self.signal.get('entry_price')

        if a_price is None or c_price is None or d_price is None:
            return

        # Determine if bullish or bearish from actual prices (same as backtesting)
        is_bullish = a_price > c_price

        if is_bullish:
            start_price = max(a_price, c_price)
            end_price = d_price
            price_range = end_price - start_price
        else:
            start_price = d_price
            end_price = min(a_price, c_price)
            price_range = end_price - start_price

        # Get display data length for line drawing
        display_data_len = len(self.display_data) if self.display_data is not None else 100

        # Calculate and draw each Fibonacci level
        for level in fib_levels:
            fib_price = start_price + (price_range * level / 100.0)

            # Use gold for golden ratios (50%, 61.8%), turquoise for others (same as backtesting)
            if level in [50, 61.8]:
                color = '#FFD700'  # Gold for golden ratios
                line_width = 3
            else:
                color = '#00CED1'  # Dark turquoise for others
                line_width = 2

            # Draw horizontal line (same as backtesting)
            fib_pen = mkPen(color=color, width=line_width, style=Qt.PenStyle.DashLine)
            self.chart.plot([0, display_data_len-1], [fib_price, fib_price], pen=fib_pen)

            # Add label on the right side - offset slightly above line for readability
            fib_text = pg.TextItem(f"Fib {level}%", color=color, anchor=(0, 0.5))
            # Offset Y position slightly above the line (1% of price range)
            price_offset = fib_price + (abs(price_range) * 0.01)
            fib_text.setPos(display_data_len - 5, price_offset)
            fib_text.setFont(QFont('Arial', 12, QFont.Weight.Bold))
            self.chart.addItem(fib_text)

    def setupCrosshair(self):
        """Setup crosshair lines and labels (same as backtesting dialog)"""
        # Create crosshair lines
        self.vLine = pg.InfiniteLine(angle=90, movable=False,
                                     pen=pg.mkPen('cyan', width=2, style=Qt.PenStyle.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False,
                                     pen=pg.mkPen('cyan', width=2, style=Qt.PenStyle.DashLine))

        self.chart.addItem(self.vLine, ignoreBounds=True)
        self.chart.addItem(self.hLine, ignoreBounds=True)

        # X-axis label (date) - larger font
        self.x_axis_label = pg.TextItem('', anchor=(0.5, 0), color='white',
                                        fill=pg.mkBrush(0, 100, 255, 220),
                                        border=pg.mkPen('white', width=2))
        self.x_axis_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))  # Increased from 9 to 11
        self.x_axis_label.setZValue(1000)
        self.chart.addItem(self.x_axis_label)

        # Y-axis label (price) - larger font
        self.y_axis_label = pg.TextItem('', anchor=(0, 0.5), color='white',
                                        fill=pg.mkBrush(0, 100, 255, 220),
                                        border=pg.mkPen('white', width=2))
        self.y_axis_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))  # Increased from 9 to 11
        self.y_axis_label.setZValue(1000)
        self.chart.addItem(self.y_axis_label)

        # OHLC info box - larger font
        self.crosshair_label = pg.TextItem('', anchor=(0, 0), color='white',
                                          fill=pg.mkBrush(0, 0, 0, 150),
                                          border=pg.mkPen('cyan', width=1))
        self.crosshair_label.setFont(QFont('Arial', 11, QFont.Weight.Bold))  # Increased from 9 to 11
        self.crosshair_label.setZValue(1001)
        self.chart.addItem(self.crosshair_label)

        # Initially hide
        self.vLine.setVisible(False)
        self.hLine.setVisible(False)
        self.x_axis_label.setVisible(False)
        self.y_axis_label.setVisible(False)
        self.crosshair_label.setVisible(False)

        # Setup mouse tracking
        self.proxy = pg.SignalProxy(self.chart.scene().sigMouseMoved, rateLimit=15, slot=self.mouseMoved)
        self.chart.setMouseTracking(True)

    def mouseMoved(self, evt):
        """Handle mouse movement for crosshair (same as backtesting dialog)"""
        if not hasattr(self, 'vLine') or self.vLine is None:
            return

        pos = evt[0]
        if self.chart.sceneBoundingRect().contains(pos):
            mousePoint = self.chart.plotItem.vb.mapSceneToView(pos)
            x, y = mousePoint.x(), mousePoint.y()

            # Show crosshair
            self.vLine.setPos(x)
            self.hLine.setPos(y)
            self.vLine.setVisible(True)
            self.hLine.setVisible(True)

            # Update axis labels and OHLC label
            self.updateAxisLabels(x, y)
            self.updateCrosshairLabel(x, y)
        else:
            # Hide crosshair
            if self.vLine.isVisible():
                self.vLine.setVisible(False)
                self.hLine.setVisible(False)
                self.x_axis_label.setVisible(False)
                self.y_axis_label.setVisible(False)
                self.crosshair_label.setVisible(False)

    def updateAxisLabels(self, x, y):
        """Update axis labels with current values (same as backtesting dialog)"""
        try:
            if self.display_data is None or len(self.display_data) == 0:
                return

            # Get view range for positioning
            view_range = self.chart.viewRange()

            # Format and position X-axis (date) label
            x_int = int(round(x))
            if 0 <= x_int < len(self.display_data):
                date = self.display_data.index[x_int]
                if hasattr(date, 'strftime'):
                    if date.hour == 0 and date.minute == 0 and date.second == 0:
                        time_str = date.strftime('%d %b %Y')
                    else:
                        time_str = date.strftime('%d %b %H:%M')
                else:
                    time_str = str(date)[:16]

                # Position near bottom of chart area
                x_label_y = view_range[1][0] + (view_range[1][1] - view_range[1][0]) * 0.05
                self.x_axis_label.setText(time_str)
                self.x_axis_label.setPos(x, x_label_y)
                self.x_axis_label.setVisible(True)

            # Format and position Y-axis (price) label
            price_str = f"${y:,.2f}"

            # Position at left edge of chart, centered on crosshair
            y_label_x = view_range[0][0] + (view_range[0][1] - view_range[0][0]) * 0.02
            self.y_axis_label.setText(price_str)
            self.y_axis_label.setPos(y_label_x, y)
            self.y_axis_label.setVisible(True)

        except Exception as e:
            pass

    def updateCrosshairLabel(self, x, y):
        """Update OHLC info box (same as backtesting dialog)"""
        try:
            if self.display_data is None or len(self.display_data) == 0:
                return

            x_int = int(round(x))
            if 0 <= x_int < len(self.display_data):
                # Get date and OHLC data for this index
                date = self.display_data.index[x_int]
                row = self.display_data.iloc[x_int]

                # Format date
                if hasattr(date, 'strftime'):
                    if date.hour == 0 and date.minute == 0 and date.second == 0:
                        date_str = date.strftime('%d %b %Y')
                    else:
                        date_str = date.strftime('%d %b %H:%M')
                else:
                    date_str = str(date)[:16]

                # Format price information
                open_price = float(row['Open'])
                high_price = float(row['High'])
                low_price = float(row['Low'])
                close_price = float(row['Close'])

                # Create label text
                label_text = f"Time: {date_str}\n"
                label_text += f"Open:  ${open_price:,.2f}\n"
                label_text += f"High:  ${high_price:,.2f}\n"
                label_text += f"Low:   ${low_price:,.2f}\n"
                label_text += f"Close: ${close_price:,.2f}"

                self.crosshair_label.setText(label_text)

                # Position in upper left corner
                view_range = self.chart.viewRange()
                self.crosshair_label.setPos(view_range[0][0] + 2, view_range[1][1] * 0.98)
                self.crosshair_label.setVisible(True)

        except Exception as e:
            pass

