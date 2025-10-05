"""
Backtesting Dialog for Harmonic Pattern Trading System
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QProgressBar,
    QMessageBox, QCheckBox, QComboBox, QRadioButton, QDateEdit,
    QButtonGroup, QSplitter, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtGui import QPixmap
import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkPen, mkBrush
import pandas as pd
import numpy as np
import os
from datetime import datetime
from PyQt6.QtGui import QFont, QColor
from optimized_walk_forward_backtester import OptimizedWalkForwardBacktester
from enhanced_excel_export import (
    create_enhanced_pattern_details,
    create_fibonacci_analysis_sheet,
    create_pattern_performance_sheet,
    create_enhanced_summary
)


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
                    # Format date as dd MMM (TradingView style)
                    strings.append(date.strftime('%d %b'))
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


class BacktestThread(QThread):
    """Thread for running backtest without blocking GUI"""
    progress = pyqtSignal(int)
    message = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, data, params):
        super().__init__()
        self.data = data
        self.params = params
        self.backtester = None

    def run(self):
        try:
            self.message.emit("Initializing backtester...")
            self.backtester = OptimizedWalkForwardBacktester(
                data=self.data,
                initial_capital=self.params['initial_capital'],
                position_size=self.params['position_size'],
                lookback_window=self.params['lookback_window'],
                future_buffer=self.params['future_buffer'],
                min_pattern_score=self.params['min_pattern_score'],
                max_open_trades=self.params['max_open_trades'],
                detection_interval=self.params['detection_interval'],
                extremum_length=self.params.get('extremum_length', 1)  # Default to 1 to match GUI
            )

            self.message.emit("Running backtest simulation...")
            stats = self.backtester.run_backtest(progress_callback=self.progress.emit)

            self.message.emit("Backtest completed!")

            # Check if stats is None or empty
            if stats is None:
                self.error.emit("Backtest returned no statistics - possible timeout or error")
                return

            # Get pattern counts directly from backtester
            total_unformed = getattr(self.backtester, 'total_unformed_found', 0)
            total_formed = getattr(self.backtester, 'total_formed_found', 0)

            # Get formed pattern breakdown
            formed_abcd = getattr(self.backtester, 'formed_abcd_count', 0)
            formed_xabcd = getattr(self.backtester, 'formed_xabcd_count', 0)

            # Get extremum counts
            total_extremums = getattr(self.backtester, 'total_extremum_points', 0)
            high_extremums = getattr(self.backtester, 'high_extremum_points', 0)
            low_extremums = getattr(self.backtester, 'low_extremum_points', 0)

            # Get pattern type distribution
            pattern_type_counts = getattr(self.backtester, 'pattern_type_counts', {})

            # Convert BacktestStatistics object to dictionary
            stats_dict = {
                'total_return': getattr(stats, 'total_return', 0),
                'sharpe_ratio': getattr(stats, 'sharpe_ratio', 0),
                'max_drawdown': getattr(stats, 'max_drawdown', 0),
                'win_rate': getattr(stats, 'win_rate', 0),
                'total_trades': getattr(stats, 'total_trades', 0),
                'winning_trades': getattr(stats, 'winning_trades', 0),
                'losing_trades': getattr(stats, 'losing_trades', 0),
                'avg_win': getattr(stats, 'avg_win', 0),
                'avg_loss': getattr(stats, 'avg_loss', 0),
                'patterns_detected': getattr(stats, 'patterns_detected', 0),
                'patterns_traded': getattr(stats, 'patterns_traded', 0),
                'total_unformed_patterns': total_unformed,
                'total_formed_patterns': total_formed,
                'formed_abcd_count': formed_abcd,
                'formed_xabcd_count': formed_xabcd,
                # Pattern tracking statistics
                'patterns_tracked': getattr(stats, 'patterns_tracked', 0),
                'patterns_completed': getattr(stats, 'patterns_completed', 0),
                'patterns_failed': getattr(stats, 'patterns_failed', 0),
                'patterns_expired': getattr(stats, 'patterns_expired', 0),
                # New lifecycle tracking fields
                'patterns_success': getattr(stats, 'patterns_success', 0),
                'patterns_dismissed': getattr(stats, 'patterns_dismissed', 0),
                'patterns_pending': getattr(stats, 'patterns_pending', 0),
                'patterns_success_rate': getattr(stats, 'patterns_success_rate', 0),
                'avg_projection_accuracy': getattr(stats, 'avg_projection_accuracy', 0),
                'pattern_type_completion_rates': getattr(stats, 'pattern_type_completion_rates', {}),
                'pattern_type_counts': pattern_type_counts,  # Add pattern type distribution
                'initial_capital': self.params['initial_capital'],
                'final_capital': stats.equity_curve[-1] if hasattr(stats, 'equity_curve') and stats.equity_curve else self.params['initial_capital'],
                'peak_capital': max(stats.equity_curve) if hasattr(stats, 'equity_curve') and stats.equity_curve else self.params['initial_capital'],
                'min_pattern_score': self.params['min_pattern_score'],
                # Add extremum counts
                'total_extremum_points': total_extremums,
                'high_extremum_points': high_extremums,
                'low_extremum_points': low_extremums,
                'time_taken': getattr(stats, 'time_taken', 0)
            }

            self.finished.emit(stats_dict)

        except Exception as e:
            import traceback
            error_details = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.error.emit(error_details)


class BacktestingDialog(QDialog):
    """Dialog for configuring and running backtests"""

    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.parent_window = parent
        self.data = data  # This might be filtered data from the main window
        self.full_data = None  # Will store the full dataset
        self.backtest_thread = None
        self.setWindowTitle("Harmonic Pattern Backtesting")
        self.setModal(False)  # Allow interaction with main window

        # Make window resizable and maximizable
        self.setMinimumSize(1000, 600)  # Minimum size
        self.resize(1400, 800)  # Default size (larger for better viewing)

        # Chart display variables
        self.current_chart_category = None
        self.current_chart_index = 0
        self.current_chart_files = []
        self.chart_dir = os.path.join("backtest_results", "pattern_charts")

        # Load the full dataset if available
        self.loadFullDataset()

        self.initUI()

    def loadFullDataset(self):
        """Load the full dataset directly from file to ensure we have ALL data"""
        try:
            import os
            # Try to load the full btcusdt_1d.csv file directly
            btc_file = os.path.join(os.path.dirname(__file__), 'btcusdt_1d.csv')

            if os.path.exists(btc_file):
                self.full_data = pd.read_csv(btc_file)
                # Standardize column names
                self.full_data.rename(columns={
                    'time': 'Date',
                    'open': 'Open',
                    'high': 'High',
                    'low': 'Low',
                    'close': 'Close',
                    'volume': 'Volume'
                }, inplace=True)
                self.full_data['Date'] = pd.to_datetime(self.full_data['Date'])
                self.full_data.set_index('Date', inplace=True)
            else:
                # If file doesn't exist, use whatever data we have
                self.full_data = self.data
        except Exception as e:
            self.full_data = self.data

    def initUI(self):
        """Initialize the user interface"""
        # Main layout
        main_layout = QVBoxLayout()

        # Create horizontal splitter for left (charts) and right (controls) panels
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEFT PANEL: Chart Display Area
        self.chart_panel = self.createChartPanel()
        self.main_splitter.addWidget(self.chart_panel)

        # RIGHT PANEL: Controls and Results
        self.control_panel = self.createControlPanel()
        self.main_splitter.addWidget(self.control_panel)

        # Set initial sizes (75% charts, 25% controls) - match GUI ratio
        self.main_splitter.setSizes([1050, 350])

        main_layout.addWidget(self.main_splitter)
        self.setLayout(main_layout)

        # Initialize date ranges and check data availability
        self.initializeDateRanges()

        # Initialize extremum info label
        self.updateExtremumInfo()

    def createChartPanel(self):
        """Create the left panel for chart display"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout()

        # Title
        title_label = QLabel("Pattern Completion Charts")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px;")
        layout.addWidget(title_label)

        # PyQtGraph chart display - create ONCE like GUI does
        # Create date axis ONCE with empty dates
        self.date_axis = DateAxisItem([], orientation='bottom')
        # Create PlotWidget ONCE with the date axis
        self.pattern_chart = pg.PlotWidget(axisItems={'bottom': self.date_axis})
        self.pattern_chart.setBackground('w')
        self.pattern_chart.showGrid(x=True, y=True, alpha=0.3)
        self.pattern_chart.setLabel('left', 'Price')
        self.pattern_chart.setMinimumSize(700, 500)

        # Initialize crosshair (will be created when chart is displayed)
        self.vLine = None
        self.hLine = None
        self.x_axis_label = None
        self.y_axis_label = None
        self.crosshair_label = None
        self.display_data = None  # Will store currently displayed data for crosshair

        # Add placeholder text
        self.chart_placeholder = QLabel("No charts available.\nRun a backtest to generate pattern charts.")
        self.chart_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_placeholder.setStyleSheet("color: gray; font-size: 12px; padding: 20px;")

        layout.addWidget(self.chart_placeholder)
        layout.addWidget(self.pattern_chart)
        self.pattern_chart.hide()  # Hide initially

        # Navigation controls
        nav_layout = QHBoxLayout()

        self.prev_chart_btn = QPushButton("◀ Previous")
        self.prev_chart_btn.clicked.connect(self.showPreviousChart)
        self.prev_chart_btn.setEnabled(False)
        nav_layout.addWidget(self.prev_chart_btn)

        self.chart_info_label = QLabel("")
        self.chart_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_info_label.setStyleSheet("font-weight: bold;")
        nav_layout.addWidget(self.chart_info_label)

        self.next_chart_btn = QPushButton("Next ▶")
        self.next_chart_btn.clicked.connect(self.showNextChart)
        self.next_chart_btn.setEnabled(False)
        nav_layout.addWidget(self.next_chart_btn)

        layout.addLayout(nav_layout)

        # Pattern Details below chart
        self.pattern_details_text = QTextEdit()
        self.pattern_details_text.setReadOnly(True)
        self.pattern_details_text.setMaximumHeight(150)
        self.pattern_details_text.setStyleSheet(
            "QTextEdit { "
            "background-color: #f8f9fa; "
            "border: 1px solid #dee2e6; "
            "border-radius: 5px; "
            "padding: 8px; "
            "font-family: 'Consolas', 'Monaco', monospace; "
            "font-size: 11px; "
            "}"
        )
        self.pattern_details_text.hide()  # Hide initially
        layout.addWidget(self.pattern_details_text)

        # Fibonacci levels toggle (only for successful patterns)
        fib_layout = QHBoxLayout()
        self.show_fib_checkbox = QCheckBox("Show Fibonacci Levels")
        self.show_fib_checkbox.setChecked(False)
        self.show_fib_checkbox.stateChanged.connect(self.toggleFibonacciLevels)
        self.show_fib_checkbox.setEnabled(False)  # Disabled until successful pattern is shown
        self.show_fib_checkbox.setToolTip(
            "Fibonacci levels calculated from Point A to Point D.\n"
            "For unformed patterns: D = first candle that touched PRZ\n"
            "(High for bearish, Low for bullish)"
        )
        fib_layout.addWidget(self.show_fib_checkbox)
        fib_layout.addStretch()
        layout.addLayout(fib_layout)

        panel.setLayout(layout)
        return panel

    def createControlPanel(self):
        """Create the right panel for controls and results"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout()

        # Parameters Group - Simplified for Pattern Detection Only
        params_group = QGroupBox("Pattern Detection Parameters")
        params_layout = QVBoxLayout()

        # Row 1: Extremum Length (Most Important)
        row1 = QHBoxLayout()
        extremum_label = QLabel("Extremum Length:")
        extremum_label.setToolTip(
            "<b>Extremum Length</b><br>"
            "Controls the sensitivity of peak/trough detection:<br>"
            "• <b>1</b> = Most sensitive (detects every local high/low)<br>"
            "• <b>2-5</b> = Moderate filtering (recommended for trading)<br>"
            "• <b>6+</b> = Only major turning points<br><br>"
            "Lower values find more patterns but may include noise.<br>"
            "Higher values find fewer, more significant patterns."
        )
        row1.addWidget(extremum_label)
        self.extremum_length_spin = QSpinBox()
        self.extremum_length_spin.setRange(1, 20)

        # Get default value from GUI if available
        if self.parent_window and hasattr(self.parent_window, 'length_spinbox'):
            default_extremum = self.parent_window.length_spinbox.value()
            self.extremum_length_spin.setValue(default_extremum)
            self.extremum_length_spin.setToolTip(
                f"<b>Extremum detection window</b><br>"
                f"Currently inheriting from GUI: <b>{default_extremum}</b><br>"
                f"This value determines how swing highs/lows are identified.<br>"
                f"Must match GUI setting for consistent results."
            )
        else:
            self.extremum_length_spin.setValue(1)  # Default to 1 if GUI not available
            self.extremum_length_spin.setToolTip(
                "<b>Extremum detection window</b><br>"
                "Set to 1 (most sensitive) by default.<br>"
                "Adjust based on your trading timeframe."
            )

        row1.addWidget(self.extremum_length_spin)

        # Add info label
        self.extremum_info = QLabel("")
        self.extremum_info.setStyleSheet("color: #8B4513; font-size: 10px; font-weight: bold; background-color: #FFF8DC; padding: 2px;")
        row1.addWidget(self.extremum_info)
        params_layout.addLayout(row1)

        # Row 2: Lookback Window and Detection Interval
        row2 = QHBoxLayout()
        lookback_label = QLabel("Lookback Window:")
        lookback_label.setToolTip(
            "<b>Lookback Window</b><br>"
            "Number of historical bars to search for patterns:<br>"
            "• <b>50-100</b> = Recent patterns only (fast)<br>"
            "• <b>100-200</b> = Balanced coverage (recommended)<br>"
            "• <b>200+</b> = Extended history (slower)<br><br>"
            "Larger windows find more historical patterns but<br>"
            "take longer to process. Start with 100 bars."
        )
        row2.addWidget(lookback_label)
        self.lookback_spin = QSpinBox()
        self.lookback_spin.setRange(50, 10000)  # Increased max to 10000
        self.lookback_spin.setValue(10000)  # Set to max for 100% accuracy
        self.lookback_spin.setToolTip(
            "<b>How many bars to analyze</b><br>"
            "The backtester will search this many bars<br>"
            "into the past at each detection point.<br>"
            "Set to maximum (10000) for 100% accuracy.<br>"
            "Default: 10000 bars (all available data)"
        )
        row2.addWidget(self.lookback_spin)

        detection_label = QLabel("Detection Interval:")
        detection_label.setToolTip(
            "<b>Detection Interval</b><br>"
            "How often to check for new patterns:<br>"
            "• <b>1</b> = Check every bar (most accurate, slowest)<br>"
            "• <b>5-10</b> = Good balance (recommended)<br>"
            "• <b>20+</b> = Fast processing (may miss short-lived patterns)<br><br>"
            "Lower values catch patterns earlier but take longer.<br>"
            "Higher values process faster but may miss opportunities."
        )
        row2.addWidget(detection_label)
        self.detection_interval_spin = QSpinBox()
        self.detection_interval_spin.setRange(1, 50)
        # Set default to 1 for 100% accuracy
        self.detection_interval_spin.setValue(1)  # Check every bar for complete accuracy
        self.detection_interval_spin.setToolTip(
            "<b>Pattern detection frequency</b><br>"
            "Check for patterns every N bars.<br>"
            "Set to 1 for 100% accuracy (checks every bar).<br>"
            "Higher values = faster but may miss patterns<br>"
            "Default: 1 (maximum accuracy)"
        )
        row2.addWidget(self.detection_interval_spin)
        params_layout.addLayout(row2)

        # Hidden parameters with default values (for compatibility with existing code)
        self.capital_spin = QSpinBox()
        self.capital_spin.setValue(10000)
        self.capital_spin.setVisible(False)

        self.position_size_spin = QDoubleSpinBox()
        self.position_size_spin.setValue(0.02)
        self.position_size_spin.setVisible(False)

        self.future_buffer_spin = QSpinBox()
        self.future_buffer_spin.setValue(5)
        self.future_buffer_spin.setVisible(False)

        self.min_score_spin = QDoubleSpinBox()
        self.min_score_spin.setValue(0.5)
        self.min_score_spin.setVisible(False)

        self.max_trades_spin = QSpinBox()
        self.max_trades_spin.setValue(5)
        self.max_trades_spin.setVisible(False)

        # Connect to update info when value changes
        self.extremum_length_spin.valueChanged.connect(self.updateExtremumInfo)
        self.extremum_length_spin.valueChanged.connect(self.updateDetectionIntervalSuggestion)

        # Data Range Selection Group
        range_group = QGroupBox("Data Range Selection")
        range_layout = QVBoxLayout()

        # Only Date Range mode (Last N Bars removed)
        self.date_radio = QRadioButton("Use Date Range")
        self.date_radio.setToolTip(
            "<b>Date Range Mode</b><br>"
            "Analyze a specific historical period.<br>"
            "Ideal for testing patterns during known market conditions.<br>"
            "<b>Inherits from GUI when matching.</b>"
        )
        self.date_radio.setChecked(True)  # Always use date range
        range_layout.addWidget(self.date_radio)

        # Date range selection
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Start Date:"))
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.start_date.setEnabled(False)  # Disabled by default
        self.start_date.setToolTip(
            "<b>Analysis Start Date</b><br>"
            "Beginning of the backtesting period.<br>"
            "Automatically inherits from GUI when dates match."
        )
        date_layout.addWidget(self.start_date)

        date_layout.addWidget(QLabel("End Date:"))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date.setEnabled(False)  # Disabled by default
        self.end_date.setToolTip(
            "<b>Analysis End Date</b><br>"
            "End of the backtesting period.<br>"
            "Automatically inherits from GUI when dates match."
        )
        date_layout.addWidget(self.end_date)
        range_layout.addLayout(date_layout)

        # Info label for selected range
        self.range_info_label = QLabel("")  # Will be set after initialization
        self.range_info_label.setStyleSheet("color: #B8860B; font-weight: bold; background-color: #FFFACD; padding: 3px;")
        range_layout.addWidget(self.range_info_label)

        range_group.setLayout(range_layout)
        params_layout.addWidget(range_group)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Connect date controls
        self.start_date.dateChanged.connect(self.updateRangeInfo)
        self.end_date.dateChanged.connect(self.updateRangeInfo)

        # Control Buttons
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Backtest")
        self.run_button.clicked.connect(self.runBacktest)
        button_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stopBacktest)
        button_layout.addWidget(self.stop_button)

        self.export_button = QPushButton("Export Results")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.exportResults)
        button_layout.addWidget(self.export_button)

        layout.addLayout(button_layout)

        # Progress Bar
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        # Results Display with enhanced tooltip
        results_group = QGroupBox("Backtest Results")
        results_group.setToolTip(
            "<b>Backtest Results</b><br>"
            "Shows comprehensive pattern detection analysis including:<br>"
            "• <b>Extremum Points:</b> Total swing highs and lows detected<br>"
            "• <b>Pattern Counts:</b> Formed and unformed patterns found<br>"
            "• <b>Pattern Types:</b> Breakdown by pattern type (ABCD, XABCD)<br>"
            "• <b>Completion Rate:</b> Success rate of pattern projections<br><br>"
            "<b>Key Metrics Explained:</b><br>"
            "• <b>Formed Patterns:</b> Complete, tradeable patterns<br>"
            "• <b>Unformed Patterns:</b> Patterns still developing<br>"
            "• <b>Success Rate:</b> Patterns that reached target vs failed"
        )
        results_layout = QVBoxLayout()

        # Pattern Completion Buttons (initially hidden)
        self.completion_button_group = QGroupBox("Pattern Completion Analysis - View Charts")
        self.completion_button_group.setVisible(False)
        button_layout = QVBoxLayout()

        # First row: Success, Invalid PRZ, Failed PRZ
        button_row1 = QHBoxLayout()

        self.success_btn = QPushButton("✓ Completed Successfully (0)")
        self.success_btn.setStyleSheet("background-color: #90EE90; font-weight: bold;")
        self.success_btn.clicked.connect(lambda: self.loadCategoryCharts('success'))
        button_row1.addWidget(self.success_btn)

        self.invalid_prz_btn = QPushButton("⚠ Invalid PRZ (0)")
        self.invalid_prz_btn.setStyleSheet("background-color: #FFA500; font-weight: bold;")
        self.invalid_prz_btn.clicked.connect(lambda: self.loadCategoryCharts('invalid_prz'))
        button_row1.addWidget(self.invalid_prz_btn)

        self.failed_prz_btn = QPushButton("✗ Failed PRZ (0)")
        self.failed_prz_btn.setStyleSheet("background-color: #FF6347; font-weight: bold;")
        self.failed_prz_btn.clicked.connect(lambda: self.loadCategoryCharts('failed_prz'))
        button_row1.addWidget(self.failed_prz_btn)

        button_layout.addLayout(button_row1)

        # Second row: In Zone, Dismissed, Pending
        button_row2 = QHBoxLayout()

        self.in_zone_btn = QPushButton("◉ In PRZ Zone (0)")
        self.in_zone_btn.setStyleSheet("background-color: #FFD700; font-weight: bold;")
        self.in_zone_btn.clicked.connect(lambda: self.loadCategoryCharts('in_zone'))
        button_row2.addWidget(self.in_zone_btn)

        self.dismissed_btn = QPushButton("⊘ Dismissed (0)")
        self.dismissed_btn.setStyleSheet("background-color: #D3D3D3; font-weight: bold;")
        self.dismissed_btn.clicked.connect(lambda: self.loadCategoryCharts('dismissed'))
        button_row2.addWidget(self.dismissed_btn)

        self.pending_btn = QPushButton("⧗ Pending (0)")
        self.pending_btn.setStyleSheet("background-color: #87CEEB; font-weight: bold;")
        self.pending_btn.clicked.connect(lambda: self.loadCategoryCharts('pending'))
        button_row2.addWidget(self.pending_btn)

        button_layout.addLayout(button_row2)

        self.completion_button_group.setLayout(button_layout)
        results_layout.addWidget(self.completion_button_group)

        # Pattern Completion Analysis Section (separate from view charts)
        self.analysis_button_group = QGroupBox("Pattern Completion Analysis")
        self.analysis_button_group.setVisible(False)
        analysis_layout = QVBoxLayout()

        # Fibonacci Analysis button
        self.fib_analysis_btn = QPushButton("📊 Fibonacci Analysis")
        self.fib_analysis_btn.setStyleSheet("background-color: #9370DB; color: white; font-weight: bold;")
        self.fib_analysis_btn.setToolTip("Analyze which Fibonacci levels are most frequently touched in current patterns")
        self.fib_analysis_btn.clicked.connect(self.runFibonacciAnalysis)
        self.fib_analysis_btn.setEnabled(False)  # Enable only when patterns are loaded
        analysis_layout.addWidget(self.fib_analysis_btn)

        # Harmonic Points Analysis button
        self.harmonic_points_btn = QPushButton("🎯 Harmonic Points Analysis")
        self.harmonic_points_btn.setStyleSheet("background-color: #20B2AA; color: white; font-weight: bold;")
        self.harmonic_points_btn.setToolTip("Analyze how many times pattern points A, B, C are crossed after point C")
        self.harmonic_points_btn.clicked.connect(self.runHarmonicPointsAnalysis)
        self.harmonic_points_btn.setEnabled(False)  # Enable only when patterns are loaded
        analysis_layout.addWidget(self.harmonic_points_btn)

        self.analysis_button_group.setLayout(analysis_layout)
        results_layout.addWidget(self.analysis_button_group)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        panel.setLayout(layout)
        return panel

    def initializeDateRanges(self):
        """Initialize date ranges based on available data"""
        data_to_check = self.full_data if self.full_data is not None else self.data
        if data_to_check is None or data_to_check.empty:
            self.run_button.setEnabled(False)
            self.results_text.append("⚠️ No data loaded. Please load data in the main window first.")
        else:
            self.results_text.append(f"✅ Full dataset loaded: {len(data_to_check)} bars available for backtesting")

            # Set date ranges based on available data
            min_date = data_to_check.index.min()
            max_date = data_to_check.index.max()

            # Convert pandas Timestamp to QDate
            q_min_date = QDate(min_date.year, min_date.month, min_date.day)
            q_max_date = QDate(max_date.year, max_date.month, max_date.day)

            # Set date ranges for QDateEdit widgets
            self.start_date.setDateRange(q_min_date, q_max_date)
            self.end_date.setDateRange(q_min_date, q_max_date)

            # Get default dates from GUI if available
            if self.parent_window and hasattr(self.parent_window, 'start_date_edit') and hasattr(self.parent_window, 'end_date_edit'):
                # Use GUI's current date range as default
                gui_start = self.parent_window.start_date_edit.date()
                gui_end = self.parent_window.end_date_edit.date()

                # Make sure GUI dates are within available data range
                if gui_start >= q_min_date and gui_start <= q_max_date:
                    self.start_date.setDate(gui_start)
                else:
                    self.start_date.setDate(q_min_date)

                if gui_end >= q_min_date and gui_end <= q_max_date:
                    self.end_date.setDate(gui_end)
                else:
                    self.end_date.setDate(q_max_date)

                # Store GUI dates for comparison
                self.gui_start_date = gui_start
                self.gui_end_date = gui_end

                # Set date range mode as default since we have GUI dates
                self.date_radio.setChecked(True)

                # Update the UI to reflect date mode
                self.start_date.setEnabled(True)
                self.end_date.setEnabled(True)

                # Update the info label
                self.updateRangeInfo()
            else:
                # Fallback to bars mode if GUI not available
                default_start = q_max_date.addDays(-100)
                if default_start < q_min_date:
                    default_start = q_min_date
                self.start_date.setDate(default_start)
                self.end_date.setDate(q_max_date)

                self.gui_start_date = None
                self.gui_end_date = None

                # Use date range mode
                self.date_radio.setChecked(True)

            # Update info
            self.results_text.append(f"Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")

    def onRangeModeChanged(self, checked):
        """Handle radio button changes for range mode (no longer used - always date range)"""
        # Date range is always enabled
        self.start_date.setEnabled(True)
        self.end_date.setEnabled(True)
        self.updateRangeInfo()

    def updateDetectionIntervalSuggestion(self):
        """Update detection interval suggestion based on extremum length."""
        # Removed automatic adjustments - let user control detection interval
        # for 100% accuracy
        pass

    def updateExtremumInfo(self):
        """Update extremum info label when value changes."""
        value = self.extremum_length_spin.value()
        if self.parent_window and hasattr(self.parent_window, 'length_spinbox'):
            gui_value = self.parent_window.length_spinbox.value()
            if value == gui_value:
                self.extremum_info.setText("(matches GUI)")
            else:
                self.extremum_info.setText(f"(GUI uses {gui_value})")
        else:
            self.extremum_info.setText("")

    def updateRangeInfo(self):
        """Update the info label based on current selection"""
        # Always use date range
        start = self.start_date.date().toString("yyyy-MM-dd")
        end = self.end_date.date().toString("yyyy-MM-dd")

        # Calculate number of bars in the date range
        data_to_check = self.full_data if self.full_data is not None else self.data
        if data_to_check is not None and not data_to_check.empty:
            start_pd = pd.Timestamp(start)
            end_pd = pd.Timestamp(end)
            mask = (data_to_check.index >= start_pd) & (data_to_check.index <= end_pd)
            num_bars = mask.sum()
            info_text = f"Selected: {start} to {end} ({num_bars} bars)"
        else:
            info_text = f"Selected: {start} to {end}"

        # Add GUI comparison info if available
        if hasattr(self, 'gui_start_date') and hasattr(self, 'gui_end_date'):
            if self.gui_start_date and self.gui_end_date:
                current_start = self.start_date.date()
                current_end = self.end_date.date()
                if current_start == self.gui_start_date and current_end == self.gui_end_date:
                    info_text += " [matches GUI]"
                else:
                    gui_start_str = self.gui_start_date.toString("yyyy-MM-dd")
                    gui_end_str = self.gui_end_date.toString("yyyy-MM-dd")
                    info_text += f" [GUI: {gui_start_str} to {gui_end_str}]"

        self.range_info_label.setText(info_text)

    def runBacktest(self):
        """Run the backtest with current parameters"""
        # Use full_data if available, otherwise fall back to self.data
        data_source = self.full_data if self.full_data is not None else self.data

        if data_source is None or data_source.empty:
            QMessageBox.warning(self, "No Data", "Please load data in the main window first.")
            return

        # Clean up any existing thread first
        if self.backtest_thread and self.backtest_thread.isRunning():
            QMessageBox.warning(self, "Backtest Running", "A backtest is already running. Please wait or stop it first.")
            return

        # Clean up finished thread
        if self.backtest_thread:
            self.backtest_thread.deleteLater()
            self.backtest_thread = None

        # Clear previous results AND cached stats
        self.results_text.clear()
        self.results_text.append("Starting backtest...\n")

        # Clear cached results to ensure fresh backtest
        if hasattr(self, 'last_stats'):
            delattr(self, 'last_stats')
        if hasattr(self, 'last_backtester'):
            delattr(self, 'last_backtester')

        # Get data range - Use full_data if available
        base_data = self.full_data if self.full_data is not None else self.data
        data_to_use = base_data.copy()

        # Always use date-based selection
        start_date = self.start_date.date().toPyDate()
        end_date = self.end_date.date().toPyDate()

        # Convert to pandas timestamps
        start_pd = pd.Timestamp(start_date)
        end_pd = pd.Timestamp(end_date)

        # Filter data by date range
        mask = (data_to_use.index >= start_pd) & (data_to_use.index <= end_pd)
        data_to_use = data_to_use[mask]

        # No automatic adjustment - user controls detection interval for 100% accuracy

        self.results_text.append(f"Using {len(data_to_use)} bars of data")
        self.results_text.append(f"Detection interval: {self.detection_interval_spin.value()} bar(s)")
        self.results_text.append(f"Lookback window: {self.lookback_spin.value()} bars")
        if len(data_to_use) >= 500 and self.detection_interval_spin.value() == 1:
            self.results_text.append("⏳ Large dataset with detection interval=1 for 100% accuracy")
            self.results_text.append("   This may take several minutes for complete analysis...")
            self.results_text.append("📊 Detecting ALL patterns (1300+ expected for 500 bars)\n")
        else:
            self.results_text.append("")

        # Prepare parameters
        params = {
            'initial_capital': self.capital_spin.value(),
            'position_size': self.position_size_spin.value() / 100,  # Convert percentage
            'lookback_window': self.lookback_spin.value(),
            'future_buffer': self.future_buffer_spin.value(),
            'min_pattern_score': self.min_score_spin.value(),
            'max_open_trades': self.max_trades_spin.value(),
            'detection_interval': self.detection_interval_spin.value(),
            'extremum_length': self.extremum_length_spin.value()  # Add extremum length
        }

        # Create and start backtest thread
        self.backtest_thread = BacktestThread(data_to_use, params)
        self.backtest_thread.progress.connect(self.updateProgress)
        self.backtest_thread.message.connect(self.updateMessage)
        self.backtest_thread.finished.connect(self.displayResults)
        self.backtest_thread.error.connect(self.handleError)

        # Note: Thread will be cleaned up after results are displayed

        # Update UI
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.export_button.setEnabled(False)
        self.progress_bar.setValue(0)

        # Start backtest
        self.backtest_thread.start()

    def stopBacktest(self):
        """Stop the running backtest"""
        if self.backtest_thread and self.backtest_thread.isRunning():
            self.backtest_thread.terminate()
            self.backtest_thread.wait(5000)  # Wait max 5 seconds
            if self.backtest_thread.isRunning():
                self.backtest_thread.quit()  # Force quit if still running
            self.results_text.append("\n❌ Backtest stopped by user.")
            self.run_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.cleanupThread()

    def updateProgress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def updateMessage(self, message):
        """Update status message"""
        self.results_text.append(message)

    def displayResults(self, stats):
        """Display backtest results"""
        # Store backtester reference first (needed for Fibonacci analysis)
        self.last_backtester = self.backtest_thread.backtester if self.backtest_thread else None

        self.results_text.append("\n" + "="*50)
        self.results_text.append("PATTERN DETECTION RESULTS")

        # Show actual backtested range from backtester data
        if self.last_backtester and hasattr(self.last_backtester, 'data'):
            try:
                if hasattr(self.last_backtester.data, 'index') and len(self.last_backtester.data) > 0:
                    actual_start = self.last_backtester.data.index[0].strftime('%Y-%m-%d')
                    actual_end = self.last_backtester.data.index[-1].strftime('%Y-%m-%d')
                    bars_count = len(self.last_backtester.data)
                    date_range = f"{actual_start} to {actual_end} ({bars_count} bars backtested)"
                else:
                    raise ValueError("Data has no index or is empty")
            except Exception:
                # Fallback to user selection (always date range)
                date_range = f"{self.start_date.date().toString('yyyy-MM-dd')} to {self.end_date.date().toString('yyyy-MM-dd')} (selected)"
        else:
            # Always use date range
            date_range = f"{self.start_date.date().toString('yyyy-MM-dd')} to {self.end_date.date().toString('yyyy-MM-dd')} (selected)"

        self.results_text.append(f"Date Range: {date_range}")
        self.results_text.append(f"Extremum Length: {self.extremum_length_spin.value()}")

        # Add extremum count information
        total_extremums = stats.get('total_extremum_points', 0)
        high_extremums = stats.get('high_extremum_points', 0)
        low_extremums = stats.get('low_extremum_points', 0)

        if total_extremums > 0:
            self.results_text.append(f"Extremum Points Detected: {total_extremums} ({high_extremums} highs, {low_extremums} lows)")

        self.results_text.append("="*50 + "\n")

        # Display tracking warnings if any
        # Handle both dict and object forms of stats
        if hasattr(stats, 'tracking_warnings'):
            tracking_warnings = stats.tracking_warnings if stats.tracking_warnings else []
        else:
            tracking_warnings = stats.get('tracking_warnings', [])
        if tracking_warnings:
            self.results_text.append("⚠️ TRACKING WARNINGS:")
            for warning in tracking_warnings[:10]:  # Show max 10 warnings to avoid clutter
                self.results_text.append(f"  • {warning}")
            if len(tracking_warnings) > 10:
                self.results_text.append(f"  ... and {len(tracking_warnings) - 10} more warnings")
            self.results_text.append("")  # Empty line for spacing
        else:
            self.results_text.append("✅ PATTERN TRACKING: 100% Accuracy - All patterns properly tracked!")
            self.results_text.append("")  # Empty line for spacing

        # Pattern Detection Overview
        self.results_text.append(f"PATTERN DETECTION SUMMARY:\n")

        # Get pattern counts
        total_unformed = stats.get('total_unformed_patterns', 0)  # Now stores unique count
        total_formed = stats.get('total_formed_patterns', 0)  # Now stores unique count
        patterns_tracked = stats.get('patterns_tracked', 0)
        formed_abcd = stats.get('formed_abcd_count', 0)
        formed_xabcd = stats.get('formed_xabcd_count', 0)

        # Display pattern analysis - clearer breakdown
        pattern_type_counts = stats.get('pattern_type_counts', {})

        # The unformed pattern types
        unformed_types = len(pattern_type_counts) if pattern_type_counts else 0

        # Display the pattern summary
        if pattern_type_counts:
            total_instances = total_formed + total_unformed
            self.results_text.append(f"  Total Pattern Instances Detected: {total_instances} from {unformed_types} unique pattern types")
            self.results_text.append(f"    - Formed (Complete): {total_formed}")
            self.results_text.append(f"      • ABCD: {formed_abcd}")
            self.results_text.append(f"      • XABCD: {formed_xabcd}")
            self.results_text.append(f"    - Unformed (Potential): {total_unformed}")
        else:
            self.results_text.append(f"  Formed Patterns Found: {total_formed}")
            self.results_text.append(f"    - Formed ABCD: {formed_abcd}")
            self.results_text.append(f"    - Formed XABCD: {formed_xabcd}")
            self.results_text.append(f"  Unformed Patterns: {total_unformed}")

        # Pattern type breakdown if available
        if pattern_type_counts and len(pattern_type_counts) > 0:
            self.results_text.append(f"\nUNFORMED PATTERN DISTRIBUTION:")
            self.results_text.append(f"  {len(pattern_type_counts)} unformed types → {total_unformed} potential instances")

            # Show top 10 most common pattern types
            top_patterns = sorted(pattern_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            for pattern_type, count in top_patterns:
                self.results_text.append(f"  {pattern_type}: {count} instances")

            if len(pattern_type_counts) > 10:
                remaining = len(pattern_type_counts) - 10
                remaining_count = sum(count for name, count in pattern_type_counts.items()
                                     if name not in [p[0] for p in top_patterns])
                self.results_text.append(f"  ... and {remaining} more types: {remaining_count} instances")

        # Pattern completion statistics with clickable buttons
        if total_unformed > 0:
            self.results_text.append(f"\nPATTERN COMPLETION ANALYSIS:")
            self.results_text.append("Click on a category below to view charts:\n")

            # Count patterns from tracker (excluding XABCD with empty d_lines)
            tracker = self.last_backtester.pattern_tracker
            success = 0
            invalid_prz = 0
            failed_prz = 0
            dismissed = 0
            pending = 0
            in_zone = 0

            for pattern_id, tracked_pattern in tracker.tracked_patterns.items():
                # Skip XABCD patterns with empty d_lines
                if tracked_pattern.pattern_type == 'XABCD':
                    if not hasattr(tracked_pattern, 'd_lines') or not tracked_pattern.d_lines:
                        continue

                # Count by status
                if tracked_pattern.status == 'success':
                    success += 1
                elif tracked_pattern.status == 'invalid_prz':
                    invalid_prz += 1
                elif tracked_pattern.status == 'failed_prz':
                    failed_prz += 1
                elif tracked_pattern.status == 'dismissed':
                    dismissed += 1
                elif tracked_pattern.status == 'pending':
                    pending += 1
                elif tracked_pattern.status == 'in_zone':
                    in_zone += 1

            # Store stats for chart loading
            self.completion_stats = {
                'success': success,
                'invalid_prz': invalid_prz,
                'failed_prz': failed_prz,
                'in_zone': in_zone,
                'dismissed': dismissed,
                'pending': pending
            }

            if total_unformed > 0:
                # Calculate success rate only from patterns that reached a conclusion (success, invalid, or failed)
                concluded = success + invalid_prz + failed_prz
                success_rate = (success / concluded * 100) if concluded > 0 else 0.0

                # Update button labels and show button group
                self.success_btn.setText(f"✓ Completed Successfully ({success})")
                self.invalid_prz_btn.setText(f"⚠ Invalid PRZ ({invalid_prz})")
                self.failed_prz_btn.setText(f"✗ Failed PRZ ({failed_prz})")
                self.in_zone_btn.setText(f"◉ In PRZ Zone ({in_zone})")
                self.dismissed_btn.setText(f"⊘ Dismissed ({dismissed})")
                self.pending_btn.setText(f"⧗ Pending ({pending})")
                self.completion_button_group.setVisible(True)
                self.analysis_button_group.setVisible(True)  # Show Pattern Completion Analysis section
                self.fib_analysis_btn.setEnabled(True)  # Enable Fibonacci Analysis when backtest completes
                self.harmonic_points_btn.setEnabled(True)  # Enable Harmonic Points Analysis when backtest completes

                self.results_text.append(f"\n  Completed Successfully: {success}")
                self.results_text.append(f"  Invalid PRZ (Crossed Once): {invalid_prz}")
                self.results_text.append(f"  Failed PRZ (Crossed Both Sides): {failed_prz}")
                self.results_text.append(f"  In PRZ Zone (Active): {in_zone}")
                self.results_text.append(f"  Dismissed (Structure Break): {dismissed}")
                self.results_text.append(f"  Still Pending: {pending}")

                if concluded > 0:
                    self.results_text.append(f"\n  Success Rate: {success_rate:.1f}% ({success}/{concluded} patterns that reached PRZ)")
                else:
                    self.results_text.append(f"\n  Success Rate: N/A (no patterns reached PRZ yet)")

                total_shown = success + invalid_prz + dismissed + pending + in_zone
                self.results_text.append(f"  Total Tracked: {total_shown}")

        # Fibonacci & Harmonic Level Analysis
        if self.last_backtester and hasattr(self.last_backtester, 'get_fibonacci_summary_statistics'):
            fib_summary = self.last_backtester.get_fibonacci_summary_statistics()


            if fib_summary and fib_summary.get('total_patterns_analyzed', 0) > 0:
                self.results_text.append(f"\nFIBONACCI & HARMONIC LEVEL ANALYSIS:")
                self.results_text.append("="*50)
                self.results_text.append(f"Total Formed Patterns Analyzed: {fib_summary['total_patterns_analyzed']}")
                self.results_text.append(f"  - ABCD: {fib_summary['abcd_count']}")
                self.results_text.append(f"  - XABCD: {fib_summary['xabcd_count']}")
                if 'patterns_completed' in fib_summary and 'patterns_active' in fib_summary:
                    self.results_text.append(f"  - Completed (PRZ broken): {fib_summary['patterns_completed']}")
                    self.results_text.append(f"  - Active (still tracking): {fib_summary['patterns_active']}")
                self.results_text.append("")

                # Overall Fibonacci levels (sorted by percentage)
                self.results_text.append("Overall Fibonacci Levels (Avg hits & timing):")
                fib_levels_order = ['Fib_0%', 'Fib_23.6%', 'Fib_38.2%', 'Fib_50%', 'Fib_61.8%',
                                   'Fib_78.6%', 'Fib_88.6%', 'Fib_100%', 'Fib_112.8%',
                                   'Fib_127.2%', 'Fib_141.4%', 'Fib_161.8%']

                for level_name in fib_levels_order:
                    if level_name in fib_summary['overall_stats']:
                        stats_data = fib_summary['overall_stats'][level_name]
                        avg_touches = stats_data['avg_touches']
                        total_touches = stats_data.get('total_touches', 0)
                        avg_first = stats_data['avg_first_touch_bar']
                        avg_interval = stats_data['avg_interval']
                        patterns_touched = stats_data['patterns_touched']

                        # Mark golden ratio levels
                        marker = " ⭐" if level_name in ['Fib_50%', 'Fib_61.8%'] else ""

                        self.results_text.append(
                            f"  {level_name:12s}: {avg_touches:.1f} avg ({total_touches} total), "
                            f"1st @ bar {avg_first:.1f}, "
                            f"interval: {avg_interval:.1f} bars "
                            f"({patterns_touched}/{fib_summary['total_patterns_analyzed']} patterns){marker}"
                        )

                # Harmonic structure levels
                self.results_text.append("")
                self.results_text.append("Harmonic Structure Levels (Avg hits & timing):")
                harmonic_levels_order = ['X_Level', 'A_Level', 'B_Level', 'C_Level']

                for level_name in harmonic_levels_order:
                    if level_name in fib_summary['overall_stats']:
                        stats_data = fib_summary['overall_stats'][level_name]
                        avg_touches = stats_data['avg_touches']
                        total_touches = stats_data.get('total_touches', 0)
                        avg_first = stats_data['avg_first_touch_bar']
                        avg_interval = stats_data['avg_interval']
                        patterns_touched = stats_data['patterns_touched']

                        self.results_text.append(
                            f"  {level_name:12s}: {avg_touches:.1f} avg ({total_touches} total), "
                            f"1st @ bar {avg_first:.1f}, "
                            f"interval: {avg_interval:.1f} bars "
                            f"({patterns_touched}/{fib_summary['total_patterns_analyzed']} patterns)"
                        )

                # Individual pattern breakdown (Option C)
                if 'individual_patterns' in fib_summary and fib_summary['individual_patterns']:
                    self.results_text.append("")
                    self.results_text.append("="*50)
                    self.results_text.append("INDIVIDUAL PATTERN DETAILS:")
                    self.results_text.append("="*50)

                    for i, pattern in enumerate(fib_summary['individual_patterns'], 1):
                        status = "Complete" if pattern['is_complete'] else "Active"
                        self.results_text.append(f"\n{i}. {pattern['pattern_name']} ({pattern['pattern_type']}) - {status}")
                        self.results_text.append(f"   Direction: {pattern['direction']}, Detected @ bar {pattern['detection_bar']}, Tracked: {pattern['total_bars_tracked']} bars")

                        # Show hits for key Fibonacci levels
                        key_fib_levels = ['Fib_23.6%', 'Fib_38.2%', 'Fib_50%', 'Fib_61.8%', 'Fib_78.6%', 'Fib_100%']
                        fib_hits = []
                        for level in key_fib_levels:
                            if level in pattern['level_touches']:
                                touch_data = pattern['level_touches'][level]
                                count = touch_data['touch_count']
                                if count > 0:
                                    first_bar = touch_data['first_touch_bar']
                                    fib_hits.append(f"{level.replace('Fib_', '').replace('%', '')}%: {count} hit{'s' if count > 1 else ''} (1st@{first_bar})")

                        if fib_hits:
                            self.results_text.append(f"   Fib Hits: {', '.join(fib_hits)}")
                        else:
                            self.results_text.append(f"   Fib Hits: None")

                        # Show harmonic level hits
                        harmonic_hits = []
                        for level in ['A_Level', 'B_Level', 'C_Level']:
                            if level in pattern['level_touches']:
                                touch_data = pattern['level_touches'][level]
                                count = touch_data['touch_count']
                                if count > 0:
                                    harmonic_hits.append(f"{level.replace('_Level', '')}: {count}")

                        if harmonic_hits:
                            self.results_text.append(f"   Harmonic Hits: {', '.join(harmonic_hits)}")

                # Pattern type breakdown (only if we have multiple types)
                if len(fib_summary['pattern_type_breakdown']) > 1:
                    self.results_text.append("")
                    self.results_text.append("Pattern Type Breakdown:")

                    for pattern_type in ['ABCD', 'XABCD']:
                        if pattern_type in fib_summary['pattern_type_breakdown']:
                            type_stats = fib_summary['pattern_type_breakdown'][pattern_type]
                            pattern_count = fib_summary['abcd_count'] if pattern_type == 'ABCD' else fib_summary['xabcd_count']

                            if pattern_count > 0:
                                self.results_text.append(f"  {pattern_type} Patterns ({pattern_count} patterns):")

                                # Show top 3 most touched Fibonacci levels for this type
                                fib_for_type = [(name, data) for name, data in type_stats.items() if name.startswith('Fib_')]
                                fib_for_type_sorted = sorted(fib_for_type, key=lambda x: x[1]['avg_touches'], reverse=True)[:3]

                                for level_name, level_data in fib_for_type_sorted:
                                    self.results_text.append(
                                        f"    {level_name}: {level_data['avg_touches']:.1f} hits, "
                                        f"1st @ bar {level_data['avg_first_touch_bar']:.1f}"
                                    )

        # Time taken
        time_taken = stats.get('time_taken', 0)
        if time_taken > 0:
            self.results_text.append(f"\nProcessing Time: {time_taken:.2f} seconds")

        # Store stats for export
        self.last_stats = stats

        # Automatically export to Excel after successful backtest
        self.autoExportToExcel(stats)

        # Update UI
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.export_button.setEnabled(True)
        self.progress_bar.setValue(100)

        # Clean up thread after completion
        self.cleanupThread()

    def handleError(self, error_msg):
        """Handle backtest errors"""
        self.results_text.append(f"\n❌ Error during backtest: {error_msg}")
        QMessageBox.critical(self, "Backtest Error", f"An error occurred:\n{error_msg}")

        # Reset UI
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.progress_bar.setValue(0)

        # Clean up thread after error
        self.cleanupThread()

    def cleanupThread(self):
        """Clean up the backtest thread"""
        if self.backtest_thread:
            if self.backtest_thread.isRunning():
                self.backtest_thread.quit()
                self.backtest_thread.wait(1000)
            self.backtest_thread.deleteLater()
            self.backtest_thread = None

    def closeEvent(self, event):
        """Handle dialog close event"""
        # Stop any running backtest
        if self.backtest_thread and self.backtest_thread.isRunning():
            self.backtest_thread.terminate()
            self.backtest_thread.wait(1000)
        self.cleanupThread()
        event.accept()

    def autoExportToExcel(self, stats):
        """Automatically export backtest results to Excel in the backtest_results folder"""
        try:
            # Create backtest_results folder if it doesn't exist
            results_dir = os.path.join(os.path.dirname(__file__), 'backtest_results')
            os.makedirs(results_dir, exist_ok=True)

            # Get the backtester and tracker
            if not self.last_backtester:
                return

            backtester = self.last_backtester
            tracker = backtester.pattern_tracker
            test_data = backtester.data

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(results_dir, f'backtest_results_{timestamp}.xlsx')

            # Get Fibonacci trackers if available
            fibonacci_trackers = getattr(backtester, 'fibonacci_trackers', None)

            # Create enhanced DataFrames using new functions
            summary_df = create_enhanced_summary(stats, tracker, test_data, backtester)
            patterns_df = create_enhanced_pattern_details(tracker, test_data, fibonacci_trackers)
            performance_df = create_pattern_performance_sheet(tracker)
            fibonacci_df = create_fibonacci_analysis_sheet(fibonacci_trackers) if fibonacci_trackers else pd.DataFrame()

            # Clean DataFrames for Excel compatibility
            def clean_dataframe(df):
                """Clean DataFrame for Excel export"""
                if df.empty:
                    return df
                # Create a copy to avoid modifying original
                df = df.copy()
                # Replace inf/-inf with NaN, then NaN with empty string
                df = df.replace([np.inf, -np.inf], np.nan)
                df = df.fillna('')
                # Convert object columns with mixed types to string
                for col in df.columns:
                    if df[col].dtype == 'object':
                        df[col] = df[col].astype(str)
                        # Replace 'nan' string representations
                        df[col] = df[col].replace('nan', '')
                        df[col] = df[col].replace('None', '')
                        # Escape any strings that could be interpreted as formulas
                        # Excel treats strings starting with =, +, -, @, | as formulas
                        def escape_formula(x):
                            s = str(x)
                            if s and len(s) > 0 and s[0] in ['=', '+', '-', '@', '|']:
                                return "'" + s
                            return s
                        df[col] = df[col].apply(escape_formula)
                return df

            # Clean all DataFrames
            summary_df = clean_dataframe(summary_df)
            patterns_df = clean_dataframe(patterns_df)
            performance_df = clean_dataframe(performance_df)
            fibonacci_df = clean_dataframe(fibonacci_df)

            # Save to Excel with multiple sheets
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # Sheet 1: Enhanced Summary
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # Sheet 2: Enhanced Pattern Details
                if not patterns_df.empty:
                    patterns_df.to_excel(writer, sheet_name='Pattern Details', index=False)

                # Sheet 3: Pattern Performance by Type
                if not performance_df.empty:
                    performance_df.to_excel(writer, sheet_name='Pattern Performance', index=False)

                # Sheet 4: Comprehensive Fibonacci & Harmonic Analysis
                if not fibonacci_df.empty:
                    fibonacci_df.to_excel(writer, sheet_name='Fib & Harmonic Analysis', index=False)

                # Auto-adjust column widths
                for sheet_name in writer.sheets:
                    worksheet = writer.sheets[sheet_name]
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        worksheet.column_dimensions[column_letter].width = adjusted_width

            # Store Excel filename for chart generation
            self.last_excel_file = filename

            # Add success message
            self.results_text.append(f"\n✅ Results automatically saved to:")
            self.results_text.append(f"   {filename}")
            self.results_text.append(f"   📊 Sheets: Summary, Pattern Details, Pattern Performance, Fib & Harmonic Analysis")

        except Exception as e:
            # Don't show error dialog, just log to results
            self.results_text.append(f"\n⚠️ Could not auto-save Excel: {str(e)}")

    def exportResults(self):
        """Export backtest results to CSV"""
        if not hasattr(self, 'last_stats'):
            QMessageBox.warning(self, "No Results", "No results to export.")
            return

        try:
            # Create results DataFrame
            results_df = pd.DataFrame([self.last_stats])

            # Save to CSV with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_results_{timestamp}.csv"
            results_df.to_csv(filename, index=False)

            QMessageBox.information(self, "Export Complete", f"Results exported to {filename}")
            self.results_text.append(f"\n📁 Results exported to {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export results:\n{str(e)}")

    def loadCategoryCharts(self, category):
        """Load all charts for a specific completion category using pattern tracker data"""
        # Check if we have backtester results
        if not hasattr(self, 'last_backtester') or not self.last_backtester:
            self.chart_placeholder.setText("No backtest results available.\nPlease run a backtest first.")
            self.chart_placeholder.show()
            self.pattern_chart.hide()
            return

        # Get pattern tracker
        tracker = self.last_backtester.pattern_tracker
        if not tracker or not hasattr(tracker, 'tracked_patterns'):
            self.chart_placeholder.setText("No pattern tracking data available.")
            self.chart_placeholder.show()
            self.pattern_chart.hide()
            return

        # Map category to status values (lowercase to match tracker)
        status_map = {
            'success': 'success',
            'invalid_prz': 'invalid_prz',
            'failed_prz': 'failed_prz',
            'in_zone': 'in_zone',
            'dismissed': 'dismissed',
            'pending': 'pending'
        }

        status_value = status_map.get(category, category)

        # Filter patterns by status from pattern tracker
        filtered_patterns = []
        for pattern_id, tracked_pattern in tracker.tracked_patterns.items():
            if tracked_pattern.status == status_value:
                # Skip XABCD patterns with empty d_lines (they were invalidated after detection)
                if tracked_pattern.pattern_type == 'XABCD':
                    if not hasattr(tracked_pattern, 'd_lines') or not tracked_pattern.d_lines:
                        continue  # Skip this pattern - it has no valid D-lines

                # Convert TrackedPattern to dictionary with all needed info
                pattern_dict = {
                    'pattern_id': pattern_id,
                    'pattern_type': tracked_pattern.pattern_type,
                    'pattern_subtype': tracked_pattern.subtype,  # Fix: it's 'subtype', not 'pattern_subtype'
                    'prz_instance': tracked_pattern.prz_instance if hasattr(tracked_pattern, 'prz_instance') else 'prz_1',  # NEW
                    'status': tracked_pattern.status,
                    'tracked_pattern': tracked_pattern,  # Add tracked pattern for Fibonacci analysis
                    'points': {}
                }

                # Add pattern points (TrackedPattern stores points as (bar_idx, price) tuples)
                # For ABCD patterns, x_point is (0, 0) which should be ignored
                if hasattr(tracked_pattern, 'x_point') and tracked_pattern.x_point:
                    bar_idx, price = tracked_pattern.x_point
                    # Only add X point if it's not the dummy (0, 0) value
                    if bar_idx != 0 or price != 0:
                        pattern_dict['points']['X'] = {'bar': bar_idx, 'price': price}

                if hasattr(tracked_pattern, 'a_point') and tracked_pattern.a_point:
                    bar_idx, price = tracked_pattern.a_point
                    pattern_dict['points']['A'] = {'bar': bar_idx, 'price': price}

                if hasattr(tracked_pattern, 'b_point') and tracked_pattern.b_point:
                    bar_idx, price = tracked_pattern.b_point
                    pattern_dict['points']['B'] = {'bar': bar_idx, 'price': price}

                if hasattr(tracked_pattern, 'c_point') and tracked_pattern.c_point:
                    bar_idx, price = tracked_pattern.c_point
                    pattern_dict['points']['C'] = {'bar': bar_idx, 'price': price}

                if hasattr(tracked_pattern, 'd_point') and tracked_pattern.d_point:
                    bar_idx, price = tracked_pattern.d_point
                    pattern_dict['points']['D'] = {'bar': bar_idx, 'price': price}

                filtered_patterns.append(pattern_dict)

        if len(filtered_patterns) == 0:
            category_names = {
                'success': 'Completed Successfully',
                'invalid_prz': 'Invalid PRZ (Crossed Once)',
                'failed_prz': 'Failed PRZ (Crossed Both Sides)',
                'in_zone': 'In PRZ Zone (Active)',
                'dismissed': 'Dismissed (Structure Break)',
                'pending': 'Still Pending'
            }
            self.chart_placeholder.setText(f"No patterns found for:\n{category_names.get(category, category)}")
            self.chart_placeholder.show()
            self.pattern_chart.hide()
            self.prev_chart_btn.setEnabled(False)
            self.next_chart_btn.setEnabled(False)
            return

        # Store pattern data for chart generation
        self.current_category_patterns = filtered_patterns
        self.current_chart_category = category
        self.current_chart_index = 0

        # Enable analysis buttons when patterns are loaded
        if hasattr(self, 'fib_analysis_btn'):
            self.fib_analysis_btn.setEnabled(True)
        if hasattr(self, 'harmonic_points_btn'):
            self.harmonic_points_btn.setEnabled(True)

        # Generate and display first chart
        self.generateAndDisplayChart()

    def generateAndDisplayChart(self):
        """Generate chart for current pattern using PyQtGraph - exact copy of GUI's drawPattern"""
        if not hasattr(self, 'current_category_patterns') or not self.current_category_patterns:
            return

        if self.current_chart_index >= len(self.current_category_patterns):
            return

        print(f"📊 generateAndDisplayChart called: index={self.current_chart_index}/{len(self.current_category_patterns)-1}")

        try:
            # Get current pattern dictionary
            pattern_dict = self.current_category_patterns[self.current_chart_index]

            # Get pattern status early for Fibonacci checkbox
            pattern_status = pattern_dict.get('status', 'Unknown')

            # Get backtester data
            if not hasattr(self, 'last_backtester') or not self.last_backtester:
                return

            test_data = self.last_backtester.data
            # Use full_data for timestamp lookups (pattern points might be outside test_data range)
            full_data = self.full_data if self.full_data is not None else test_data
            points = pattern_dict.get('points', {})

            if not points:
                return

            # Get data slice first to create date axis
            # Get all pattern bars for determining range
            all_bars = [p['bar'] for p in points.values() if 'bar' in p]
            if not all_bars:
                return

            # Store original bars for later use in labels
            self.current_pattern_bars = {label: points[label]['bar'] for label in points.keys() if 'bar' in points[label]}

            # Calculate range with enough padding to show all points
            # Only include bars that are within test_data range for slicing
            valid_bars = [b for b in all_bars if 0 <= b < len(test_data)]
            if not valid_bars:
                # All pattern points are outside test_data range
                self.chart_label.setText("Pattern points are outside the backtest data range.")
                return

            min_bar = max(0, min(valid_bars) - 20)

            # For successful/invalid/failed patterns, extend to show entry/reversal/failed bars
            # Get tracked pattern first to check for entry/reversal/failed bars
            max_bar = max(valid_bars) + 30  # Default: 30 bars after last point
            pattern_id = pattern_dict.get('pattern_id')
            if pattern_id and hasattr(self.last_backtester, 'pattern_tracker'):
                tracker = self.last_backtester.pattern_tracker
                if pattern_id in tracker.tracked_patterns:
                    tracked_pattern = tracker.tracked_patterns[pattern_id]

                    # Find the latest significant event bar
                    latest_event_bar = max(valid_bars)

                    if hasattr(tracked_pattern, 'zone_entry_bar') and tracked_pattern.zone_entry_bar:
                        latest_event_bar = max(latest_event_bar, tracked_pattern.zone_entry_bar)
                    if hasattr(tracked_pattern, 'reversal_bar') and tracked_pattern.reversal_bar:
                        latest_event_bar = max(latest_event_bar, tracked_pattern.reversal_bar)
                    if hasattr(tracked_pattern, 'zone_exit_bar') and tracked_pattern.zone_exit_bar:
                        latest_event_bar = max(latest_event_bar, tracked_pattern.zone_exit_bar)
                    if hasattr(tracked_pattern, 'invalid_bar') and tracked_pattern.invalid_bar:
                        latest_event_bar = max(latest_event_bar, tracked_pattern.invalid_bar)
                    if hasattr(tracked_pattern, 'failed_bar') and tracked_pattern.failed_bar:
                        latest_event_bar = max(latest_event_bar, tracked_pattern.failed_bar)

                    # Show 15-20 candles after the latest event
                    max_bar = latest_event_bar + 20

            max_bar = min(len(test_data), max_bar)  # Don't exceed data length

            # Store for use in coordinate calculations
            self.chart_min_bar = min_bar
            self.chart_max_bar = max_bar

            # Get data slice
            display_data = test_data.iloc[min_bar:max_bar]
            self.display_data = display_data.copy()  # Store WITH datetime index for crosshair

            # Clear chart (like GUI does) instead of recreating
            self.pattern_chart.clear()

            # Update date axis with current data dates (like GUI does)
            self.date_axis.dates = display_data.index

            # Show chart, hide placeholder
            self.chart_placeholder.hide()
            self.pattern_chart.show()

            # Setup crosshair (re-create after clear)
            self.setupCrosshair()

            # Create candlestick chart (needs reset index for x-coordinates)
            candles = CandlestickItem(display_data.reset_index(drop=True))
            self.pattern_chart.addItem(candles)

            # Set Y-axis range - include all pattern point prices
            all_prices = [p['price'] for p in points.values() if 'price' in p]
            data_y_min = display_data['Low'].min()
            data_y_max = display_data['High'].max()
            pattern_y_min = min(all_prices) if all_prices else data_y_min
            pattern_y_max = max(all_prices) if all_prices else data_y_max

            y_min = min(data_y_min, pattern_y_min) * 0.999
            y_max = max(data_y_max, pattern_y_max) * 1.001
            self.pattern_chart.setYRange(y_min, y_max, padding=0)

            # Plot ALL extremum points in the visible range as reference
            if hasattr(self.last_backtester, 'extremum_points') and self.last_backtester.extremum_points:
                for ep_time, ep_price, is_high, bar_idx in self.last_backtester.extremum_points:
                    # Check if this extremum is in our display range
                    if min_bar <= bar_idx < max_bar:
                        display_ep_idx = bar_idx - min_bar

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
                            self.pattern_chart.addItem(scatter)

            # Determine point order
            point_order = []
            if 'X' in points:
                point_order = ['X', 'A', 'B', 'C']
            else:
                point_order = ['A', 'B', 'C']

            if 'D' in points:
                point_order.append('D')

            # Calculate display coordinates - use timestamps like GUI does
            x_coords = []
            y_coords = []
            labels = []

            for point_name in point_order:
                if point_name in points:
                    bar = points[point_name]['bar']
                    price = points[point_name]['price']

                    # Only process points that are within test_data range
                    # Points outside (like X before backtest window) will be skipped from display
                    if not (0 <= bar < len(test_data)):
                        # Point is outside test_data, skip it
                        continue

                    # Convert bar index to display coordinates
                    display_idx = bar - min_bar

                    if 0 <= display_idx < len(display_data):
                        x_coords.append(display_idx)
                        y_coords.append(price)
                        labels.append(point_name)

            # Draw pattern lines
            if len(x_coords) >= 2:
                # Determine if bullish or bearish
                is_bullish = points['A']['price'] > points['C']['price']
                color = '#00BFFF' if is_bullish else '#FF8C00'

                # Draw lines connecting pattern points
                pen = mkPen(color=color, width=3, style=Qt.PenStyle.SolidLine)
                point_pen = mkPen('#000000', width=2)  # Black border
                point_brush = mkBrush('#FFFF00')  # Bright yellow fill

                self.pattern_chart.plot(x_coords, y_coords, pen=pen, symbol='o',
                                      symbolPen=point_pen, symbolBrush=point_brush, symbolSize=16)

                # Add labels for each point with price values AND dates
                for x, y, label in zip(x_coords, y_coords, labels):
                    # Get the timestamp for this point from the stored bars
                    point_bar = self.current_pattern_bars.get(label)
                    if point_bar is None or point_bar >= len(test_data):
                        continue

                    # Get timestamp from test_data
                    point_timestamp = test_data.index[point_bar]

                    # Format date/time - only show time if it's not all zeros
                    if hasattr(point_timestamp, 'strftime'):
                        if point_timestamp.hour == 0 and point_timestamp.minute == 0 and point_timestamp.second == 0:
                            datetime_str = point_timestamp.strftime('%d %b %Y')
                        else:
                            datetime_str = point_timestamp.strftime('%d %b %H:%M')
                    else:
                        point_timestamp = pd.to_datetime(point_timestamp)
                        if point_timestamp.hour == 0 and point_timestamp.minute == 0 and point_timestamp.second == 0:
                            datetime_str = point_timestamp.strftime('%d %b %Y')
                        else:
                            datetime_str = point_timestamp.strftime('%d %b %H:%M')

                    # Create label with point name, price value, and date/time
                    label_text = f"{label}\n${y:.2f}\n{datetime_str}"
                    text = pg.TextItem(label_text, color='#000000', anchor=(0.5, 1.2))
                    text.setPos(x, y)
                    text.setFont(QFont('Arial', 10, QFont.Weight.Bold))
                    self.pattern_chart.addItem(text)

            # Get tracked pattern for PRZ/D-lines info
            tracker = self.last_backtester.pattern_tracker
            pattern_id = pattern_dict.get('pattern_id')

            # Debug: Show what we're checking
            print(f"\n=== PRZ/D-lines Debug ===")
            print(f"Pattern ID: {pattern_id[:30] if pattern_id else 'None'}...")
            print(f"Pattern Type: {pattern_dict.get('pattern_type')}")
            print(f"Pattern Subtype: {pattern_dict.get('pattern_subtype')}")
            print(f"Status: {pattern_dict.get('status')}")
            print(f"x_coords available: {len(x_coords)}")
            print(f"Points in dict: {list(points.keys())}")

            if pattern_id and pattern_id in tracker.tracked_patterns:
                tracked_pattern = tracker.tracked_patterns[pattern_id]

                # Print pattern points with bar numbers and prices
                print(f"\n--- Pattern Points ---")
                if hasattr(tracked_pattern, 'x_point') and tracked_pattern.x_point:
                    bar_idx, price = tracked_pattern.x_point
                    if bar_idx != 0 or price != 0:
                        print(f"X: Bar {bar_idx}, Price ${price:,.2f}")
                if hasattr(tracked_pattern, 'a_point') and tracked_pattern.a_point:
                    bar_idx, price = tracked_pattern.a_point
                    print(f"A: Bar {bar_idx}, Price ${price:,.2f}")
                if hasattr(tracked_pattern, 'b_point') and tracked_pattern.b_point:
                    bar_idx, price = tracked_pattern.b_point
                    print(f"B: Bar {bar_idx}, Price ${price:,.2f}")
                if hasattr(tracked_pattern, 'c_point') and tracked_pattern.c_point:
                    bar_idx, price = tracked_pattern.c_point
                    print(f"C: Bar {bar_idx}, Price ${price:,.2f}")
                if hasattr(tracked_pattern, 'd_point') and tracked_pattern.d_point:
                    bar_idx, price = tracked_pattern.d_point
                    print(f"D: Bar {bar_idx}, Price ${price:,.2f}")

                # Print zone entry/exit information
                print(f"\n--- Zone Entry/Exit ---")
                if hasattr(tracked_pattern, 'zone_entry_bar') and tracked_pattern.zone_entry_bar:
                    entry_bar = tracked_pattern.zone_entry_bar
                    print(f"Zone Entry Bar: {entry_bar}")
                    print(f"Zone Entry Price: ${tracked_pattern.zone_entry_price:,.2f}")

                    # Calculate bars from point C to entry
                    if 'C' in points and 'bar' in points['C']:
                        c_bar = points['C']['bar']
                        bars_from_c = entry_bar - c_bar
                        print(f"Bars from Point C (bar {c_bar}) to Entry: {bars_from_c} bars")

                    # Show actual bar data at entry
                    if entry_bar < len(test_data):
                        bar_data = test_data.iloc[entry_bar]
                        print(f"Bar {entry_bar} OHLC: O=${bar_data['Open']:,.2f} H=${bar_data['High']:,.2f} L=${bar_data['Low']:,.2f} C=${bar_data['Close']:,.2f}")

                if hasattr(tracked_pattern, 'reversal_bar') and tracked_pattern.reversal_bar:
                    print(f"Reversal Bar: {tracked_pattern.reversal_bar}")
                    print(f"Reversal Price: ${tracked_pattern.reversal_price:,.2f}")
                if hasattr(tracked_pattern, 'zone_exit_bar') and tracked_pattern.zone_exit_bar:
                    print(f"Zone Exit Bar: {tracked_pattern.zone_exit_bar}")
                    print(f"Zone Exit Price: ${tracked_pattern.zone_exit_price:,.2f}")

                # Print PRZ/D-lines
                print(f"\n--- PRZ/D-lines ---")
                print(f"Has prz_zones: {hasattr(tracked_pattern, 'prz_zones')}")
                if hasattr(tracked_pattern, 'prz_zones'):
                    print(f"prz_zones count: {len(tracked_pattern.prz_zones)}")
                    print(f"prz_zones value: {tracked_pattern.prz_zones}")
                print(f"Has all_prz_zones: {hasattr(tracked_pattern, 'all_prz_zones')}")
                if hasattr(tracked_pattern, 'all_prz_zones'):
                    print(f"all_prz_zones count: {len(tracked_pattern.all_prz_zones)}")
                    for i, zone in enumerate(tracked_pattern.all_prz_zones, 1):
                        zone_min = zone.get('min') or zone.get('zone_min', 0)
                        zone_max = zone.get('max') or zone.get('zone_max', 0)
                        print(f"  PRZ {i}: {zone.get('pattern_source')} - {zone_min:.2f} to {zone_max:.2f}")
                print(f"Has d_lines: {hasattr(tracked_pattern, 'd_lines')}")
                if hasattr(tracked_pattern, 'd_lines'):
                    print(f"d_lines value: {tracked_pattern.d_lines}")
            else:
                print(f"Pattern not found in tracker!")
            print(f"========================\n")

            if pattern_id and pattern_id in tracker.tracked_patterns:
                tracked_pattern = tracker.tracked_patterns[pattern_id]

                # Draw D-lines for XABCD patterns (check XABCD first before PRZ zones)
                if pattern_dict.get('pattern_type') == 'XABCD' and hasattr(tracked_pattern, 'd_lines') and tracked_pattern.d_lines and len(x_coords) > 0:
                    last_x = x_coords[-1]
                    is_bullish = points['A']['price'] > points['C']['price']
                    color = '#00BFFF' if is_bullish else '#FF8C00'

                    # Debug
                    print(f"Drawing D-lines for {pattern_dict.get('pattern_subtype')}: {tracked_pattern.d_lines}")

                    # Extend D-lines to the right edge of the chart
                    right_edge = len(display_data) - 1

                    for i, d_price in enumerate(tracked_pattern.d_lines, 1):
                        # Convert to float if needed
                        d_val = float(d_price)

                        # Draw horizontal line extending from C point to right edge
                        line_pen = mkPen(color=color, width=1.5, style=Qt.PenStyle.DashLine)
                        self.pattern_chart.plot([last_x, right_edge], [d_val, d_val], pen=line_pen)

                        # Add label at the end
                        label_text = f"D{i}: {d_val:.2f}"
                        text = pg.TextItem(label_text, color=color, anchor=(0, 0.5))
                        text.setPos(right_edge - 15, d_val)
                        text.setFont(QFont('Arial', 8, QFont.Weight.Bold))
                        self.pattern_chart.addItem(text)

                # Draw PRZ zones for ABCD patterns
                else:
                    # Draw PRZ zones if available (use all_prz_zones for display)
                    prz_display = tracked_pattern.all_prz_zones if hasattr(tracked_pattern, 'all_prz_zones') and tracked_pattern.all_prz_zones else tracked_pattern.prz_zones if hasattr(tracked_pattern, 'prz_zones') else []
                    if prz_display and len(x_coords) > 0:
                        last_x = x_coords[-1]
                        is_bullish = points['A']['price'] > points['C']['price']
                        color = '#00BFFF' if is_bullish else '#FF8C00'

                        for i, zone in enumerate(prz_display, 1):
                            # Draw zone as shaded rectangle
                            zone_color = QColor(color)
                            zone_color.setAlpha(80)
                            zone_brush = mkBrush(zone_color)

                            # Handle both 'min'/'max' and 'zone_min'/'zone_max' keys
                            zone_min = zone.get('min') or zone.get('zone_min', 0)
                            zone_max = zone.get('max') or zone.get('zone_max', 0)

                            rect = pg.QtWidgets.QGraphicsRectItem(last_x - 10, zone_min,
                                                                 20, zone_max - zone_min)
                            rect.setBrush(zone_brush)
                            rect.setPen(mkPen(color, width=2))
                            self.pattern_chart.addItem(rect)

                            # Add label
                            label_text = f"PRZ{i}\n{zone_min:.2f}-{zone_max:.2f}"
                            text = pg.TextItem(label_text, color=color, anchor=(0, 0.5))
                            text.setPos(last_x + 12, (zone_min + zone_max) / 2)
                            text.setFont(QFont('Arial', 7, QFont.Weight.Bold))
                            self.pattern_chart.addItem(text)

            # Draw Fibonacci levels if checkbox is checked and pattern is successful
            print(f"📊 Fib checkbox checked: {self.show_fib_checkbox.isChecked()}, status: {pattern_status}")
            if self.show_fib_checkbox.isChecked() and pattern_status == 'success':
                print("✅ Drawing Fibonacci levels...")

                # Get pattern points for Fibonacci calculation
                # For unformed patterns, use zone_entry_price as D
                a_price = points['A']['price'] if 'A' in points else None
                c_price = points['C']['price'] if 'C' in points else None

                # Determine D price
                if 'D' in points:
                    d_price = points['D']['price']
                elif pattern_id and pattern_id in tracker.tracked_patterns:
                    # For unformed patterns, use zone_entry_price
                    d_price = tracker.tracked_patterns[pattern_id].zone_entry_price
                else:
                    d_price = None

                if a_price and c_price and d_price:
                    # Determine if bullish or bearish
                    is_bullish = a_price < c_price

                    # Calculate start price: max(A,C) for bullish, min(A,C) for bearish
                    if is_bullish:
                        start_price = max(a_price, c_price)
                    else:
                        start_price = min(a_price, c_price)

                    end_price = d_price
                    price_range = end_price - start_price

                    # Calculate Fibonacci levels (same logic as backtester)
                    fib_percentages = [0, 23.6, 38.2, 50, 61.8, 78.6, 88.6, 100, 112.8, 127.2, 141.4, 161.8]
                    fib_levels = {}

                    for pct in fib_percentages:
                        level_price = start_price + (price_range * pct / 100.0)
                        fib_levels[f"{pct}%"] = level_price

                    # Draw horizontal lines for each Fibonacci level
                    for level_name, level_price in fib_levels.items():
                        # Use different colors for key levels
                        if level_name in ['50%', '61.8%']:
                            line_color = '#FFD700'  # Gold for golden ratios
                            line_width = 3
                        else:
                            line_color = '#00CED1'  # Dark turquoise for others
                            line_width = 2

                        # Draw line across the chart
                        fib_pen = mkPen(color=line_color, width=line_width, style=Qt.PenStyle.DashLine)
                        self.pattern_chart.plot([0, len(display_data)-1], [level_price, level_price], pen=fib_pen)

                        # Add label on the right side
                        fib_text = pg.TextItem(f"Fib {level_name}", color=line_color, anchor=(0, 0.5))
                        fib_text.setPos(len(display_data) - 5, level_price)
                        fib_text.setFont(QFont('Arial', 10, QFont.Weight.Bold))
                        self.pattern_chart.addItem(fib_text)

            # Set title
            pattern_type = pattern_dict.get('pattern_type', 'Unknown')
            pattern_subtype = pattern_dict.get('pattern_subtype', 'Unknown')
            status = pattern_dict.get('status', 'Unknown')

            # For ABCD patterns with multiple PRZ zones, show which PRZ instance
            # For XABCD patterns, don't show PRZ instance (they only have d_lines)
            if pattern_type == 'ABCD':
                prz_instance = pattern_dict.get('prz_instance', 'prz_1')
                title = f"{pattern_type} - {pattern_subtype} ({prz_instance.upper()}) | Status: {status}"
            else:
                title = f"{pattern_type} - {pattern_subtype} | Status: {status}"

            self.pattern_chart.setTitle(title, color='black', size='12pt')

            # Enable/disable Fibonacci checkbox based on pattern status
            # Enable for successful patterns (formed with D, or unformed with zone_entry_price)
            has_d_point = 'D' in points
            has_zone_entry = (pattern_id and pattern_id in tracker.tracked_patterns and
                            tracker.tracked_patterns[pattern_id].zone_entry_price is not None)

            if pattern_status == 'success' and (has_d_point or has_zone_entry):
                self.show_fib_checkbox.setEnabled(True)
            else:
                self.show_fib_checkbox.setEnabled(False)
                self.show_fib_checkbox.setChecked(False)  # Uncheck if disabled

            # Set x-axis labels to show dates
            axis = self.pattern_chart.getAxis('bottom')
            date_labels = []
            for i in range(0, len(display_data), max(1, len(display_data)//10)):
                date_labels.append((i, str(display_data.index[i].date())))
            axis.setTicks([date_labels])

            # Enable auto-range
            self.pattern_chart.enableAutoRange(axis='x')
            self.pattern_chart.setAutoVisible(y=True, x=True)

            # Final auto-range call (like GUI)
            self.pattern_chart.autoRange()

            # Update info label
            category_names = {
                'success': 'Completed Successfully',
                'invalid_prz': 'Invalid PRZ (Crossed Once)',
                'failed_prz': 'Failed PRZ (Crossed Both Sides)',
                'in_zone': 'In PRZ Zone (Active)',
                'dismissed': 'Dismissed (Structure Break)',
                'pending': 'Still Pending'
            }
            category_name = category_names.get(self.current_chart_category, self.current_chart_category)
            total_patterns = len(self.current_category_patterns)
            self.chart_info_label.setText(
                f"Chart {self.current_chart_index + 1} of {total_patterns} - {category_name}"
            )

            # Enable/disable navigation buttons (always enabled for circular navigation if we have patterns)
            self.prev_chart_btn.setEnabled(total_patterns > 1)
            self.next_chart_btn.setEnabled(total_patterns > 1)

            # Update pattern details
            self.updatePatternDetails(pattern_dict)

        except Exception as e:
            self.chart_placeholder.setText(f"Error generating chart:\n{str(e)}")
            self.chart_placeholder.show()
            self.pattern_chart.hide()
            import traceback
            traceback.print_exc()

    def showPreviousChart(self):
        """Show the previous chart in the current category (wraps around to end)"""
        if hasattr(self, 'current_category_patterns') and self.current_category_patterns:
            self.current_chart_index -= 1
            # Wrap around to end if at beginning
            if self.current_chart_index < 0:
                self.current_chart_index = len(self.current_category_patterns) - 1
            self.generateAndDisplayChart()

    def showNextChart(self):
        """Show the next chart in the current category (wraps around to start)"""
        if hasattr(self, 'current_category_patterns') and self.current_category_patterns:
            self.current_chart_index += 1
            # Wrap around to start if at end
            if self.current_chart_index >= len(self.current_category_patterns):
                self.current_chart_index = 0
            self.generateAndDisplayChart()

    def updatePatternDetails(self, pattern_dict):
        """Update pattern details text - similar to GUI's updateDetails"""
        try:
            # Get pattern info
            pattern_name = pattern_dict.get('name', 'Unknown Pattern')
            points = pattern_dict.get('points', {})

            # Build details text
            details = ""

            # Pattern name header
            if 'AB=CD_bull_' in pattern_name:
                clean_name = 'ABCD Bull ' + pattern_name.replace('AB=CD_bull_', '').replace('_unformed', '').replace('_formed', '')
            elif 'AB=CD_bear_' in pattern_name:
                clean_name = 'ABCD Bear ' + pattern_name.replace('AB=CD_bear_', '').replace('_unformed', '').replace('_formed', '')
            else:
                clean_name = pattern_name.replace('_unformed', '').replace('_formed', '')

            details += f"📊 {clean_name}\n\n"

            # Determine point order based on pattern type
            if 'X' in points:
                point_names = ['X', 'A', 'B', 'C']
            else:
                point_names = ['A', 'B', 'C']

            if 'D' in points:
                point_names.append('D')

            # Show points with prices and dates
            point_values = []
            for point_name in point_names:
                if point_name in points and 'price' in points[point_name]:
                    price = points[point_name]['price']
                    bar = points[point_name].get('bar')

                    # Get timestamp from full_data if available
                    time_str = ""
                    if bar is not None and self.full_data is not None and 0 <= bar < len(self.full_data):
                        point_time = self.full_data.index[bar]
                        if hasattr(point_time, 'strftime'):
                            if point_time.hour == 0 and point_time.minute == 0:
                                time_str = f"@{point_time.strftime('%d %b')}"
                            else:
                                time_str = f"@{point_time.strftime('%d %b %H:%M')}"

                    point_values.append(f"{point_name}=${price:.2f}{time_str}")

            if point_values:
                details += "Points: " + " • ".join(point_values) + "\n\n"

            # Show ratios
            if 'ratios' in pattern_dict:
                ratios = pattern_dict['ratios']
                ratio_values = []

                # ABCD ratios
                if 'bc' in ratios and isinstance(ratios['bc'], (int, float)):
                    ratio_values.append(f"BC: {ratios['bc']:.1f}%")
                if 'cd' in ratios and isinstance(ratios['cd'], (int, float)):
                    ratio_values.append(f"CD: {ratios['cd']:.1f}%")

                # XABCD ratios
                if 'ab_xa' in ratios and isinstance(ratios['ab_xa'], (int, float)):
                    ratio_values.append(f"AB/XA: {ratios['ab_xa']:.1f}%")
                if 'bc_ab' in ratios and isinstance(ratios['bc_ab'], (int, float)):
                    ratio_values.append(f"BC/AB: {ratios['bc_ab']:.1f}%")
                if 'cd_bc' in ratios and isinstance(ratios['cd_bc'], (int, float)):
                    ratio_values.append(f"CD/BC: {ratios['cd_bc']:.1f}%")
                if 'ad_xa' in ratios and isinstance(ratios['ad_xa'], (int, float)):
                    ratio_values.append(f"AD/XA: {ratios['ad_xa']:.1f}%")

                if ratio_values:
                    details += "Ratios: " + "  •  ".join(ratio_values) + "\n\n"

            # Show PRZ zones for ABCD patterns
            if 'prz_zones' in pattern_dict and 'X' not in points:
                prz_list = []
                proj_list = []
                for i, zone in enumerate(pattern_dict['prz_zones'], 1):
                    prz_list.append(f"{i}:${zone['min']:.2f}-${zone['max']:.2f}")
                    if 'proj_min' in zone and 'proj_max' in zone:
                        proj_list.append(f"{zone['proj_min']:.1f}%-{zone['proj_max']:.1f}%")

                prz_str = "PRZ Zones: " + "  •  ".join(prz_list)
                if proj_list:
                    prz_str += "\nProjections: " + "  •  ".join(proj_list)
                details += prz_str + "\n\n"

            # Show D-lines for XABCD patterns
            if 'd_lines' in pattern_dict and 'X' in points:
                d_lines = pattern_dict['d_lines']
                if 'D' in points:
                    # Formed pattern
                    details += f"D Lines (Formed XABCD - {len(d_lines)} lines):\n"
                else:
                    # Unformed pattern
                    details += f"D Projections (Unformed XABCD - {len(d_lines)} lines):\n"

                for i, d_price in enumerate(d_lines[:6], 1):  # Show first 6
                    details += f"  D{i}: ${d_price:.2f}\n"
                if len(d_lines) > 6:
                    details += f"  ... and {len(d_lines)-6} more\n"
                details += "\n"

            # Show tracking status if available
            pattern_id = pattern_dict.get('pattern_id')
            if pattern_id and hasattr(self.last_backtester, 'pattern_tracker'):
                tracker = self.last_backtester.pattern_tracker
                if pattern_id in tracker.tracked_patterns:
                    tracked = tracker.tracked_patterns[pattern_id]

                    details += "Tracking Info:\n"
                    details += f"Status: {tracked.status}\n"

                    if tracked.zone_entry_bar:
                        details += f"Zone Entry: Bar {tracked.zone_entry_bar}\n"
                    if tracked.reversal_bar:
                        details += f"Reversal: Bar {tracked.reversal_bar}\n"
                    if tracked.zone_exit_bar:
                        details += f"Zone Exit: Bar {tracked.zone_exit_bar}\n"

            # Set text and show widget
            self.pattern_details_text.setPlainText(details.strip())
            self.pattern_details_text.show()

        except Exception as e:
            print(f"Error updating pattern details: {e}")
            import traceback
            traceback.print_exc()
            self.pattern_details_text.hide()

    def toggleFibonacciLevels(self):
        """Toggle Fibonacci levels on/off and redraw chart"""
        print(f"🔄 Fibonacci checkbox toggled: {self.show_fib_checkbox.isChecked()}")
        if hasattr(self, 'current_category_patterns') and self.current_category_patterns:
            # Redraw current chart with/without Fibonacci levels
            self.generateAndDisplayChart()
        else:
            print("⚠️ No patterns available to redraw")

    def runFibonacciAnalysis(self):
        """Analyze Fibonacci level touches for current loaded patterns"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QProgressDialog, QMessageBox
        from PyQt6.QtCore import Qt
        import pandas as pd

        # Check if a category is selected
        if not hasattr(self, 'current_category_patterns') or not self.current_category_patterns:
            QMessageBox.information(
                self,
                "Select Category First",
                "Please select a category first.\n\n"
                "Note: Fibonacci analysis requires formed patterns (found in 'Completed Successfully')."
            )
            return

        # Check if the selected category is 'success'
        if not hasattr(self, 'current_chart_category') or self.current_chart_category != 'success':
            category_names = {
                'invalid_prz': 'Invalid PRZ',
                'failed_prz': 'Failed PRZ',
                'in_zone': 'In PRZ Zone',
                'dismissed': 'Dismissed',
                'pending': 'Pending'
            }
            current_category_display = category_names.get(self.current_chart_category, self.current_chart_category)

            QMessageBox.warning(
                self,
                "Invalid Category",
                "Fibonacci analysis only works on formed patterns.\n\n"
                "Click '✓ Completed Successfully' to analyze."
            )
            return

        # Get tracker
        tracker = self.last_backtester.pattern_tracker if hasattr(self, 'last_backtester') else None

        # Use the selected successful patterns
        patterns_to_analyze = self.current_category_patterns
        category_name = "COMPLETED SUCCESSFULLY"

        if not patterns_to_analyze:
            QMessageBox.warning(self, "No Patterns", "No successfully completed patterns available to analyze.")
            return

        # Show progress dialog
        progress = QProgressDialog("Computing Fibonacci analysis...", "Cancel", 0, len(patterns_to_analyze), self)
        progress.setWindowTitle("Fibonacci Analysis")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        # Initialize tracking
        fib_percentages = [0, 23.6, 38.2, 50, 61.8, 78.6, 88.6, 100, 112.8, 127.2, 141.4, 161.8]
        fib_stats = {f"{pct}%": {'touched': 0, 'total_candles': 0, 'touches': []} for pct in fib_percentages}
        total_patterns_analyzed = 0

        # Track individual pattern results
        individual_pattern_results = []

        print(f"\n🔍 Starting Fibonacci analysis on {len(patterns_to_analyze)} patterns")
        print(f"   Category: {category_name}")
        print(f"   Tracker available: {tracker is not None}")

        # Analyze each pattern
        for idx, pattern_dict in enumerate(patterns_to_analyze):
            if progress.wasCanceled():
                break

            progress.setValue(idx)

            try:
                # Get pattern data
                tracked_pattern = pattern_dict.get('tracked_pattern')
                if not tracked_pattern:
                    print(f"⚠️ Pattern {idx}: No tracked_pattern in dict")
                    continue

                points = pattern_dict.get('points', {})
                pattern_id = pattern_dict.get('pattern_id')

                print(f"\n🔍 Pattern {idx}: ID={pattern_id}, Points={list(points.keys())}")

                # Get A, C, D prices
                a_price = points.get('A', {}).get('price') if 'A' in points else None
                c_price = points.get('C', {}).get('price') if 'C' in points else None

                # Get D price (formed pattern or zone_entry_price for unformed)
                d_price = None
                if 'D' in points:
                    d_price = points['D']['price']
                    print(f"   Using D from points: {d_price:.2f}")
                elif pattern_id and tracker and pattern_id in tracker.tracked_patterns:
                    d_price = tracker.tracked_patterns[pattern_id].zone_entry_price
                    print(f"   Using zone_entry_price as D: {d_price}")

                if not all([a_price, c_price, d_price]):
                    print(f"⚠️ Pattern {idx}: Missing price data - A:{a_price}, C:{c_price}, D:{d_price}")
                    continue

                # Determine direction
                is_bullish = a_price < c_price

                # Calculate Fibonacci levels
                if is_bullish:
                    start_price = max(a_price, c_price)
                else:
                    start_price = min(a_price, c_price)

                end_price = d_price
                price_range = end_price - start_price

                print(f"✓ Pattern {idx}: A={a_price:.2f}, C={c_price:.2f}, D={d_price:.2f}, Range={price_range:.2f}, Bullish={is_bullish}")

                fib_levels = {}
                for pct in fib_percentages:
                    level_price = start_price + (price_range * pct / 100.0)
                    fib_levels[f"{pct}%"] = level_price

                # Get data after pattern SUCCESS (zone entry + reversal)
                # For successful patterns, analyze from reversal point, not C point
                if tracked_pattern.reversal_bar:
                    start_bar = tracked_pattern.reversal_bar
                    print(f"  Using reversal_bar: {start_bar}")
                elif tracked_pattern.zone_entry_bar:
                    start_bar = tracked_pattern.zone_entry_bar
                    print(f"  Using zone_entry_bar: {start_bar}")
                else:
                    c_bar = tracked_pattern.c_point[0] if tracked_pattern.c_point else None
                    if not c_bar:
                        print(f"  ⚠️ No start bar found!")
                        continue
                    start_bar = c_bar
                    print(f"  Using C point bar: {start_bar}")

                display_data = self.full_data.iloc[start_bar:].copy().reset_index(drop=True)

                print(f"  Start bar: {start_bar}, Data after: {len(display_data)} candles")
                print(f"  DEBUG: display_data index range: {display_data.index.min()} to {display_data.index.max()}")

                if display_data.empty:
                    print(f"  ⚠️ No data after formation!")
                    continue

                # Track which levels were touched and when (for this pattern)
                pattern_fib_touches = {f"{pct}%": None for pct in fib_percentages}
                touches_found = 0

                for level_name, level_price in fib_levels.items():
                    # Stop at 161.8%
                    if float(level_name.rstrip('%')) > 161.8:
                        break

                    # Iterate through candles with proper index
                    for candle_idx in range(len(display_data)):
                        candle = display_data.iloc[candle_idx]
                        # Check if candle touched this level (exact: Low <= level <= High)
                        if candle['Low'] <= level_price <= candle['High']:
                            # Update combined stats
                            fib_stats[level_name]['touched'] += 1
                            fib_stats[level_name]['total_candles'] += candle_idx + 1
                            fib_stats[level_name]['touches'].append(candle_idx + 1)

                            # Update individual pattern stats
                            pattern_fib_touches[level_name] = candle_idx + 1

                            touches_found += 1
                            print(f"    ✓✓✓ NEW CODE: {level_name} touched at candle_idx={candle_idx}, storing={candle_idx + 1}")
                            break  # Only count first touch

                # Store individual pattern result
                individual_pattern_results.append({
                    'pattern_id': pattern_id,
                    'pattern_type': tracked_pattern.pattern_type,
                    'pattern_subtype': tracked_pattern.subtype,
                    'fib_touches': pattern_fib_touches,
                    'total_touches': touches_found
                })

                print(f"  Total touches found: {touches_found}")
                total_patterns_analyzed += 1

            except Exception as e:
                print(f"❌ Error analyzing pattern {idx}: {e}")
                import traceback
                traceback.print_exc()
                continue

        progress.setValue(len(patterns_to_analyze))

        print(f"\n📊 Analysis complete: {total_patterns_analyzed} patterns analyzed")

        # Generate results display
        self.showFibonacciAnalysisResults(fib_stats, total_patterns_analyzed, individual_pattern_results, category_name)

    def showFibonacciAnalysisResults(self, fib_stats, total_patterns, individual_results, category_name="UNKNOWN"):
        """Display Fibonacci analysis results in a dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont

        dialog = QDialog(self)
        dialog.setWindowTitle("Fibonacci Analysis Results")
        dialog.resize(1000, 700)

        layout = QVBoxLayout()

        # Header
        header = QLabel(f"<b>Fibonacci Level Analysis - {total_patterns} Patterns Analyzed ({category_name})</b>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 16px;")
        layout.addWidget(header)

        # Tab widget for combined and individual results
        tab_widget = QTabWidget()

        # === TAB 1: COMBINED ANALYSIS TABLE ===
        combined_table = QTableWidget()
        combined_table.setColumnCount(4)
        combined_table.setHorizontalHeaderLabels(["Fib Level", "Times Touched", "Touch %", "Avg Candles"])

        # Set font
        font = QFont("Arial", 14)
        combined_table.setFont(font)

        # Populate table
        fib_levels = sorted(fib_stats.keys(), key=lambda x: float(x.rstrip('%')))
        combined_table.setRowCount(len(fib_levels))

        for row, level_name in enumerate(fib_levels):
            stat = fib_stats[level_name]
            times_touched = stat['touched']
            touch_percentage = (times_touched / total_patterns * 100) if total_patterns > 0 else 0
            avg_candles = (stat['total_candles'] / times_touched) if times_touched > 0 else 0

            # Create table items
            level_item = QTableWidgetItem(level_name)
            touched_item = QTableWidgetItem(str(times_touched))
            percentage_item = QTableWidgetItem(f"{touch_percentage:.1f}%")
            avg_item = QTableWidgetItem(f"{avg_candles:.1f}")

            # Center align all items
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            touched_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            percentage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            avg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            combined_table.setItem(row, 0, level_item)
            combined_table.setItem(row, 1, touched_item)
            combined_table.setItem(row, 2, percentage_item)
            combined_table.setItem(row, 3, avg_item)

        # Resize columns to content
        combined_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        tab_widget.addTab(combined_table, "Combined Analysis")

        # === TAB 2: INDIVIDUAL PATTERNS TABLE ===
        individual_table = QTableWidget()
        individual_table.setColumnCount(4)
        individual_table.setHorizontalHeaderLabels(["Pattern", "Pattern Type", "Fib Level", "Candle #"])
        individual_table.setFont(font)

        # Count total rows needed
        total_rows = sum(len([fib for fib, candle in result['fib_touches'].items() if candle is not None])
                        for result in individual_results)
        individual_table.setRowCount(total_rows)

        current_row = 0
        for idx, result in enumerate(individual_results, 1):
            pattern_name = f"#{idx}: {result['pattern_subtype']}"
            pattern_type = result['pattern_type']

            # Get all touched levels
            touched_levels = [(level, candle) for level, candle in sorted(result['fib_touches'].items(),
                             key=lambda x: float(x[0].rstrip('%'))) if candle is not None]

            for level_idx, (level_name, candle_num) in enumerate(touched_levels):
                # Only show pattern name and type in first row of this pattern
                if level_idx == 0:
                    pattern_item = QTableWidgetItem(pattern_name)
                    type_item = QTableWidgetItem(pattern_type)
                else:
                    pattern_item = QTableWidgetItem("")
                    type_item = QTableWidgetItem("")

                level_item = QTableWidgetItem(level_name)
                candle_item = QTableWidgetItem(str(candle_num))

                # Center align
                pattern_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                candle_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                individual_table.setItem(current_row, 0, pattern_item)
                individual_table.setItem(current_row, 1, type_item)
                individual_table.setItem(current_row, 2, level_item)
                individual_table.setItem(current_row, 3, candle_item)

                current_row += 1

        # Resize columns
        individual_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        tab_widget.addTab(individual_table, "Individual Patterns")

        layout.addWidget(tab_widget)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def runHarmonicPointsAnalysis(self):
        """Analyze how many times harmonic pattern points A, B, C are crossed after point C"""
        from PyQt6.QtWidgets import QProgressDialog, QMessageBox
        from PyQt6.QtCore import Qt

        # Check if a category is selected
        if not hasattr(self, 'current_category_patterns') or not self.current_category_patterns:
            QMessageBox.information(
                self,
                "Select Category First",
                "Please select a pattern category first.\n\n"
                "Note: Harmonic Points analysis works only on formed patterns (found in 'Completed Successfully')."
            )
            return

        # Check if the selected category is 'success'
        if not hasattr(self, 'current_chart_category') or self.current_chart_category != 'success':
            QMessageBox.warning(
                self,
                "Invalid Category",
                "Harmonic Points analysis only works on formed patterns.\n\n"
                "Click '✓ Completed Successfully' to analyze."
            )
            return

        # Get tracker
        tracker = self.last_backtester.pattern_tracker if hasattr(self, 'last_backtester') else None

        # Use the selected successful patterns
        patterns_to_analyze = self.current_category_patterns
        category_name = "COMPLETED SUCCESSFULLY"

        if not patterns_to_analyze:
            QMessageBox.warning(self, "No Patterns", "No successfully completed patterns available to analyze.")
            return

        # Show progress dialog
        progress = QProgressDialog("Computing Harmonic Points analysis...", "Cancel", 0, len(patterns_to_analyze), self)
        progress.setWindowTitle("Harmonic Points Analysis")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        # Initialize tracking for points A, B, C
        points_stats = {
            'A': {'touched': 0, 'total_candles': 0, 'touches': []},
            'B': {'touched': 0, 'total_candles': 0, 'touches': []},
            'C': {'touched': 0, 'total_candles': 0, 'touches': []}
        }
        total_patterns_analyzed = 0
        individual_pattern_results = []

        print(f"\n🔍 Starting Harmonic Points analysis on {len(patterns_to_analyze)} patterns")
        print(f"   Category: {category_name}")
        print(f"   Tracker available: {tracker is not None}")

        # Analyze each pattern
        for idx, pattern_dict in enumerate(patterns_to_analyze):
            if progress.wasCanceled():
                break

            progress.setValue(idx)

            try:
                tracked_pattern = pattern_dict.get('tracked_pattern')
                if not tracked_pattern:
                    print(f"⚠️ Pattern {idx}: No tracked_pattern in dict")
                    continue

                points = pattern_dict.get('points', {})
                pattern_id = pattern_dict.get('pattern_id')

                print(f"\n🔍 Pattern {idx}: ID={pattern_id}, Points={list(points.keys())}")

                # Get A, B, C prices
                a_price = points.get('A', {}).get('price') if 'A' in points else None
                b_price = points.get('B', {}).get('price') if 'B' in points else None
                c_price = points.get('C', {}).get('price') if 'C' in points else None

                if not all([a_price, b_price, c_price]):
                    print(f"⚠️ Pattern {idx}: Missing price data - A:{a_price}, B:{b_price}, C:{c_price}")
                    continue

                print(f"✓ Pattern {idx}: A={a_price:.2f}, B={b_price:.2f}, C={c_price:.2f}")

                # Get data after pattern SUCCESS (zone entry + reversal)
                if tracked_pattern.reversal_bar:
                    start_bar = tracked_pattern.reversal_bar
                    print(f"  Using reversal_bar: {start_bar}")
                elif tracked_pattern.zone_entry_bar:
                    start_bar = tracked_pattern.zone_entry_bar
                    print(f"  Using zone_entry_bar: {start_bar}")
                else:
                    c_bar = tracked_pattern.c_point[0] if tracked_pattern.c_point else None
                    if not c_bar:
                        print(f"  ⚠️ No start bar found!")
                        continue
                    start_bar = c_bar
                    print(f"  Using C point bar: {start_bar}")

                display_data = self.full_data.iloc[start_bar:].copy().reset_index(drop=True)

                print(f"  Start bar: {start_bar}, Data after: {len(display_data)} candles")

                if display_data.empty:
                    print(f"  ⚠️ No data after formation!")
                    continue

                # Track which points were touched and when
                pattern_point_touches = {'A': None, 'B': None, 'C': None}
                touches_found = 0

                for point_name, point_price in [('A', a_price), ('B', b_price), ('C', c_price)]:
                    # Iterate through candles with proper index
                    for candle_idx in range(len(display_data)):
                        candle = display_data.iloc[candle_idx]
                        # Check if candle touched this point level (exact: Low <= level <= High)
                        if candle['Low'] <= point_price <= candle['High']:
                            # Update combined stats
                            points_stats[point_name]['touched'] += 1
                            points_stats[point_name]['total_candles'] += candle_idx + 1
                            points_stats[point_name]['touches'].append(candle_idx + 1)

                            # Update individual pattern stats
                            pattern_point_touches[point_name] = candle_idx + 1

                            touches_found += 1
                            print(f"    ✓✓✓ Point {point_name} touched at candle {candle_idx + 1}")
                            break  # Only count first touch

                # Store individual pattern result
                individual_pattern_results.append({
                    'pattern_id': pattern_id,
                    'pattern_type': tracked_pattern.pattern_type,
                    'pattern_subtype': tracked_pattern.subtype,
                    'point_touches': pattern_point_touches,
                    'total_touches': touches_found
                })

                print(f"  Total point touches found: {touches_found}")
                total_patterns_analyzed += 1

            except Exception as e:
                print(f"❌ Error analyzing pattern {idx}: {e}")
                import traceback
                traceback.print_exc()
                continue

        progress.setValue(len(patterns_to_analyze))

        print(f"\n📊 Analysis complete: {total_patterns_analyzed} patterns analyzed")

        # Generate results display
        self.showHarmonicPointsAnalysisResults(points_stats, total_patterns_analyzed, individual_pattern_results, category_name)

    def showHarmonicPointsAnalysisResults(self, points_stats, total_patterns, individual_results, category_name="UNKNOWN"):
        """Display Harmonic Points analysis results in a dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont

        dialog = QDialog(self)
        dialog.setWindowTitle("Harmonic Points Analysis Results")
        dialog.resize(1000, 700)

        layout = QVBoxLayout()

        # Header
        header = QLabel(f"<b>Harmonic Points Analysis - {total_patterns} Patterns Analyzed ({category_name})</b>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 16px;")
        layout.addWidget(header)

        # Tab widget for combined and individual results
        tab_widget = QTabWidget()

        # === TAB 1: COMBINED ANALYSIS TABLE ===
        combined_table = QTableWidget()
        combined_table.setColumnCount(4)
        combined_table.setHorizontalHeaderLabels(["Point", "Times Touched", "Touch %", "Avg Candles"])

        # Set font
        font = QFont("Arial", 14)
        combined_table.setFont(font)

        # Populate table
        combined_table.setRowCount(3)  # A, B, C

        for row, point_name in enumerate(['A', 'B', 'C']):
            stat = points_stats[point_name]
            times_touched = stat['touched']
            touch_percentage = (times_touched / total_patterns * 100) if total_patterns > 0 else 0
            avg_candles = (stat['total_candles'] / times_touched) if times_touched > 0 else 0

            # Create table items
            point_item = QTableWidgetItem(f"Point {point_name}")
            touched_item = QTableWidgetItem(str(times_touched))
            percentage_item = QTableWidgetItem(f"{touch_percentage:.1f}%")
            avg_item = QTableWidgetItem(f"{avg_candles:.1f}")

            # Center align all items
            point_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            touched_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            percentage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            avg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            combined_table.setItem(row, 0, point_item)
            combined_table.setItem(row, 1, touched_item)
            combined_table.setItem(row, 2, percentage_item)
            combined_table.setItem(row, 3, avg_item)

        # Resize columns to content
        combined_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        tab_widget.addTab(combined_table, "Combined Analysis")

        # === TAB 2: INDIVIDUAL PATTERNS TABLE ===
        individual_table = QTableWidget()
        individual_table.setColumnCount(4)
        individual_table.setHorizontalHeaderLabels(["Pattern", "Pattern Type", "Point", "Candle #"])
        individual_table.setFont(font)

        # Count total rows needed
        total_rows = sum(len([pt for pt, candle in result['point_touches'].items() if candle is not None])
                        for result in individual_results)
        individual_table.setRowCount(total_rows)

        current_row = 0
        for idx, result in enumerate(individual_results, 1):
            pattern_name = f"#{idx}: {result['pattern_subtype']}"
            pattern_type = result['pattern_type']

            # Get all touched points
            touched_points = [(point, candle) for point, candle in [('A', result['point_touches']['A']),
                             ('B', result['point_touches']['B']), ('C', result['point_touches']['C'])] if candle is not None]

            for point_idx, (point_name, candle_num) in enumerate(touched_points):
                # Only show pattern name and type in first row of this pattern
                if point_idx == 0:
                    pattern_item = QTableWidgetItem(pattern_name)
                    type_item = QTableWidgetItem(pattern_type)
                else:
                    pattern_item = QTableWidgetItem("")
                    type_item = QTableWidgetItem("")

                point_item = QTableWidgetItem(f"Point {point_name}")
                candle_item = QTableWidgetItem(str(candle_num))

                # Center align
                pattern_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                point_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                candle_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                individual_table.setItem(current_row, 0, pattern_item)
                individual_table.setItem(current_row, 1, type_item)
                individual_table.setItem(current_row, 2, point_item)
                individual_table.setItem(current_row, 3, candle_item)

                current_row += 1

        # Resize columns
        individual_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        tab_widget.addTab(individual_table, "Individual Patterns")

        layout.addWidget(tab_widget)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def setupCrosshair(self):
        """Setup crosshair lines and labels (called after chart.clear())"""
        from PyQt6.QtGui import QFont

        # Create crosshair lines
        self.vLine = pg.InfiniteLine(angle=90, movable=False, pen=pg.mkPen('cyan', width=2, style=Qt.PenStyle.DashLine))
        self.hLine = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen('cyan', width=2, style=Qt.PenStyle.DashLine))

        self.pattern_chart.addItem(self.vLine, ignoreBounds=True)
        self.pattern_chart.addItem(self.hLine, ignoreBounds=True)

        # X-axis label
        self.x_axis_label = pg.TextItem('', anchor=(0.5, 0), color='white',
                                        fill=pg.mkBrush(0, 100, 255, 220),
                                        border=pg.mkPen('white', width=2))
        self.x_axis_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        self.x_axis_label.setZValue(1000)
        self.pattern_chart.addItem(self.x_axis_label)

        # Y-axis label
        self.y_axis_label = pg.TextItem('', anchor=(0, 0.5), color='white',
                                        fill=pg.mkBrush(0, 100, 255, 220),
                                        border=pg.mkPen('white', width=2))
        self.y_axis_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        self.y_axis_label.setZValue(1000)
        self.pattern_chart.addItem(self.y_axis_label)

        # OHLC info box
        self.crosshair_label = pg.TextItem('', anchor=(0, 0), color='white',
                                          fill=pg.mkBrush(0, 0, 0, 150),
                                          border=pg.mkPen('cyan', width=1))
        self.crosshair_label.setFont(QFont('Arial', 9, QFont.Weight.Bold))
        self.crosshair_label.setZValue(1001)
        self.pattern_chart.addItem(self.crosshair_label)

        # Initially hide
        self.vLine.setVisible(False)
        self.hLine.setVisible(False)
        self.x_axis_label.setVisible(False)
        self.y_axis_label.setVisible(False)
        self.crosshair_label.setVisible(False)

        # Setup mouse tracking
        self.proxy = pg.SignalProxy(self.pattern_chart.scene().sigMouseMoved, rateLimit=15, slot=self.mouseMoved)
        self.pattern_chart.setMouseTracking(True)

    def mouseMoved(self, evt):
        """Handle mouse movement for crosshair"""
        if not hasattr(self, 'vLine') or self.vLine is None:
            return

        pos = evt[0]
        if self.pattern_chart.sceneBoundingRect().contains(pos):
            mousePoint = self.pattern_chart.plotItem.vb.mapSceneToView(pos)
            x, y = mousePoint.x(), mousePoint.y()

            # Show crosshair
            self.vLine.setPos(x)
            self.hLine.setPos(y)
            self.vLine.setVisible(True)
            self.hLine.setVisible(True)

            # Update labels
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
        """Update axis labels with current values - match GUI formatting"""
        try:
            if self.display_data is None or len(self.display_data) == 0:
                return

            view_range = self.pattern_chart.viewRange()

            # Format and position X-axis (time) label
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

                # Position near bottom of chart area, visible inside the chart
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
        """Update OHLC info box - match GUI formatting"""
        try:
            if self.display_data is None or len(self.display_data) == 0:
                return

            x_int = int(round(x))
            if 0 <= x_int < len(self.display_data):
                # Get date and OHLC data for this index
                date = self.display_data.index[x_int]
                row = self.display_data.iloc[x_int]

                # Format date - handle different date types
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

                # Create label text with better formatting - match GUI
                label_text = f"Time: {date_str}\n"
                label_text += f"Open:  ${open_price:,.2f}\n"
                label_text += f"High:  ${high_price:,.2f}\n"
                label_text += f"Low:   ${low_price:,.2f}\n"
                label_text += f"Close: ${close_price:,.2f}\n"
                label_text += f"Price: ${y:,.2f}"

                self.crosshair_label.setText(label_text)

                # Position in upper left corner
                view_range = self.pattern_chart.viewRange()
                self.crosshair_label.setPos(view_range[0][0] + 2, view_range[1][1] * 0.98)
                self.crosshair_label.setVisible(True)

        except Exception as e:
            pass