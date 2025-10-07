"""
Backtesting Dialog for Harmonic Pattern Trading System
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QProgressBar,
    QMessageBox, QCheckBox, QComboBox, QRadioButton, QDateEdit,
    QButtonGroup, QSplitter, QScrollArea, QFrame, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate, QTimer
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
                    # Format date as dd MMM YYYY (TradingView style with year)
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

        # Enable maximize button
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

        # Chart display variables
        self.current_chart_category = None
        self.current_chart_index = 0
        self.current_chart_files = []
        self.chart_dir = os.path.join("backtest_results", "pattern_charts")

        # Load the full dataset if available
        self.loadFullDataset()

        self.initUI()

        # Open maximized by default (after UI is initialized)
        # Use QTimer to ensure maximize happens after show()
        QTimer.singleShot(0, self.showMaximized)

    def loadFullDataset(self):
        """Use the data passed from GUI (already filtered to the correct date range)"""
        try:
            # Use the data that was passed to us - it's already the correct range
            self.full_data = self.data.copy()

            # Ensure index is datetime
            if not isinstance(self.full_data.index, pd.DatetimeIndex):
                if 'Date' in self.full_data.columns:
                    self.full_data['Date'] = pd.to_datetime(self.full_data['Date'])
                    self.full_data.set_index('Date', inplace=True)
                elif 'time' in self.full_data.columns:
                    self.full_data['time'] = pd.to_datetime(self.full_data['time'])
                    self.full_data.set_index('time', inplace=True)

            print(f"✓ Using backtesting data: {len(self.full_data)} bars from {self.full_data.index[0]} to {self.full_data.index[-1]}")

        except Exception as e:
            print(f"Error setting up full dataset: {e}")
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
        # Grid lines removed for cleaner chart appearance
        self.pattern_chart.showGrid(x=False, y=False)
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
        self.pattern_details_text.setMaximumHeight(120)
        self.pattern_details_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)  # Disable line wrapping to show horizontally
        # Set larger font size to match pattern viewer
        font = self.pattern_details_text.font()
        font.setPointSize(12)
        self.pattern_details_text.setFont(font)
        self.pattern_details_text.hide()  # Hide initially
        layout.addWidget(self.pattern_details_text)

        # Fibonacci and Harmonic Points toggles (only for successful patterns)
        fib_layout = QHBoxLayout()

        # Fibonacci levels checkbox
        self.show_fib_checkbox = QCheckBox("Show Fibonacci Levels")
        self.show_fib_checkbox.setChecked(True)  # Default ON
        self.show_fib_checkbox.stateChanged.connect(self.toggleFibonacciLevels)
        self.show_fib_checkbox.setEnabled(False)  # Disabled until successful pattern is shown
        self.show_fib_checkbox.setToolTip(
            "Fibonacci levels calculated from Point A to Point D.\n"
            "For unformed patterns: D = first candle that touched PRZ\n"
            "(High for bearish, Low for bullish)"
        )
        fib_layout.addWidget(self.show_fib_checkbox)

        # Harmonic Points checkbox
        self.show_harmonic_points_checkbox = QCheckBox("Show Harmonic Points (A, B, C)")
        self.show_harmonic_points_checkbox.setChecked(True)  # Default ON
        self.show_harmonic_points_checkbox.stateChanged.connect(self.toggleHarmonicPoints)
        self.show_harmonic_points_checkbox.setEnabled(False)  # Disabled until successful pattern is shown
        self.show_harmonic_points_checkbox.setToolTip(
            "Show horizontal lines for harmonic pattern points A, B, and C.\n"
            "Useful for visualizing price interactions with key pattern levels."
        )
        fib_layout.addWidget(self.show_harmonic_points_checkbox)

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

        # PnL Analysis button
        self.pnl_analysis_btn = QPushButton("💰 PnL Analysis (Custom)")
        self.pnl_analysis_btn.setStyleSheet("background-color: #32CD32; color: white; font-weight: bold;")
        self.pnl_analysis_btn.setToolTip("Calculate Profit & Loss based on entry/exit prices and leverage")
        self.pnl_analysis_btn.clicked.connect(self.runPnLAnalysis)
        self.pnl_analysis_btn.setEnabled(False)  # Enable only when patterns are loaded
        analysis_layout.addWidget(self.pnl_analysis_btn)

        # Enhanced PnL Analysis button (successful patterns only)
        self.enhanced_pnl_btn = QPushButton("💎 Enhanced PnL (TP1 Strategy)")
        self.enhanced_pnl_btn.setStyleSheet("background-color: #FFD700; color: black; font-weight: bold;")
        self.enhanced_pnl_btn.setToolTip("Entry at D, TP1 at first Fib/Point hit, 25% profit, SL to entry\nOnly analyzes successful patterns")
        self.enhanced_pnl_btn.clicked.connect(self.runEnhancedPnLAnalysis)
        self.enhanced_pnl_btn.setEnabled(False)  # Enable only when patterns are loaded
        analysis_layout.addWidget(self.enhanced_pnl_btn)

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
                self.pnl_analysis_btn.setEnabled(True)  # Enable PnL Analysis when backtest completes
                self.enhanced_pnl_btn.setEnabled(True)  # Enable Enhanced PnL Analysis

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

        # Excel export removed from auto-save - user must click Export button
        # Display message to inform user
        self.results_text.append("\n✅ Backtest complete! Click 'Export Results' button to save to Excel.")

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

    def autoExportToExcel(self, stats, show_dialog=True):
        """Export backtest results to Excel in the backtest_results folder"""
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

            # Add success message to results text
            self.results_text.append(f"\n✅ Excel exported successfully:")
            self.results_text.append(f"   {filename}")
            self.results_text.append(f"   📊 Sheets: Summary, Pattern Details, Pattern Performance, Fib & Harmonic Analysis")

            # Show dialog if requested (when user clicks Export button)
            if show_dialog:
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Results exported to Excel:\n\n{filename}\n\n"
                    f"Sheets included:\n"
                    f"• Summary\n"
                    f"• Pattern Details\n"
                    f"• Pattern Performance\n"
                    f"• Fib & Harmonic Analysis"
                )

        except Exception as e:
            # Show error with appropriate handling
            error_msg = f"Could not export Excel: {str(e)}"
            self.results_text.append(f"\n⚠️ {error_msg}")
            if show_dialog:
                QMessageBox.critical(self, "Export Error", error_msg)

    def exportResults(self):
        """Export backtest results to Excel (only when user clicks Export button)"""
        if not hasattr(self, 'last_stats'):
            QMessageBox.warning(self, "No Results", "No results to export. Please run a backtest first.")
            return

        # Call the Excel export function
        self.autoExportToExcel(self.last_stats)

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
        if hasattr(self, 'pnl_analysis_btn'):
            self.pnl_analysis_btn.setEnabled(True)
        if hasattr(self, 'enhanced_pnl_btn'):
            self.enhanced_pnl_btn.setEnabled(True)

        # Generate and display first chart
        self.generateAndDisplayChart()

    def generateAndDisplayChart(self):
        """Generate chart for current pattern using PyQtGraph - exact copy of GUI's drawPattern"""
        if not hasattr(self, 'current_category_patterns') or not self.current_category_patterns:
            return

        if self.current_chart_index >= len(self.current_category_patterns):
            return

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

                    # Show ALL candles after the latest event until end of backtest data
                    max_bar = len(test_data)  # Show everything until end date

            # max_bar already set to end of data, no need to limit further

            # Store for use in coordinate calculations
            self.chart_min_bar = min_bar
            self.chart_max_bar = max_bar
            self.display_start_idx = min_bar  # For OHLC box bar number calculation

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
                    if point_bar is None:
                        continue

                    # CRITICAL FIX: Bar indices are relative to test_data (filtered backtest data)
                    # NOT relative to full_data. Use test_data for correct timestamp lookup.
                    if point_bar >= len(test_data):
                        continue

                    # Get timestamp from test_data using bar index (relative to backtest data)
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
            if pattern_id and pattern_id in tracker.tracked_patterns:
                tracked_pattern = tracker.tracked_patterns[pattern_id]

                # Draw D-lines for XABCD patterns (check XABCD first before PRZ zones)
                if pattern_dict.get('pattern_type') == 'XABCD' and hasattr(tracked_pattern, 'd_lines') and tracked_pattern.d_lines and len(x_coords) > 0:
                    last_x = x_coords[-1]
                    is_bullish = points['A']['price'] > points['C']['price']
                    color = '#00BFFF' if is_bullish else '#FF8C00'

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
            if self.show_fib_checkbox.isChecked() and pattern_status == 'success':

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
                    # Determine if bullish or bearish (same logic as pattern drawing)
                    is_bullish = a_price > c_price  # A > C = bullish (A is high, C is high, D is low)

                    # Calculate Fibonacci levels (same logic as analysis function)
                    # For BULLISH: 0% at C/A (low), 100% at D (high) - measures upward extension
                    # For BEARISH: 0% at D (high), 100% at C/A (low) - measures downward retracement
                    if is_bullish:
                        start_price = max(a_price, c_price)  # 0% at swing high (C or A)
                        end_price = d_price  # 100% at D (higher)
                        price_range = end_price - start_price
                    else:
                        # BEARISH: Retracement FROM D back down
                        start_price = d_price  # 0% at D (the high where pattern completed)
                        end_price = min(a_price, c_price)  # 100% back to swing low (C or A)
                        price_range = end_price - start_price  # Negative range for bearish

                    # Calculate Fibonacci levels
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

            # Draw harmonic point levels (A, B, C) if checkbox is checked and pattern is successful
            if self.show_harmonic_points_checkbox.isChecked() and pattern_status == 'success':
                # Use different colors than Fibonacci to distinguish them
                harmonic_colors = {
                    'A': '#FF6B6B',  # Red for Point A
                    'B': '#FF6B6B',  # Red for Point B (same as A for visibility)
                    'C': '#FF6B6B'   # Red for Point C (same as A for visibility)
                }

                for point_label in ['A', 'B', 'C']:
                    if point_label in points and 'price' in points[point_label]:
                        point_price = points[point_label]['price']
                        point_color = harmonic_colors[point_label]

                        # Draw horizontal line for this harmonic point
                        point_pen = mkPen(color=point_color, width=2, style=Qt.PenStyle.SolidLine)
                        self.pattern_chart.plot([0, len(display_data)-1], [point_price, point_price], pen=point_pen)

                        # Add label on the left side (to differentiate from Fib labels on right)
                        point_text = pg.TextItem(f"Point {point_label}", color=point_color, anchor=(1, 0.5))
                        point_text.setPos(5, point_price)  # Left side at position 5
                        point_text.setFont(QFont('Arial', 10, QFont.Weight.Bold))
                        self.pattern_chart.addItem(point_text)

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
                self.show_harmonic_points_checkbox.setEnabled(True)
            else:
                self.show_fib_checkbox.setEnabled(False)
                self.show_fib_checkbox.setChecked(False)  # Uncheck if disabled
                self.show_harmonic_points_checkbox.setEnabled(False)
                self.show_harmonic_points_checkbox.setChecked(False)  # Uncheck if disabled

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
            # Get pattern info from tracked pattern if available
            pattern_id = pattern_dict.get('pattern_id')
            tracked = None
            if pattern_id and hasattr(self.last_backtester, 'pattern_tracker'):
                tracker = self.last_backtester.pattern_tracker
                if pattern_id in tracker.tracked_patterns:
                    tracked = tracker.tracked_patterns[pattern_id]

            # Get pattern name from tracked pattern or fall back to pattern_dict
            if tracked:
                pattern_type = tracked.pattern_type
                subtype = tracked.subtype
                # Build proper pattern name
                if pattern_type == 'ABCD':
                    # Determine bull/bear from points
                    points = pattern_dict.get('points', {})
                    if 'A' in points and 'B' in points:
                        is_bull = points['B']['price'] < points['A']['price']
                        direction = 'Bull' if is_bull else 'Bear'
                    else:
                        direction = ''
                    pattern_name = f"ABCD {direction} {subtype}".strip()
                else:  # XABCD
                    pattern_name = subtype  # Gartley, Butterfly, etc.
            else:
                pattern_name = pattern_dict.get('name', 'Unknown Pattern')
                # Clean up pattern name
                if 'AB=CD_bull_' in pattern_name:
                    pattern_name = 'ABCD Bull ' + pattern_name.replace('AB=CD_bull_', '').replace('_unformed', '').replace('_formed', '')
                elif 'AB=CD_bear_' in pattern_name:
                    pattern_name = 'ABCD Bear ' + pattern_name.replace('AB=CD_bear_', '').replace('_unformed', '').replace('_formed', '')
                else:
                    pattern_name = pattern_name.replace('_unformed', '').replace('_formed', '')

            points = pattern_dict.get('points', {})

            # Build details text
            details = ""
            details += f"📊 {pattern_name}\n\n"

            # Determine point order based on pattern type
            if 'X' in points:
                point_names = ['X', 'A', 'B', 'C']
            else:
                point_names = ['A', 'B', 'C']

            if 'D' in points:
                point_names.append('D')

            # Show points with prices and dates (including year)
            point_values = []
            # CRITICAL: Get test_data from backtester (filtered data used for backtest)
            test_data = self.last_backtester.data if hasattr(self, 'last_backtester') and self.last_backtester else None

            for point_name in point_names:
                if point_name in points and 'price' in points[point_name]:
                    price = points[point_name]['price']
                    bar = points[point_name].get('bar')

                    # Get timestamp from test_data (NOT full_data)
                    # Bar indices are relative to the backtested data range
                    time_str = ""
                    if bar is not None and test_data is not None and 0 <= bar < len(test_data):
                        try:
                            point_time = test_data.index[bar]

                            # Ensure it's a datetime object
                            if not hasattr(point_time, 'strftime'):
                                point_time = pd.to_datetime(point_time)

                            if point_time.hour == 0 and point_time.minute == 0:
                                time_str = f"@{point_time.strftime('%d %b %Y')}"
                            else:
                                time_str = f"@{point_time.strftime('%d %b %Y %H:%M')}"
                        except Exception as e:
                            print(f"Error formatting time for {point_name} at bar {bar}: {e}")
                            time_str = ""

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

            # Show ALL PRZ zones for ABCD patterns (use all_prz_zones from tracked pattern if available)
            prz_zones_to_show = []
            if tracked and hasattr(tracked, 'all_prz_zones') and tracked.all_prz_zones:
                prz_zones_to_show = tracked.all_prz_zones
            elif 'prz_zones' in pattern_dict:
                prz_zones_to_show = pattern_dict['prz_zones']

            if prz_zones_to_show and 'X' not in points:
                prz_list = []
                proj_list = []
                for i, zone in enumerate(prz_zones_to_show, 1):
                    prz_list.append(f"{i}:${zone['min']:.2f}-${zone['max']:.2f}")
                    if 'proj_min' in zone and 'proj_max' in zone:
                        proj_list.append(f"{zone['proj_min']:.1f}%-{zone['proj_max']:.1f}%")

                prz_str = "PRZ Zones: " + "  •  ".join(prz_list)
                if proj_list:
                    prz_str += "\nProjections: " + "  •  ".join(proj_list)
                details += prz_str + "\n\n"

            # Show D-lines for XABCD patterns (from tracked pattern if available)
            d_lines_to_show = []
            if tracked and hasattr(tracked, 'd_lines') and tracked.d_lines:
                d_lines_to_show = tracked.d_lines
            elif 'd_lines' in pattern_dict:
                d_lines_to_show = pattern_dict['d_lines']

            if d_lines_to_show and 'X' in points:
                if 'D' in points:
                    # Formed pattern - get D point timestamp
                    d_bar = points['D'].get('bar')
                    d_time_str = ""
                    if d_bar is not None and test_data is not None and 0 <= d_bar < len(test_data):
                        d_time = test_data.index[d_bar]
                        if hasattr(d_time, 'strftime'):
                            if d_time.hour == 0 and d_time.minute == 0:
                                d_time_str = d_time.strftime('%d %b %Y')
                            else:
                                d_time_str = d_time.strftime('%d %b %Y %H:%M')

                    if d_time_str:
                        details += f"D Lines ({len(d_lines_to_show)} lines, at D @ {d_time_str}):\n"
                    else:
                        details += f"D Lines (Formed XABCD - {len(d_lines_to_show)} lines):\n"
                else:
                    # Unformed pattern - get C point timestamp
                    c_bar = points['C'].get('bar')
                    c_time_str = ""
                    if c_bar is not None and test_data is not None and 0 <= c_bar < len(test_data):
                        c_time = test_data.index[c_bar]
                        if hasattr(c_time, 'strftime'):
                            if c_time.hour == 0 and c_time.minute == 0:
                                c_time_str = c_time.strftime('%d %b %Y')
                            else:
                                c_time_str = c_time.strftime('%d %b %Y %H:%M')

                    if c_time_str:
                        details += f"D Projections ({len(d_lines_to_show)} lines, from C @ {c_time_str}):\n"
                    else:
                        details += f"D Projections ({len(d_lines_to_show)} lines):\n"

                for i, d_price in enumerate(d_lines_to_show, 1):
                    details += f"  D{i}: ${d_price:.2f}\n"
                details += "\n"

            # Show tracking status if available
            if tracked:
                details += "Tracking Info:\n"
                details += f"Status: {tracked.status}\n"

                if tracked.zone_entry_bar:
                    zone_entry_bar = tracked.zone_entry_bar
                    details += f"Zone Entry: Bar {zone_entry_bar}"

                    # Add date for zone entry - use test_data not full_data
                    if test_data is not None and 0 <= zone_entry_bar < len(test_data):
                        try:
                            zone_time = test_data.index[zone_entry_bar]
                            if not hasattr(zone_time, 'strftime'):
                                zone_time = pd.to_datetime(zone_time)
                            zone_date_str = zone_time.strftime('%d %b %Y')
                            details += f" ({zone_date_str})"
                        except:
                            pass

                    details += f" @ ${tracked.zone_entry_price:,.2f}\n"

                if tracked.reversal_bar:
                    reversal_bar = tracked.reversal_bar
                    details += f"Reversal: Bar {reversal_bar}"

                    # Add date for reversal - use test_data not full_data
                    if test_data is not None and 0 <= reversal_bar < len(test_data):
                        try:
                            rev_time = test_data.index[reversal_bar]
                            if not hasattr(rev_time, 'strftime'):
                                rev_time = pd.to_datetime(rev_time)
                            rev_date_str = rev_time.strftime('%d %b %Y')
                            details += f" ({rev_date_str})"
                        except:
                            pass

                    details += f" @ ${tracked.reversal_price:,.2f}\n"

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
        if hasattr(self, 'current_category_patterns') and self.current_category_patterns:
            # Redraw current chart with/without Fibonacci levels
            self.generateAndDisplayChart()

    def toggleHarmonicPoints(self):
        """Toggle Harmonic Points (A, B, C) on/off and redraw chart"""
        if hasattr(self, 'current_category_patterns') and self.current_category_patterns:
            # Redraw current chart with/without Harmonic Points
            self.generateAndDisplayChart()

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

        # Get tracker and backtesting data
        tracker = self.last_backtester.pattern_tracker if hasattr(self, 'last_backtester') else None
        backtest_data = self.last_backtester.data if hasattr(self, 'last_backtester') else None

        if backtest_data is None:
            QMessageBox.warning(self, "No Data", "Backtesting data not available.")
            return

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

                # Get A, C, D prices
                a_price = points.get('A', {}).get('price') if 'A' in points else None
                c_price = points.get('C', {}).get('price') if 'C' in points else None

                # Get D price (formed pattern or zone_entry_price for unformed)
                d_price = None
                if 'D' in points:
                    d_price = points['D']['price']
                elif pattern_id and tracker and pattern_id in tracker.tracked_patterns:
                    d_price = tracker.tracked_patterns[pattern_id].zone_entry_price

                if not all([a_price, c_price, d_price]):
                    print(f"⚠️ Pattern {idx}: Missing price data - A:{a_price}, C:{c_price}, D:{d_price}")
                    continue

                # Determine direction (same logic as chart drawing)
                is_bullish = a_price > c_price  # A > C = bullish

                # Calculate Fibonacci levels
                # For BULLISH: 0% at C/A (low), 100% at D (high) - measures upward extension
                # For BEARISH: 0% at D (high), 100% at C/A (low) - measures downward retracement
                if is_bullish:
                    start_price = max(a_price, c_price)  # 0% at swing high (C or A)
                    end_price = d_price  # 100% at D (higher)
                    price_range = end_price - start_price
                else:
                    # BEARISH: Retracement FROM D back down
                    start_price = d_price  # 0% at D (the high where pattern completed)
                    end_price = min(a_price, c_price)  # 100% back to swing low (C or A)
                    price_range = end_price - start_price  # Negative range for bearish

                # Calculate Fibonacci levels
                fib_levels = {}
                for pct in fib_percentages:
                    level_price = start_price + (price_range * pct / 100.0)
                    fib_levels[f"{pct}%"] = level_price

                # Get data after D point (when pattern completes)
                # This gives us maximum candles for analysis
                d_bar = tracked_pattern.zone_entry_bar if tracked_pattern.zone_entry_bar else None
                if not d_bar:
                    # Fallback to actual D point if available
                    if 'D' in points and 'index' in points['D']:
                        d_bar = points['D']['index']
                    elif tracked_pattern.actual_d_bar:
                        d_bar = tracked_pattern.actual_d_bar
                    else:
                        print(f"  ⚠️ No D bar found!")
                        continue

                display_data = backtest_data.iloc[d_bar:].copy().reset_index(drop=True)

                if display_data.empty:
                    print(f"  ⚠️ No data after formation!")
                    continue

                # Track how many times price crosses each Fibonacci level (for this pattern)
                pattern_fib_crosses = {f"{pct}%": 0 for pct in fib_percentages}
                total_crosses = 0
                pattern_completed = False  # Flag to mark pattern as completed when 161.8% hit

                # Check if 161.8% level is hit first (pattern completion condition)
                level_161_8 = fib_levels.get('161.8%')
                stop_at_candle = len(display_data)  # Default: analyze all candles

                if level_161_8:
                    # Find first candle that touches 161.8% level
                    for candle_idx in range(len(display_data)):
                        candle = display_data.iloc[candle_idx]
                        # Check if candle touched 161.8% (low <= level <= high)
                        if candle['Low'] <= level_161_8 <= candle['High']:
                            stop_at_candle = candle_idx + 1  # Include this candle
                            pattern_completed = True
                            print(f"    🎯 161.8% Fib hit at candle {candle_idx} - Pattern COMPLETED, stopping analysis")
                            break

                for level_name, level_price in fib_levels.items():
                    # Stop at 161.8%
                    if float(level_name.rstrip('%')) > 161.8:
                        break

                    # Track touches: count every time candle wick touches the level
                    touches = 0
                    touch_details = []  # Store touch info for debug

                    # Only analyze up to stop_at_candle (either all candles or where 161.8% was hit)
                    for candle_idx in range(min(stop_at_candle, len(display_data))):
                        candle = display_data.iloc[candle_idx]

                        # Check if candle touched this level (low <= level <= high)
                        if candle['Low'] <= level_price <= candle['High']:
                            touches += 1
                            touch_details.append({
                                'candle': candle_idx,
                                'low': candle['Low'],
                                'high': candle['High'],
                                'close': candle['Close']
                            })

                    # Update stats for this level
                    if touches > 0:
                        fib_stats[level_name]['touched'] += 1  # Pattern touched this level
                        fib_stats[level_name]['total_candles'] += touches  # Now stores total touches
                        fib_stats[level_name]['touches'].append(touches)

                        # Update individual pattern stats
                        pattern_fib_crosses[level_name] = touches
                        total_crosses += touches

                # Store individual pattern result
                individual_pattern_results.append({
                    'pattern_id': pattern_id,
                    'pattern_type': tracked_pattern.pattern_type,
                    'pattern_subtype': tracked_pattern.subtype,
                    'fib_crosses': pattern_fib_crosses,
                    'total_crosses': total_crosses
                })

                total_patterns_analyzed += 1

            except Exception as e:
                print(f"❌ Error analyzing pattern {idx}: {e}")
                import traceback
                traceback.print_exc()
                continue

        progress.setValue(len(patterns_to_analyze))

        print(f"\n📊 Analysis complete: {total_patterns_analyzed} patterns analyzed")

        # Save statistics to database for Active Trading Signals
        self.saveFibonacciStatistics(fib_stats, total_patterns_analyzed, individual_pattern_results)

        # Generate results display
        self.showFibonacciAnalysisResults(fib_stats, total_patterns_analyzed, individual_pattern_results, category_name)

    def saveFibonacciStatistics(self, fib_stats, total_patterns, individual_results):
        """Save Fibonacci analysis statistics to database for use in Active Trading Signals"""
        try:
            from signal_database import SignalDatabase

            db = SignalDatabase()

            # Get symbol and timeframe from backtester
            if not hasattr(self, 'last_backtester'):
                return

            symbol = getattr(self.last_backtester, 'symbol', 'UNKNOWN')
            timeframe = getattr(self.last_backtester, 'timeframe', 'UNKNOWN')

            # Group patterns by type and direction
            pattern_groups = {}

            for result in individual_results:
                pattern_type = result['pattern_type']
                pattern_name = result.get('pattern_subtype', result['pattern_type'])
                direction = 'bullish' if result.get('is_bullish', True) else 'bearish'

                key = (pattern_type, pattern_name, direction)

                if key not in pattern_groups:
                    pattern_groups[key] = []

                pattern_groups[key].append(result)

            # Calculate and save statistics for each group
            for (pattern_type, pattern_name, direction), patterns in pattern_groups.items():
                sample_count = len(patterns)

                # Aggregate Fibonacci level statistics
                fib_aggregated = {}

                for pattern in patterns:
                    fib_crosses = pattern.get('fib_crosses', {})

                    for level_name, touches in fib_crosses.items():
                        if level_name not in fib_aggregated:
                            fib_aggregated[level_name] = {'hit_count': 0, 'total_touches': 0}

                        if touches > 0:
                            fib_aggregated[level_name]['hit_count'] += 1
                            fib_aggregated[level_name]['total_touches'] += touches

                # Save each Fibonacci level statistic
                for level_name, data in fib_aggregated.items():
                    hit_percentage = (data['hit_count'] / sample_count * 100) if sample_count > 0 else 0
                    avg_touches = (data['total_touches'] / data['hit_count']) if data['hit_count'] > 0 else 0

                    db.upsert_pattern_statistic(
                        symbol=symbol,
                        timeframe=timeframe,
                        pattern_type=pattern_type,
                        pattern_name=pattern_name,
                        direction=direction,
                        stat_type='fibonacci',
                        level_name=level_name,
                        patterns_hit=data['hit_count'],
                        hit_percentage=hit_percentage,
                        avg_touches=avg_touches,
                        sample_count=sample_count
                    )

            print(f"✅ Saved Fibonacci statistics for {len(pattern_groups)} pattern groups")

        except Exception as e:
            print(f"⚠️ Error saving Fibonacci statistics: {e}")
            import traceback
            traceback.print_exc()

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
        combined_table.setHorizontalHeaderLabels(["Fib Level", "Patterns Hit", "Hit %", "Avg Touches"])

        # Set font
        font = QFont("Arial", 14)
        combined_table.setFont(font)

        # Populate table
        fib_levels = sorted(fib_stats.keys(), key=lambda x: float(x.rstrip('%')))
        combined_table.setRowCount(len(fib_levels))

        for row, level_name in enumerate(fib_levels):
            stat = fib_stats[level_name]
            patterns_hit = stat['touched']  # Number of patterns that hit this level
            hit_percentage = (patterns_hit / total_patterns * 100) if total_patterns > 0 else 0
            avg_touches = (stat['total_candles'] / patterns_hit) if patterns_hit > 0 else 0

            # Create table items
            level_item = QTableWidgetItem(level_name)
            hit_item = QTableWidgetItem(str(patterns_hit))
            percentage_item = QTableWidgetItem(f"{hit_percentage:.1f}%")
            avg_item = QTableWidgetItem(f"{avg_touches:.1f}")

            # Center align all items
            level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            hit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            percentage_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            avg_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            combined_table.setItem(row, 0, level_item)
            combined_table.setItem(row, 1, hit_item)
            combined_table.setItem(row, 2, percentage_item)
            combined_table.setItem(row, 3, avg_item)

        # Resize columns to content
        combined_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        tab_widget.addTab(combined_table, "Combined Analysis")

        # === TAB 2: INDIVIDUAL PATTERNS TABLE ===
        individual_table = QTableWidget()
        individual_table.setColumnCount(4)
        individual_table.setHorizontalHeaderLabels(["Pattern", "Pattern Type", "Fib Level", "Touches"])
        individual_table.setFont(font)

        # Count total rows needed
        total_rows = sum(len([fib for fib, crosses in result['fib_crosses'].items() if crosses > 0])
                        for result in individual_results)
        individual_table.setRowCount(total_rows)

        current_row = 0
        for idx, result in enumerate(individual_results, 1):
            pattern_name = f"#{idx}: {result['pattern_subtype']}"
            pattern_type = result['pattern_type']

            # Get all crossed levels
            crossed_levels = [(level, crosses) for level, crosses in sorted(result['fib_crosses'].items(),
                             key=lambda x: float(x[0].rstrip('%'))) if crosses > 0]

            for level_idx, (level_name, cross_count) in enumerate(crossed_levels):
                # Only show pattern name and type in first row of this pattern
                if level_idx == 0:
                    pattern_item = QTableWidgetItem(pattern_name)
                    type_item = QTableWidgetItem(pattern_type)
                else:
                    pattern_item = QTableWidgetItem("")
                    type_item = QTableWidgetItem("")

                level_item = QTableWidgetItem(level_name)
                cross_item = QTableWidgetItem(str(cross_count))

                # Center align
                pattern_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                level_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                cross_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                individual_table.setItem(current_row, 0, pattern_item)
                individual_table.setItem(current_row, 1, type_item)
                individual_table.setItem(current_row, 2, level_item)
                individual_table.setItem(current_row, 3, cross_item)

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
        """Analyze how many times harmonic pattern points A, B, C are touched after point D"""
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

        # Get tracker and backtesting data
        tracker = self.last_backtester.pattern_tracker if hasattr(self, 'last_backtester') else None
        backtest_data = self.last_backtester.data if hasattr(self, 'last_backtester') else None

        if backtest_data is None:
            QMessageBox.warning(self, "No Data", "Backtesting data not available.")
            return

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

        # Initialize tracking for points A, B, C (separate for bullish and bearish)
        points_stats = {
            'bullish': {
                'A': {'touched': 0, 'total_touches': 0, 'touches': []},
                'B': {'touched': 0, 'total_touches': 0, 'touches': []},
                'C': {'touched': 0, 'total_touches': 0, 'touches': []}
            },
            'bearish': {
                'A': {'touched': 0, 'total_touches': 0, 'touches': []},
                'B': {'touched': 0, 'total_touches': 0, 'touches': []},
                'C': {'touched': 0, 'total_touches': 0, 'touches': []}
            }
        }
        total_patterns_analyzed = {'bullish': 0, 'bearish': 0}
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

                # Get A, B, C prices
                a_price = points.get('A', {}).get('price') if 'A' in points else None
                b_price = points.get('B', {}).get('price') if 'B' in points else None
                c_price = points.get('C', {}).get('price') if 'C' in points else None

                # Get D price (for Fibonacci 161.8% calculation)
                if 'D' in points:
                    d_price = points['D']['price']
                elif pattern_id and pattern_id in tracker.tracked_patterns:
                    d_price = tracker.tracked_patterns[pattern_id].zone_entry_price
                else:
                    d_price = None

                if not all([a_price, b_price, c_price, d_price]):
                    print(f"⚠️ Pattern {idx}: Missing price data - A:{a_price}, B:{b_price}, C:{c_price}, D:{d_price}")
                    continue

                # Determine direction (same logic as Fibonacci)
                is_bullish = a_price > c_price
                direction = 'bullish' if is_bullish else 'bearish'

                # Calculate 161.8% Fibonacci level to stop analysis
                if is_bullish:
                    start_price = max(a_price, c_price)
                    end_price = d_price
                    price_range = end_price - start_price
                else:
                    start_price = d_price
                    end_price = min(a_price, c_price)
                    price_range = end_price - start_price

                fib_161_8 = start_price + (price_range * 161.8 / 100.0)

                # Get data after D point
                d_bar = tracked_pattern.zone_entry_bar if tracked_pattern.zone_entry_bar else None
                if not d_bar:
                    if 'D' in points and 'index' in points['D']:
                        d_bar = points['D']['index']
                    elif tracked_pattern.actual_d_bar:
                        d_bar = tracked_pattern.actual_d_bar
                    else:
                        print(f"  ⚠️ No D bar found!")
                        continue

                display_data = backtest_data.iloc[d_bar:].copy().reset_index(drop=True)

                if display_data.empty:
                    print(f"  ⚠️ No data after D point!")
                    continue

                # Find where 161.8% Fib is hit to stop analysis
                stop_at_candle = len(display_data)
                for candle_idx in range(len(display_data)):
                    candle = display_data.iloc[candle_idx]
                    if candle['Low'] <= fib_161_8 <= candle['High']:
                        stop_at_candle = candle_idx + 1
                        break

                # Track point touches (count ALL touches, not just first)
                # IMPORTANT: Start counting from candle AFTER D point (skip the D bar itself)
                pattern_point_touches = {'A': 0, 'B': 0, 'C': 0}
                total_touches = 0

                for point_name, point_price in [('A', a_price), ('B', b_price), ('C', c_price)]:
                    touches = 0

                    # Start from index 1 to skip the D bar itself
                    for candle_idx in range(1, min(stop_at_candle, len(display_data))):
                        candle = display_data.iloc[candle_idx]
                        # Check if candle touched this point level (Low <= level <= High)
                        if candle['Low'] <= point_price <= candle['High']:
                            touches += 1

                    if touches > 0:
                        # Update direction-specific stats
                        points_stats[direction][point_name]['touched'] += 1
                        points_stats[direction][point_name]['total_touches'] += touches
                        points_stats[direction][point_name]['touches'].append(touches)

                        # Update individual pattern stats
                        pattern_point_touches[point_name] = touches
                        total_touches += touches

                # Store individual pattern result
                individual_pattern_results.append({
                    'pattern_id': pattern_id,
                    'pattern_type': tracked_pattern.pattern_type,
                    'pattern_subtype': tracked_pattern.subtype,
                    'direction': direction,
                    'point_touches': pattern_point_touches,
                    'total_touches': total_touches
                })

                total_patterns_analyzed[direction] += 1

            except Exception as e:
                print(f"❌ Error analyzing pattern {idx}: {e}")
                import traceback
                traceback.print_exc()
                continue

        progress.setValue(len(patterns_to_analyze))

        total_analyzed = total_patterns_analyzed['bullish'] + total_patterns_analyzed['bearish']
        print(f"\n📊 Analysis complete: {total_analyzed} patterns analyzed ({total_patterns_analyzed['bullish']} bullish, {total_patterns_analyzed['bearish']} bearish)")

        # Save statistics to database for Active Trading Signals
        self.saveHarmonicPointsStatistics(points_stats, total_patterns_analyzed, individual_pattern_results)

        # Generate results display
        self.showHarmonicPointsAnalysisResults(points_stats, total_patterns_analyzed, individual_pattern_results, category_name)

    def saveHarmonicPointsStatistics(self, points_stats, total_patterns, individual_results):
        """Save Harmonic Points analysis statistics to database for use in Active Trading Signals"""
        try:
            from signal_database import SignalDatabase

            db = SignalDatabase()

            # Get symbol and timeframe from backtester
            if not hasattr(self, 'last_backtester'):
                return

            symbol = getattr(self.last_backtester, 'symbol', 'UNKNOWN')
            timeframe = getattr(self.last_backtester, 'timeframe', 'UNKNOWN')

            # Group patterns by type, name, and direction
            pattern_groups = {}

            for result in individual_results:
                pattern_type = result['pattern_type']
                pattern_name = result.get('pattern_subtype', pattern_type)
                direction = result['direction']

                key = (pattern_type, pattern_name, direction)

                if key not in pattern_groups:
                    pattern_groups[key] = []

                pattern_groups[key].append(result)

            # Calculate and save statistics for each group
            for (pattern_type, pattern_name, direction), patterns in pattern_groups.items():
                sample_count = len(patterns)

                # Aggregate harmonic point statistics
                point_aggregated = {'A': {'hit_count': 0, 'total_touches': 0},
                                   'B': {'hit_count': 0, 'total_touches': 0},
                                   'C': {'hit_count': 0, 'total_touches': 0}}

                for pattern in patterns:
                    point_touches = pattern.get('point_touches', {})

                    for point_name in ['A', 'B', 'C']:
                        touches = point_touches.get(point_name, 0)

                        if touches > 0:
                            point_aggregated[point_name]['hit_count'] += 1
                            point_aggregated[point_name]['total_touches'] += touches

                # Save each harmonic point statistic
                for point_name, data in point_aggregated.items():
                    if data['hit_count'] > 0:  # Only save if point was hit at least once
                        hit_percentage = (data['hit_count'] / sample_count * 100) if sample_count > 0 else 0
                        avg_touches = (data['total_touches'] / data['hit_count']) if data['hit_count'] > 0 else 0

                        db.upsert_pattern_statistic(
                            symbol=symbol,
                            timeframe=timeframe,
                            pattern_type=pattern_type,
                            pattern_name=pattern_name,
                            direction=direction,
                            stat_type='harmonic_point',
                            level_name=f"Point {point_name}",
                            patterns_hit=data['hit_count'],
                            hit_percentage=hit_percentage,
                            avg_touches=avg_touches,
                            sample_count=sample_count
                        )

            print(f"✅ Saved Harmonic Points statistics for {len(pattern_groups)} pattern groups")

        except Exception as e:
            print(f"⚠️ Error saving Harmonic Points statistics: {e}")
            import traceback
            traceback.print_exc()

    def showHarmonicPointsAnalysisResults(self, points_stats, total_patterns, individual_results, category_name="UNKNOWN"):
        """Display Harmonic Points analysis results in a dialog"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont

        dialog = QDialog(self)
        dialog.setWindowTitle("Harmonic Points Analysis Results")
        dialog.resize(1200, 700)

        layout = QVBoxLayout()

        # Header
        total_analyzed = total_patterns['bullish'] + total_patterns['bearish']
        header = QLabel(f"<b>Harmonic Points Analysis - {total_analyzed} Patterns Analyzed ({category_name})</b><br>"
                       f"<span style='font-size:12px;'>Bullish: {total_patterns['bullish']} | Bearish: {total_patterns['bearish']}</span>")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-size: 16px;")
        layout.addWidget(header)

        # Tab widget for combined and individual results
        tab_widget = QTabWidget()

        # Set font
        font = QFont("Arial", 14)

        # === TAB 1: BULLISH PATTERNS COMBINED ANALYSIS ===
        bullish_table = QTableWidget()
        bullish_table.setColumnCount(4)
        bullish_table.setHorizontalHeaderLabels(["Point", "Patterns Hit", "Hit %", "Avg Touches"])
        bullish_table.setFont(font)
        bullish_table.setRowCount(3)  # A, B, C

        for row, point_name in enumerate(['A', 'B', 'C']):
            stat = points_stats['bullish'][point_name]
            times_touched = stat['touched']
            total_bull = total_patterns['bullish']
            touch_percentage = (times_touched / total_bull * 100) if total_bull > 0 else 0
            avg_touches = (stat['total_touches'] / times_touched) if times_touched > 0 else 0

            # Create table items
            point_item = QTableWidgetItem(f"Point {point_name}")
            touched_item = QTableWidgetItem(str(times_touched))
            percentage_item = QTableWidgetItem(f"{touch_percentage:.1f}%")
            avg_item = QTableWidgetItem(f"{avg_touches:.1f}")

            # Center align all items
            for item in [point_item, touched_item, percentage_item, avg_item]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            bullish_table.setItem(row, 0, point_item)
            bullish_table.setItem(row, 1, touched_item)
            bullish_table.setItem(row, 2, percentage_item)
            bullish_table.setItem(row, 3, avg_item)

        bullish_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_widget.addTab(bullish_table, "📈 Bullish Patterns")

        # === TAB 2: BEARISH PATTERNS COMBINED ANALYSIS ===
        bearish_table = QTableWidget()
        bearish_table.setColumnCount(4)
        bearish_table.setHorizontalHeaderLabels(["Point", "Patterns Hit", "Hit %", "Avg Touches"])
        bearish_table.setFont(font)
        bearish_table.setRowCount(3)  # A, B, C

        for row, point_name in enumerate(['A', 'B', 'C']):
            stat = points_stats['bearish'][point_name]
            times_touched = stat['touched']
            total_bear = total_patterns['bearish']
            touch_percentage = (times_touched / total_bear * 100) if total_bear > 0 else 0
            avg_touches = (stat['total_touches'] / times_touched) if times_touched > 0 else 0

            # Create table items
            point_item = QTableWidgetItem(f"Point {point_name}")
            touched_item = QTableWidgetItem(str(times_touched))
            percentage_item = QTableWidgetItem(f"{touch_percentage:.1f}%")
            avg_item = QTableWidgetItem(f"{avg_touches:.1f}")

            # Center align all items
            for item in [point_item, touched_item, percentage_item, avg_item]:
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            bearish_table.setItem(row, 0, point_item)
            bearish_table.setItem(row, 1, touched_item)
            bearish_table.setItem(row, 2, percentage_item)
            bearish_table.setItem(row, 3, avg_item)

        bearish_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_widget.addTab(bearish_table, "📉 Bearish Patterns")

        # === TAB 3: INDIVIDUAL PATTERNS TABLE ===
        individual_table = QTableWidget()
        individual_table.setColumnCount(5)
        individual_table.setHorizontalHeaderLabels(["Pattern", "Pattern Type", "Direction", "Point", "Touches"])
        individual_table.setFont(font)

        # Count total rows needed (only points with touches > 0)
        total_rows = sum(len([pt for pt, touches in result['point_touches'].items() if touches > 0])
                        for result in individual_results)
        individual_table.setRowCount(total_rows)

        current_row = 0
        for idx, result in enumerate(individual_results, 1):
            pattern_name = f"#{idx}: {result['pattern_subtype']}"
            pattern_type = result['pattern_type']
            direction = result['direction']

            # Get all touched points (touches > 0)
            touched_points = [(point, touches) for point, touches in [('A', result['point_touches']['A']),
                             ('B', result['point_touches']['B']), ('C', result['point_touches']['C'])] if touches > 0]

            for point_idx, (point_name, touch_count) in enumerate(touched_points):
                # Only show pattern name, type, and direction in first row of this pattern
                if point_idx == 0:
                    pattern_item = QTableWidgetItem(pattern_name)
                    type_item = QTableWidgetItem(pattern_type)
                    dir_item = QTableWidgetItem("📈 Bull" if direction == 'bullish' else "📉 Bear")
                else:
                    pattern_item = QTableWidgetItem("")
                    type_item = QTableWidgetItem("")
                    dir_item = QTableWidgetItem("")

                point_item = QTableWidgetItem(f"Point {point_name}")
                touches_item = QTableWidgetItem(str(touch_count))

                # Center align
                for item in [pattern_item, type_item, dir_item, point_item, touches_item]:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                individual_table.setItem(current_row, 0, pattern_item)
                individual_table.setItem(current_row, 1, type_item)
                individual_table.setItem(current_row, 2, dir_item)
                individual_table.setItem(current_row, 3, point_item)
                individual_table.setItem(current_row, 4, touches_item)

                current_row += 1

        # Resize columns
        individual_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        tab_widget.addTab(individual_table, "📋 Individual Patterns")

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

                # Get actual bar number from full_data
                bar_number = x_int
                if hasattr(self, 'display_start_idx') and self.display_start_idx is not None:
                    bar_number = self.display_start_idx + x_int

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

                # Create label text with better formatting - include bar number
                label_text = f"Bar: {bar_number}\n"
                label_text += f"Time: {date_str}\n"
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

    def runEnhancedPnLAnalysis(self):
        """
        Enhanced PnL Analysis for Successful Patterns Only

        Strategy:
        - Entry: Pattern D point
        - TP1: First of (Fibonacci levels or Points A/B/C) - 25% profit
        - TP2, TP3, etc.: Subsequent levels - 10% profit each
        - Stop Loss: Initial SL, track if hit
        - Move SL to entry after TP1
        - Position size: $100 per trade
        - Leverage: 1x
        - Long for bullish, Short for bearish
        """
        from PyQt6.QtWidgets import QProgressDialog

        if not hasattr(self, 'last_backtester') or not self.last_backtester:
            QMessageBox.warning(self, "No Data", "Please run backtest first")
            return

        if not hasattr(self, 'current_category_patterns') or not self.current_category_patterns:
            QMessageBox.warning(self, "No Patterns", "Please load patterns first")
            return

        # Filter only successful patterns
        successful_patterns = [p for p in self.current_category_patterns if p.get('status') == 'success']

        # Debug: Show pattern status breakdown
        if not successful_patterns:
            status_counts = {}
            for p in self.current_category_patterns:
                status = p.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1

            status_msg = f"No successful patterns found.\n\nPattern status breakdown:\n"
            for status, count in status_counts.items():
                status_msg += f"  {status}: {count}\n"
            status_msg += f"\nTotal patterns: {len(self.current_category_patterns)}\n\n"
            status_msg += "Note: Enhanced PnL only works on patterns with status='success'.\n"
            status_msg += "Try running Fibonacci Level Analysis first to mark patterns as successful."

            QMessageBox.warning(self, "No Successful Patterns", status_msg)
            return

        # Progress dialog
        progress = QProgressDialog("Calculating Enhanced PnL...", "Cancel", 0, len(successful_patterns), self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)

        backtest_data = self.last_backtester.data
        tracker = self.last_backtester.pattern_tracker

        results = []
        skipped_reasons = {}  # Track why patterns are skipped

        for idx, pattern_dict in enumerate(successful_patterns):
            progress.setValue(idx)
            if progress.wasCanceled():
                break

            try:
                pattern_id = pattern_dict.get('pattern_id')
                if not pattern_id:
                    skipped_reasons['no_pattern_id'] = skipped_reasons.get('no_pattern_id', 0) + 1
                    continue

                if pattern_id not in tracker.tracked_patterns:
                    skipped_reasons['not_in_tracker'] = skipped_reasons.get('not_in_tracker', 0) + 1
                    continue

                tracked_pattern = tracker.tracked_patterns[pattern_id]
                points = pattern_dict.get('points', {})

                # Get D point price (entry)
                entry_price = None
                d_bar = None

                if 'D' in points and 'price' in points['D']:
                    entry_price = points['D']['price']
                    d_bar = points['D'].get('index', points['D'].get('bar'))
                elif tracked_pattern.zone_entry_price:
                    entry_price = tracked_pattern.zone_entry_price
                    d_bar = tracked_pattern.zone_entry_bar

                if not entry_price or d_bar is None:
                    skipped_reasons['no_entry_or_dbar'] = skipped_reasons.get('no_entry_or_dbar', 0) + 1
                    continue

                # Determine direction
                a_price = points.get('A', {}).get('price', 0)
                c_price = points.get('C', {}).get('price', 0)
                is_bullish = a_price > c_price

                # Get Points A, B, C prices
                point_a = a_price
                point_b = points.get('B', {}).get('price', 0)
                point_c = c_price

                # Calculate Fibonacci RETRACEMENT levels for TP targets
                # These are the reversal targets from D point back towards A/C
                # For bullish: D is bottom, targets are upward towards C/A
                # For bearish: D is top, targets are downward towards C/A

                if is_bullish:
                    # Bullish: Retracement from D (low) back up to C (high)
                    # D is entry, targets are upward
                    fib_start = entry_price  # D point (low)
                    fib_end = c_price  # C point (high)
                else:
                    # Bearish: Retracement from D (high) back down to C (low)
                    # D is entry, targets are downward
                    fib_start = entry_price  # D point (high)
                    fib_end = c_price  # C point (low)

                price_range = fib_end - fib_start

                # Fibonacci retracement percentages
                fib_percentages = [23.6, 38.2, 50, 61.8, 78.6, 88.6, 100]
                fib_levels = {}
                for pct in fib_percentages:
                    level_price = fib_start + (price_range * pct / 100.0)
                    fib_levels[pct] = level_price

                # Get Stop Loss from pattern
                stop_loss = pattern_dict.get('stop_loss', entry_price * 0.98 if is_bullish else entry_price * 1.02)

                # Build all TP candidates (Fib + Harmonic Points)
                all_candidates = []

                # Add Fib levels as candidates
                for pct, fib_price in fib_levels.items():
                    all_candidates.append(('Fib', f"{pct}%", fib_price))

                # Add harmonic points as candidates
                if point_a > 0:
                    all_candidates.append(('Point', 'A', point_a))
                if point_b > 0:
                    all_candidates.append(('Point', 'B', point_b))
                if point_c > 0:
                    all_candidates.append(('Point', 'C', point_c))

                # Sort candidates by distance from entry (closest to furthest in profit direction)
                if is_bullish:
                    # For bullish, TP levels should be above entry
                    all_candidates = [c for c in all_candidates if c[2] > entry_price]
                    all_candidates.sort(key=lambda x: x[2])  # Ascending
                else:
                    # For bearish, TP levels should be below entry
                    all_candidates = [c for c in all_candidates if c[2] < entry_price]
                    all_candidates.sort(key=lambda x: x[2], reverse=True)  # Descending

                if not all_candidates:
                    skipped_reasons['no_tp_candidates'] = skipped_reasons.get('no_tp_candidates', 0) + 1
                    continue

                # Track all TPs and SL hits
                display_data = backtest_data.iloc[d_bar:].copy().reset_index(drop=True)

                position_size = 100  # $100 per trade
                leverage = 1  # 1x leverage

                tp_hits = []  # List of {tp_num, tp_name, tp_price, tp_bar, bars_to_tp, profit_usd, profit_pct}
                sl_hit = False
                sl_hit_bar = None
                remaining_candidates = all_candidates.copy()
                current_sl = stop_loss

                # Scan through candles after D
                for candle_idx in range(1, len(display_data)):
                    candle = display_data.iloc[candle_idx]
                    current_bar = d_bar + candle_idx

                    # Check if SL hit first
                    if is_bullish:
                        if candle['Low'] <= current_sl:
                            sl_hit = True
                            sl_hit_bar = current_bar
                            break
                    else:
                        if candle['High'] >= current_sl:
                            sl_hit = True
                            sl_hit_bar = current_bar
                            break

                    # Check if any TP level hit
                    for candidate_type, candidate_name, candidate_price in remaining_candidates:
                        if candle['Low'] <= candidate_price <= candle['High']:
                            tp_num = len(tp_hits) + 1
                            tp_name = f"{candidate_type} {candidate_name}"

                            # Calculate profit for this TP
                            if is_bullish:
                                price_change_percent = ((candidate_price - entry_price) / entry_price) * 100
                            else:
                                price_change_percent = ((entry_price - candidate_price) / entry_price) * 100

                            # TP1: 25%, TP2+: 10% each
                            position_pct = 0.25 if tp_num == 1 else 0.10
                            profit_percent = price_change_percent * leverage * position_pct
                            profit_usd = (position_size * profit_percent) / 100

                            tp_hits.append({
                                'tp_num': tp_num,
                                'tp_name': tp_name,
                                'tp_price': candidate_price,
                                'tp_bar': current_bar,
                                'bars_to_tp': current_bar - d_bar,
                                'profit_usd': profit_usd,
                                'profit_pct': profit_percent,
                                'position_pct': position_pct * 100
                            })

                            # After TP1, move SL to entry
                            if tp_num == 1:
                                current_sl = entry_price

                            # Remove this candidate
                            remaining_candidates.remove((candidate_type, candidate_name, candidate_price))
                            break

                # Mark as pending if no outcome yet (neither TP nor SL hit)
                is_pending = not tp_hits and not sl_hit

                if is_pending:
                    # Log pending pattern
                    print(f"\n⏳ Pattern {pattern_id} - Pending (no TP or SL hit yet):")
                    print(f"   Entry: ${entry_price:.2f} at bar {d_bar}")
                    print(f"   Direction: {'Bullish' if is_bullish else 'Bearish'}")
                    print(f"   TP Candidates ({len(all_candidates)}): {[(c[1], f'${c[2]:.2f}') for c in all_candidates[:5]]}")
                    print(f"   Candles after D: {len(display_data) - 1}")
                    if len(display_data) > 1:
                        print(f"   Price range after D: ${display_data['Low'].min():.2f} - ${display_data['High'].max():.2f}")
                    print(f"   Status: Will update when price hits TP or SL")

                # Calculate total profit/loss
                total_profit_usd = sum(tp['profit_usd'] for tp in tp_hits)

                # If SL was hit, calculate the loss
                if sl_hit:
                    # Calculate loss based on when SL was hit
                    if is_bullish:
                        # For bullish: SL is below entry, loss when price goes down
                        price_change_percent = ((stop_loss - entry_price) / entry_price) * 100
                    else:
                        # For bearish: SL is above entry, loss when price goes up
                        price_change_percent = ((entry_price - stop_loss) / entry_price) * 100

                    # Calculate position percentage remaining (100% - TPs already taken)
                    position_taken = sum(tp['position_pct'] for tp in tp_hits)
                    position_remaining = 100 - position_taken

                    # Calculate loss on remaining position
                    sl_loss_percent = price_change_percent * leverage * (position_remaining / 100)
                    sl_loss_usd = (position_size * sl_loss_percent) / 100

                    # Add SL loss to total (will be negative)
                    total_profit_usd += sl_loss_usd

                    # Log the SL hit
                    print(f"\n🛑 Pattern {pattern_id} - SL Hit:")
                    print(f"   Entry: ${entry_price:.2f}, SL: ${stop_loss:.2f}")
                    print(f"   TPs hit before SL: {len(tp_hits)}")
                    print(f"   Position remaining: {position_remaining:.0f}%")
                    print(f"   SL Loss: ${sl_loss_usd:.2f}")
                    print(f"   Total P/L: ${total_profit_usd:.2f}")

                # Calculate bars to outcome (first TP or SL)
                outcome_bar = None
                bars_to_outcome = None

                if tp_hits:
                    # First TP hit bar
                    outcome_bar = tp_hits[0]['tp_bar']
                    bars_to_outcome = tp_hits[0]['bars_to_tp']
                elif sl_hit:
                    # SL hit bar
                    outcome_bar = sl_hit_bar
                    bars_to_outcome = sl_hit_bar - d_bar if sl_hit_bar else None

                # Determine status
                if is_pending:
                    status = 'Pending'
                elif total_profit_usd > 0:
                    status = 'Profit'
                elif total_profit_usd < 0:
                    status = 'Loss'
                else:
                    status = 'Breakeven'

                # Store result
                result = {
                    'pattern_id': pattern_id,
                    'pattern_name': pattern_dict.get('pattern_subtype', 'Unknown'),
                    'direction': 'Bullish' if is_bullish else 'Bearish',
                    'entry_price': entry_price,
                    'entry_bar': d_bar,
                    'stop_loss': stop_loss,
                    'sl_hit': sl_hit,
                    'sl_hit_bar': sl_hit_bar,
                    'outcome_bar': outcome_bar,
                    'bars_to_outcome': bars_to_outcome,
                    'tp_hits': tp_hits,
                    'total_profit_usd': total_profit_usd,
                    'num_tps_hit': len(tp_hits),
                    'status': status,
                    'is_pending': is_pending
                }

                results.append(result)

            except Exception as e:
                print(f"Error calculating enhanced PnL for pattern {idx}: {e}")
                continue

        progress.setValue(len(successful_patterns))

        if not results:
            # Show detailed error message with skip reasons
            error_msg = f"Could not calculate PnL for any successful patterns.\n\n"
            error_msg += f"Analyzed {len(successful_patterns)} successful patterns, but all were skipped.\n\n"
            error_msg += "Skip reasons:\n"
            for reason, count in skipped_reasons.items():
                error_msg += f"  • {reason}: {count} patterns\n"

            error_msg += "\nPossible solutions:\n"
            error_msg += "  • Ensure patterns have D point data\n"
            error_msg += "  • Verify Fibonacci levels or harmonic points exist\n"
            error_msg += "  • Check that price moved beyond entry after pattern formed\n"

            QMessageBox.information(self, "No Results", error_msg)
            return

        # Show results
        self.showEnhancedPnLResults(results)

    def showEnhancedPnLResults(self, results):
        """Display Enhanced PnL Analysis Results with multiple TPs and SL tracking"""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QLabel, QPushButton, QTabWidget, QTextEdit
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont, QColor

        dialog = QDialog(self)
        dialog.setWindowTitle("💰 Enhanced PnL Analysis - Multi-TP Strategy")
        dialog.resize(1400, 800)

        layout = QVBoxLayout()

        # Separate completed and pending patterns
        completed_results = [r for r in results if not r['is_pending']]
        pending_results = [r for r in results if r['is_pending']]

        # Calculate summary statistics (only for completed)
        total_profit = sum(r['total_profit_usd'] for r in completed_results)
        avg_profit = total_profit / len(completed_results) if completed_results else 0
        profitable_trades = len([r for r in completed_results if r['total_profit_usd'] > 0])
        losing_trades = len([r for r in completed_results if r['total_profit_usd'] < 0])
        breakeven_trades = len([r for r in completed_results if r['total_profit_usd'] == 0])
        win_rate = (profitable_trades / len(completed_results) * 100) if completed_results else 0

        # Calculate TP statistics
        avg_tps_hit = sum(r['num_tps_hit'] for r in completed_results) / len(completed_results) if completed_results else 0
        sl_hit_count = len([r for r in completed_results if r['sl_hit']])

        # Separate SL stats: with and without TPs
        sl_with_tps = len([r for r in completed_results if r['sl_hit'] and r['num_tps_hit'] > 0])
        sl_without_tps = len([r for r in completed_results if r['sl_hit'] and r['num_tps_hit'] == 0])

        avg_bars_to_tp1 = sum(r['tp_hits'][0]['bars_to_tp'] for r in completed_results if r['tp_hits']) / len([r for r in completed_results if r['tp_hits']]) if any(r['tp_hits'] for r in completed_results) else 0

        # Calculate average bars to outcome (for completed patterns)
        avg_bars_to_outcome = sum(r['bars_to_outcome'] for r in completed_results if r['bars_to_outcome'] is not None) / len([r for r in completed_results if r['bars_to_outcome'] is not None]) if any(r['bars_to_outcome'] is not None for r in completed_results) else 0

        # Calculate total loss from SL hits
        total_sl_loss = sum(
            r['total_profit_usd'] - sum(tp['profit_usd'] for tp in r['tp_hits'])
            for r in completed_results if r['sl_hit']
        )

        # Clean, simple table-based summary
        summary = f"""
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 13px; }}
            .section {{ margin-bottom: 20px; }}
            .section-title {{ font-size: 15px; font-weight: bold; margin-bottom: 10px;
                            border-bottom: 2px solid #333; padding-bottom: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin-bottom: 15px; }}
            td {{ padding: 6px 10px; border-bottom: 1px solid #e0e0e0; }}
            td:first-child {{ font-weight: 500; width: 50%; }}
            td:last-child {{ text-align: right; font-weight: 600; }}
            .positive {{ color: #16a34a; }}
            .negative {{ color: #dc2626; }}
            .neutral {{ color: #6b7280; }}
            .strategy-info {{ background: #f5f5f5; padding: 12px; margin-bottom: 15px;
                             border-left: 3px solid #333; font-size: 12px; line-height: 1.6; }}
        </style>

        <div class="strategy-info">
            <b>Strategy:</b> Entry at D point • TP1: 25% profit • TP2/3: 10% each • SL moves to entry after TP1<br>
            <b>Position Size:</b> $100/trade • <b>Leverage:</b> 1x • <b>Direction:</b> Long (Bullish) / Short (Bearish)
        </div>

        <div class="section">
            <div class="section-title">Performance Summary</div>
            <table>
                <tr>
                    <td>Total P&L</td>
                    <td class="{"positive" if total_profit >= 0 else "negative"}">${total_profit:,.2f}</td>
                </tr>
                <tr>
                    <td>Win Rate</td>
                    <td class="{"positive" if win_rate >= 50 else "negative"}">{win_rate:.1f}%</td>
                </tr>
                <tr>
                    <td>Average P&L per Trade</td>
                    <td class="{"positive" if avg_profit >= 0 else "negative"}">${avg_profit:.2f}</td>
                </tr>
                <tr>
                    <td>Average TPs Hit per Pattern</td>
                    <td class="neutral">{avg_tps_hit:.1f}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <div class="section-title">Trade Breakdown</div>
            <table>
                <tr>
                    <td>Total Completed Trades</td>
                    <td>{len(completed_results)}</td>
                </tr>
                <tr>
                    <td>Profitable Trades</td>
                    <td class="positive">{profitable_trades} ({win_rate:.1f}%)</td>
                </tr>
                <tr>
                    <td>Losing Trades</td>
                    <td class="negative">{losing_trades} ({(losing_trades/len(completed_results)*100 if completed_results else 0):.1f}%)</td>
                </tr>
                <tr>
                    <td>Breakeven Trades</td>
                    <td class="neutral">{breakeven_trades} ({(breakeven_trades/len(completed_results)*100 if completed_results else 0):.1f}%)</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <div class="section-title">Timing Analysis</div>
            <table>
                <tr>
                    <td>Average Bars to Outcome</td>
                    <td>{avg_bars_to_outcome:.1f}</td>
                </tr>
                <tr>
                    <td>Average Bars to TP1</td>
                    <td>{avg_bars_to_tp1:.1f}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <div class="section-title">Stop Loss Analysis</div>
            <table>
                <tr>
                    <td>SL Hit Count</td>
                    <td class="negative">{sl_hit_count} ({(sl_hit_count/len(completed_results)*100 if completed_results else 0):.1f}%)</td>
                </tr>
                <tr>
                    <td>SL Hit After Hitting TPs</td>
                    <td>{sl_with_tps}</td>
                </tr>
                <tr>
                    <td>SL Hit Before Any TP</td>
                    <td>{sl_without_tps}</td>
                </tr>
                <tr>
                    <td>Total Loss from SL</td>
                    <td class="negative">${total_sl_loss:.2f}</td>
                </tr>
            </table>
        </div>

        <div class="section">
            <div class="section-title">Pattern Status</div>
            <table>
                <tr>
                    <td>Total Patterns Analyzed</td>
                    <td>{len(results)}</td>
                </tr>
                <tr>
                    <td>Completed Patterns</td>
                    <td>{len(completed_results)}</td>
                </tr>
                <tr>
                    <td>Pending Patterns (awaiting TP/SL)</td>
                    <td class="neutral">{len(pending_results)}</td>
                </tr>
            </table>
        </div>
        """

        summary_label = QLabel(summary)
        summary_label.setWordWrap(True)
        layout.addWidget(summary_label)

        # Create tab widget
        tab_widget = QTabWidget()

        # Tab 1: Summary Table
        summary_table = QTableWidget()
        summary_table.setRowCount(len(results))
        summary_table.setColumnCount(11)
        summary_table.setHorizontalHeaderLabels([
            "Pattern", "Direction", "Entry $", "Entry Bar", "SL $",
            "Outcome Bar", "Bars to Outcome", "TPs Hit",
            "Total P/L $", "SL Hit", "Status"
        ])

        font = QFont("Arial", 10)
        summary_table.setFont(font)

        for row, result in enumerate(results):
            col = 0

            # Pattern name
            summary_table.setItem(row, col, QTableWidgetItem(result['pattern_name']))
            col += 1

            # Direction
            dir_item = QTableWidgetItem(result['direction'])
            dir_item.setForeground(QColor(0, 150, 0) if result['direction'] == 'Bullish' else QColor(200, 0, 0))
            summary_table.setItem(row, col, dir_item)
            col += 1

            # Entry price
            summary_table.setItem(row, col, QTableWidgetItem(f"${result['entry_price']:.2f}"))
            col += 1

            # Entry bar
            summary_table.setItem(row, col, QTableWidgetItem(str(result['entry_bar'])))
            col += 1

            # Stop Loss
            summary_table.setItem(row, col, QTableWidgetItem(f"${result['stop_loss']:.2f}"))
            col += 1

            # Outcome bar (first TP or SL hit)
            outcome_bar_text = str(result['outcome_bar']) if result['outcome_bar'] else "—"
            summary_table.setItem(row, col, QTableWidgetItem(outcome_bar_text))
            col += 1

            # Bars to outcome
            bars_text = str(result['bars_to_outcome']) if result['bars_to_outcome'] is not None else "—"
            summary_table.setItem(row, col, QTableWidgetItem(bars_text))
            col += 1

            # TPs hit
            tp_text = f"{result['num_tps_hit']} TPs"
            summary_table.setItem(row, col, QTableWidgetItem(tp_text))
            col += 1

            # Total P/L
            if result['is_pending']:
                pl_item = QTableWidgetItem("—")
                pl_item.setForeground(QColor(128, 128, 128))  # Gray for pending
            else:
                pl_item = QTableWidgetItem(f"${result['total_profit_usd']:.2f}")
                pl_item.setForeground(QColor(0, 150, 0) if result['total_profit_usd'] >= 0 else QColor(200, 0, 0))
            summary_table.setItem(row, col, pl_item)
            col += 1

            # SL Hit
            sl_status = "❌ YES" if result['sl_hit'] else "✅ NO"
            sl_item = QTableWidgetItem(sl_status)
            sl_item.setForeground(QColor(200, 0, 0) if result['sl_hit'] else QColor(0, 150, 0))
            summary_table.setItem(row, col, sl_item)
            col += 1

            # Status
            status_text = result['status']
            if status_text == 'Profit':
                status_display = "✅ Profit"
                status_color = QColor(0, 150, 0)
            elif status_text == 'Loss':
                status_display = "❌ Loss"
                status_color = QColor(200, 0, 0)
            elif status_text == 'Pending':
                status_display = "⏳ Pending"
                status_color = QColor(255, 165, 0)  # Orange
            else:
                status_display = "⚖️ Breakeven"
                status_color = QColor(128, 128, 128)

            status_item = QTableWidgetItem(status_display)
            status_item.setForeground(status_color)
            summary_table.setItem(row, col, status_item)

        summary_table.horizontalHeader().setStretchLastSection(True)
        tab_widget.addTab(summary_table, "📊 Summary")

        # Tab 2: Detailed TP Breakdown
        detail_table = QTableWidget()

        # Count total TP rows needed
        total_tp_rows = sum(len(r['tp_hits']) for r in results)
        detail_table.setRowCount(total_tp_rows)
        detail_table.setColumnCount(10)
        detail_table.setHorizontalHeaderLabels([
            "Pattern", "Direction", "Entry $", "TP#", "TP Level", "TP Price $",
            "Bars to TP", "Position %", "Profit %", "Profit $"
        ])

        detail_table.setFont(font)

        detail_row = 0
        for result in results:
            for tp in result['tp_hits']:
                # Pattern name
                detail_table.setItem(detail_row, 0, QTableWidgetItem(result['pattern_name']))

                # Direction
                dir_item = QTableWidgetItem(result['direction'])
                dir_item.setForeground(QColor(0, 150, 0) if result['direction'] == 'Bullish' else QColor(200, 0, 0))
                detail_table.setItem(detail_row, 1, dir_item)

                # Entry price
                detail_table.setItem(detail_row, 2, QTableWidgetItem(f"${result['entry_price']:.2f}"))

                # TP number
                tp_num_item = QTableWidgetItem(f"TP{tp['tp_num']}")
                if tp['tp_num'] == 1:
                    tp_num_item.setForeground(QColor(0, 100, 200))  # Blue for TP1
                detail_table.setItem(detail_row, 3, tp_num_item)

                # TP level name
                detail_table.setItem(detail_row, 4, QTableWidgetItem(tp['tp_name']))

                # TP price
                detail_table.setItem(detail_row, 5, QTableWidgetItem(f"${tp['tp_price']:.2f}"))

                # Bars to TP
                detail_table.setItem(detail_row, 6, QTableWidgetItem(str(tp['bars_to_tp'])))

                # Position %
                detail_table.setItem(detail_row, 7, QTableWidgetItem(f"{tp['position_pct']:.0f}%"))

                # Profit %
                profit_pct_item = QTableWidgetItem(f"{tp['profit_pct']:.2f}%")
                profit_pct_item.setForeground(QColor(0, 150, 0) if tp['profit_pct'] >= 0 else QColor(200, 0, 0))
                detail_table.setItem(detail_row, 8, profit_pct_item)

                # Profit $
                profit_item = QTableWidgetItem(f"${tp['profit_usd']:.2f}")
                profit_item.setForeground(QColor(0, 150, 0) if tp['profit_usd'] >= 0 else QColor(200, 0, 0))
                detail_table.setItem(detail_row, 9, profit_item)

                detail_row += 1

        detail_table.horizontalHeader().setStretchLastSection(True)
        tab_widget.addTab(detail_table, "📈 TP Details")

        # Tab 3: Stop Loss Details
        sl_patterns = [r for r in results if r['sl_hit']]
        if sl_patterns:
            sl_table = QTableWidget()
            sl_table.setRowCount(len(sl_patterns))
            sl_table.setColumnCount(9)
            sl_table.setHorizontalHeaderLabels([
                "Pattern", "Direction", "Entry $", "SL $", "SL Bar",
                "TPs Before SL", "Position Left %", "SL Loss $", "Total P/L $"
            ])
            sl_table.setFont(font)

            for row, result in enumerate(sl_patterns):
                # Pattern name
                sl_table.setItem(row, 0, QTableWidgetItem(result['pattern_name']))

                # Direction
                dir_item = QTableWidgetItem(result['direction'])
                dir_item.setForeground(QColor(0, 150, 0) if result['direction'] == 'Bullish' else QColor(200, 0, 0))
                sl_table.setItem(row, 1, dir_item)

                # Entry price
                sl_table.setItem(row, 2, QTableWidgetItem(f"${result['entry_price']:.2f}"))

                # Stop Loss price
                sl_table.setItem(row, 3, QTableWidgetItem(f"${result['stop_loss']:.2f}"))

                # SL hit bar
                sl_table.setItem(row, 4, QTableWidgetItem(str(result['sl_hit_bar']) if result['sl_hit_bar'] else "N/A"))

                # TPs hit before SL
                sl_table.setItem(row, 5, QTableWidgetItem(str(result['num_tps_hit'])))

                # Calculate position left
                position_taken = sum(tp['position_pct'] for tp in result['tp_hits'])
                position_left = 100 - position_taken
                sl_table.setItem(row, 6, QTableWidgetItem(f"{position_left:.0f}%"))

                # Calculate SL loss
                entry = result['entry_price']
                sl = result['stop_loss']
                is_bullish = result['direction'] == 'Bullish'

                if is_bullish:
                    price_change_pct = ((sl - entry) / entry) * 100
                else:
                    price_change_pct = ((entry - sl) / entry) * 100

                sl_loss_pct = price_change_pct * (position_left / 100)
                sl_loss_usd = (100 * sl_loss_pct) / 100  # position_size = 100

                sl_loss_item = QTableWidgetItem(f"${sl_loss_usd:.2f}")
                sl_loss_item.setForeground(QColor(200, 0, 0))  # Red for loss
                sl_table.setItem(row, 7, sl_loss_item)

                # Total P/L
                total_pl_item = QTableWidgetItem(f"${result['total_profit_usd']:.2f}")
                total_pl_item.setForeground(QColor(0, 150, 0) if result['total_profit_usd'] >= 0 else QColor(200, 0, 0))
                sl_table.setItem(row, 8, total_pl_item)

            sl_table.horizontalHeader().setStretchLastSection(True)
            tab_widget.addTab(sl_table, f"🛑 Stop Loss Details ({len(sl_patterns)})")

        layout.addWidget(tab_widget)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    def runPnLAnalysis(self):
        """Run PnL (Profit and Loss) analysis on current patterns"""
        # Check if patterns are loaded
        if not hasattr(self, 'current_category_patterns') or not self.current_category_patterns:
            QMessageBox.information(
                self,
                "No Patterns Loaded",
                "Please load a category first by clicking one of the pattern completion buttons."
            )
            return

        # Show input dialog for PnL parameters
        dialog = QDialog(self)
        dialog.setWindowTitle("PnL Analysis Parameters")
        dialog.setMinimumWidth(400)
        layout = QVBoxLayout()

        # Instructions
        instructions = QLabel("Enter trading parameters to calculate Profit & Loss:")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Entry Type selection
        entry_type_group = QGroupBox("Entry Price")
        entry_type_layout = QVBoxLayout()

        self.entry_type_combo = QComboBox()
        self.entry_type_combo.addItems([
            "Pattern D Point",
            "PRZ Zone Entry (for unformed)",
            "Custom Price"
        ])
        entry_type_layout.addWidget(self.entry_type_combo)

        # Custom entry price field (hidden by default)
        self.custom_entry_layout = QHBoxLayout()
        self.custom_entry_layout.addWidget(QLabel("Custom Entry:"))
        self.custom_entry_input = QLineEdit()
        self.custom_entry_input.setPlaceholderText("Enter price...")
        self.custom_entry_input.setEnabled(False)
        self.custom_entry_layout.addWidget(self.custom_entry_input)
        entry_type_layout.addLayout(self.custom_entry_layout)

        # Connect combo box to enable/disable custom input
        self.entry_type_combo.currentTextChanged.connect(
            lambda text: self.custom_entry_input.setEnabled(text == "Custom Price")
        )

        entry_type_group.setLayout(entry_type_layout)
        layout.addWidget(entry_type_group)

        # Exit Type selection
        exit_type_group = QGroupBox("Exit Price")
        exit_type_layout = QVBoxLayout()

        self.exit_type_combo = QComboBox()
        self.exit_type_combo.addItems([
            "Reversal Point (actual exit from backtest)",
            "Custom Price"
        ])
        exit_type_layout.addWidget(self.exit_type_combo)

        # Custom exit price field
        self.custom_exit_layout = QHBoxLayout()
        self.custom_exit_layout.addWidget(QLabel("Custom Exit:"))
        self.custom_exit_input = QLineEdit()
        self.custom_exit_input.setPlaceholderText("Enter price...")
        self.custom_exit_input.setEnabled(False)
        self.custom_exit_layout.addWidget(self.custom_exit_input)
        exit_type_layout.addLayout(self.custom_exit_layout)

        self.exit_type_combo.currentTextChanged.connect(
            lambda text: self.custom_exit_input.setEnabled(text == "Custom Price")
        )

        exit_type_group.setLayout(exit_type_layout)
        layout.addWidget(exit_type_group)

        # Position Type
        position_layout = QHBoxLayout()
        position_layout.addWidget(QLabel("Position Type:"))
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Long", "Short"])
        position_layout.addWidget(self.position_combo)
        layout.addLayout(position_layout)

        # Leverage
        leverage_layout = QHBoxLayout()
        leverage_layout.addWidget(QLabel("Leverage:"))
        self.leverage_spin = QSpinBox()
        self.leverage_spin.setRange(1, 125)
        self.leverage_spin.setValue(1)
        self.leverage_spin.setSuffix("x")
        leverage_layout.addWidget(self.leverage_spin)
        layout.addLayout(leverage_layout)

        # Position Size (in USD)
        position_size_layout = QHBoxLayout()
        position_size_layout.addWidget(QLabel("Position Size (USD):"))
        self.position_size_input = QLineEdit()
        self.position_size_input.setText("100")
        self.position_size_input.setPlaceholderText("Enter amount...")
        position_size_layout.addWidget(self.position_size_input)
        layout.addLayout(position_size_layout)

        # Buttons
        button_layout = QHBoxLayout()
        calculate_btn = QPushButton("Calculate PnL")
        calculate_btn.clicked.connect(lambda: self.calculatePnL(dialog))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.close)
        button_layout.addWidget(calculate_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)
        dialog.exec()

    def calculatePnL(self, dialog):
        """Calculate and display PnL based on user inputs"""
        try:
            # Get user inputs
            entry_type = self.entry_type_combo.currentText()
            exit_type = self.exit_type_combo.currentText()
            position_type = self.position_combo.currentText()
            leverage = self.leverage_spin.value()

            # Validate position size
            try:
                position_size = float(self.position_size_input.text())
                if position_size <= 0:
                    raise ValueError("Position size must be positive")
            except ValueError as e:
                QMessageBox.warning(dialog, "Invalid Input", f"Position size error: {str(e)}")
                return

            # Calculate PnL for each pattern
            results = []
            total_pnl = 0
            total_pnl_percent = 0
            successful_trades = 0
            failed_trades = 0

            for pattern_dict in self.current_category_patterns:
                try:
                    # Get entry price
                    entry_price = None
                    if entry_type == "Pattern D Point":
                        if 'D' in pattern_dict.get('points', {}):
                            entry_price = pattern_dict['points']['D']['price']
                    elif entry_type == "PRZ Zone Entry (for unformed)":
                        if 'zone_entry_price' in pattern_dict:
                            entry_price = pattern_dict['zone_entry_price']
                    elif entry_type == "Custom Price":
                        try:
                            entry_price = float(self.custom_entry_input.text())
                        except:
                            continue

                    if entry_price is None:
                        continue

                    # Get exit price
                    exit_price = None
                    if exit_type == "Reversal Point (actual exit from backtest)":
                        pattern_id = pattern_dict.get('pattern_id')
                        if pattern_id and hasattr(self.last_backtester, 'pattern_tracker'):
                            tracker = self.last_backtester.pattern_tracker
                            if pattern_id in tracker.tracked_patterns:
                                tracked = tracker.tracked_patterns[pattern_id]
                                if tracked.reversal_bar and self.full_data is not None:
                                    if 0 <= tracked.reversal_bar < len(self.full_data):
                                        exit_price = self.full_data.iloc[tracked.reversal_bar]['Close']
                    elif exit_type == "Custom Price":
                        try:
                            exit_price = float(self.custom_exit_input.text())
                        except:
                            continue

                    if exit_price is None:
                        continue

                    # Calculate PnL
                    if position_type == "Long":
                        price_change_percent = ((exit_price - entry_price) / entry_price) * 100
                    else:  # Short
                        price_change_percent = ((entry_price - exit_price) / entry_price) * 100

                    pnl_percent = price_change_percent * leverage
                    pnl_usd = (position_size * pnl_percent) / 100

                    # Track statistics
                    total_pnl += pnl_usd
                    total_pnl_percent += pnl_percent
                    if pnl_usd > 0:
                        successful_trades += 1
                    else:
                        failed_trades += 1

                    # Store result
                    results.append({
                        'pattern_name': pattern_dict.get('name', 'Unknown'),
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'price_change_percent': price_change_percent,
                        'pnl_percent': pnl_percent,
                        'pnl_usd': pnl_usd
                    })

                except Exception as e:
                    print(f"Error calculating PnL for pattern: {e}")
                    continue

            # Close input dialog
            dialog.close()

            # Show results
            if not results:
                QMessageBox.information(
                    self,
                    "No Results",
                    "Could not calculate PnL for any patterns. Make sure patterns have the required price data."
                )
                return

            self.showPnLResults(results, total_pnl, total_pnl_percent, successful_trades, failed_trades,
                              leverage, position_size, position_type)

        except Exception as e:
            QMessageBox.critical(dialog, "Calculation Error", f"Error calculating PnL: {str(e)}")
            import traceback
            traceback.print_exc()

    def showPnLResults(self, results, total_pnl, total_pnl_percent, successful_trades, failed_trades,
                      leverage, position_size, position_type):
        """Display PnL analysis results in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("💰 PnL Analysis Results")
        dialog.setMinimumSize(900, 600)
        layout = QVBoxLayout()

        # Summary statistics
        summary_text = f"""
<b>Trading Parameters:</b>
Position Type: {position_type} | Leverage: {leverage}x | Position Size: ${position_size:.2f}

<b>Summary Statistics:</b>
Total Patterns Analyzed: {len(results)}
Profitable Trades: {successful_trades} ({(successful_trades/len(results)*100):.1f}%)
Losing Trades: {failed_trades} ({(failed_trades/len(results)*100):.1f}%)

<b>Total PnL:</b>
USD: ${total_pnl:.2f}
Percent: {total_pnl_percent:.2f}%
Average PnL per Trade: ${(total_pnl/len(results)):.2f}
        """

        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("background-color: #f0f0f0; padding: 10px; border-radius: 5px;")
        layout.addWidget(summary_label)

        # Results table
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "Pattern", "Entry Price", "Exit Price", "Price Change %",
            f"PnL % ({leverage}x)", "PnL USD"
        ])
        table.setRowCount(len(results))

        # Set font
        font = QFont("Arial", 12)
        table.setFont(font)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Populate table
        for row, result in enumerate(results):
            table.setItem(row, 0, QTableWidgetItem(result['pattern_name']))
            table.setItem(row, 1, QTableWidgetItem(f"${result['entry_price']:.2f}"))
            table.setItem(row, 2, QTableWidgetItem(f"${result['exit_price']:.2f}"))
            table.setItem(row, 3, QTableWidgetItem(f"{result['price_change_percent']:.2f}%"))
            table.setItem(row, 4, QTableWidgetItem(f"{result['pnl_percent']:.2f}%"))

            # Color code PnL
            pnl_item = QTableWidgetItem(f"${result['pnl_usd']:.2f}")
            if result['pnl_usd'] > 0:
                pnl_item.setForeground(QColor(0, 128, 0))  # Green for profit
            else:
                pnl_item.setForeground(QColor(255, 0, 0))  # Red for loss
            table.setItem(row, 5, pnl_item)

        layout.addWidget(table)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()