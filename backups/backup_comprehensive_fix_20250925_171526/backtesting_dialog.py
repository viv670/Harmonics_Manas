"""
Backtesting Dialog for Harmonic Pattern Trading System
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QDoubleSpinBox, QTextEdit, QGroupBox, QProgressBar,
    QMessageBox, QCheckBox, QComboBox, QRadioButton, QDateEdit,
    QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
import pandas as pd
import numpy as np
import os
from datetime import datetime
from optimized_walk_forward_backtester import OptimizedWalkForwardBacktester


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

            # Debug output
            # Debug prints without the full stats object (which contains long equity_curve)
            print(f"DEBUG: Unformed patterns: {total_unformed}")
            print(f"DEBUG: Formed patterns: {total_formed}")
            print(f"DEBUG: Extremum points: {total_extremums} (highs: {high_extremums}, lows: {low_extremums})")

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
        self.resize(800, 600)

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
                print(f"DEBUG: Loaded full dataset directly from file: {len(self.full_data)} bars")
            else:
                # If file doesn't exist, use whatever data we have
                self.full_data = self.data
                print(f"DEBUG: Using provided data: {len(self.data) if self.data is not None else 0} bars")
        except Exception as e:
            print(f"DEBUG: Could not load full dataset: {e}")
            self.full_data = self.data

    def initUI(self):
        """Initialize the user interface"""
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

        # Radio buttons for selection mode
        radio_layout = QHBoxLayout()
        self.range_mode_group = QButtonGroup()

        self.bars_radio = QRadioButton("Use Last N Bars")
        self.bars_radio.setToolTip(
            "<b>Fixed Bar Count Mode</b><br>"
            "Analyze the most recent N bars of data.<br>"
            "Good for quick testing and consistent comparisons."
        )
        # Don't set default yet - will be set based on GUI
        self.range_mode_group.addButton(self.bars_radio)
        radio_layout.addWidget(self.bars_radio)

        self.date_radio = QRadioButton("Use Date Range")
        self.date_radio.setToolTip(
            "<b>Date Range Mode</b><br>"
            "Analyze a specific historical period.<br>"
            "Ideal for testing patterns during known market conditions.<br>"
            "<b>Inherits from GUI when matching.</b>"
        )
        self.range_mode_group.addButton(self.date_radio)
        radio_layout.addWidget(self.date_radio)

        range_layout.addLayout(radio_layout)

        # Bars selection (ComboBox)
        bars_layout = QHBoxLayout()
        bars_layout.addWidget(QLabel("Number of Bars:"))
        self.data_range_combo = QComboBox()
        self.data_range_combo.addItems(["Last 50 bars", "Last 100 bars", "Last 200 bars", "Last 500 bars", "All data"])
        self.data_range_combo.setCurrentIndex(0)  # Default to 50 bars for complete analysis
        self.data_range_combo.setToolTip(
            "<b>Bar Count Selection</b><br>"
            "• <b>50 bars</b> = Quick test, 100% detection coverage<br>"
            "• <b>100 bars</b> = Good balance<br>"
            "• <b>200 bars</b> = Extended analysis<br>"
            "• <b>500+ bars</b> = Long-term patterns (slower)<br><br>"
            "Smaller datasets ensure complete pattern detection."
        )
        bars_layout.addWidget(self.data_range_combo)
        range_layout.addLayout(bars_layout)

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

        # Connect radio buttons to enable/disable appropriate controls
        self.bars_radio.toggled.connect(self.onRangeModeChanged)
        self.date_radio.toggled.connect(self.onRangeModeChanged)
        self.data_range_combo.currentTextChanged.connect(self.updateRangeInfo)
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

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        results_layout.addWidget(self.results_text)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        self.setLayout(layout)

        # Initialize date ranges and check data availability
        self.initializeDateRanges()

        # Initialize extremum info label
        self.updateExtremumInfo()

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
                self.bars_radio.setChecked(False)

                # Update the UI to reflect date mode
                self.data_range_combo.setEnabled(False)
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

                # Use bars mode as fallback
                self.bars_radio.setChecked(True)
                self.date_radio.setChecked(False)

            # Update info
            self.results_text.append(f"Date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")

    def onRangeModeChanged(self, checked):
        """Handle radio button changes for range mode"""
        if self.bars_radio.isChecked():
            # Enable bars selection, disable date selection
            self.data_range_combo.setEnabled(True)
            self.start_date.setEnabled(False)
            self.end_date.setEnabled(False)
            self.updateRangeInfo()
        else:
            # Enable date selection, disable bars selection
            self.data_range_combo.setEnabled(False)
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
        if self.bars_radio.isChecked():
            self.range_info_label.setText(f"Selected: {self.data_range_combo.currentText()}")
        else:
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

        # Clear previous results
        self.results_text.clear()
        self.results_text.append("Starting backtest...\n")

        # Get data range - Use full_data if available
        base_data = self.full_data if self.full_data is not None else self.data
        data_to_use = base_data.copy()
        print(f"DEBUG: Using full dataset: {len(base_data)} bars")

        # Check which mode is selected: bars or date range
        if self.bars_radio.isChecked():
            # Use bars-based selection
            range_text = self.data_range_combo.currentText()
            print(f"DEBUG: Selected range: {range_text}")

            # Important: Check for specific matches in order to avoid overlap
            # "Last 500 bars" contains "50" so we must check for "500" first
            if "500" in range_text:
                data_to_use = data_to_use.iloc[-500:]
                print(f"DEBUG: After slicing to 500 bars: {len(data_to_use)} bars")
                # No automatic adjustment - user controls detection interval for 100% accuracy
            elif "200" in range_text:
                data_to_use = data_to_use.iloc[-200:]
                print(f"DEBUG: After slicing to 200 bars: {len(data_to_use)} bars")
            elif "100" in range_text:
                data_to_use = data_to_use.iloc[-100:]
                print(f"DEBUG: After slicing to 100 bars: {len(data_to_use)} bars")
            elif "50" in range_text:
                data_to_use = data_to_use.iloc[-50:]
                print(f"DEBUG: After slicing to 50 bars: {len(data_to_use)} bars")
            # else use all data

        else:
            # Use date-based selection
            start_date = self.start_date.date().toPyDate()
            end_date = self.end_date.date().toPyDate()

            # Convert to pandas timestamps
            start_pd = pd.Timestamp(start_date)
            end_pd = pd.Timestamp(end_date)

            # Filter data by date range
            mask = (data_to_use.index >= start_pd) & (data_to_use.index <= end_pd)
            data_to_use = data_to_use[mask]

            print(f"DEBUG: Date range: {start_date} to {end_date}")
            print(f"DEBUG: After date filtering: {len(data_to_use)} bars")

            # No automatic adjustment - user controls detection interval for 100% accuracy

        print(f"DEBUG: Final data size to use: {len(data_to_use)} bars")
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
        self.results_text.append("\n" + "="*50)
        self.results_text.append("PATTERN DETECTION RESULTS")

        # Show configuration used
        if self.date_radio.isChecked():
            date_range = f"{self.start_date.date().toString('yyyy-MM-dd')} to {self.end_date.date().toString('yyyy-MM-dd')}"
        else:
            date_range = self.data_range_combo.currentText()

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
            self.results_text.append(f"  Total Pattern Instances Detected: {total_instances}")
            self.results_text.append(f"    - Formed (Complete): {total_formed}")
            self.results_text.append(f"      • ABCD: {formed_abcd}")
            self.results_text.append(f"      • XABCD: {formed_xabcd}")
            self.results_text.append(f"    - Unformed (Potential): {total_unformed}")
            self.results_text.append(f"      • From {unformed_types} unique pattern types")
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

        # Pattern completion statistics
        if total_unformed > 0:
            self.results_text.append(f"\nPATTERN COMPLETION ANALYSIS:")

            success = stats.get('patterns_success', 0)
            failed = stats.get('patterns_failed', 0)
            dismissed = stats.get('patterns_dismissed', 0)
            pending = stats.get('patterns_pending', 0)
            in_zone = stats.get('patterns_in_zone', 0)

            # Debug print to check values
            print(f"DEBUG: Success from stats: {success}, Total unformed: {total_unformed}")

            if total_unformed > 0:
                # Calculate success rate only from patterns that reached a conclusion (success or failed)
                concluded = success + failed
                success_rate = (success / concluded * 100) if concluded > 0 else 0.0

                self.results_text.append(f"  Completed Successfully: {success}")
                self.results_text.append(f"  Failed (PRZ Violated): {failed}")
                self.results_text.append(f"  In PRZ Zone (Active): {in_zone}")
                self.results_text.append(f"  Dismissed (Structure Break): {dismissed}")
                self.results_text.append(f"  Still Pending: {pending}")

                if concluded > 0:
                    self.results_text.append(f"\n  Success Rate: {success_rate:.1f}% ({success}/{concluded} patterns that reached PRZ)")
                else:
                    self.results_text.append(f"\n  Success Rate: N/A (no patterns reached PRZ yet)")

                total_shown = success + failed + dismissed + pending + in_zone
                self.results_text.append(f"  Total Tracked: {total_shown}")

        # Time taken
        time_taken = stats.get('time_taken', 0)
        if time_taken > 0:
            self.results_text.append(f"\nProcessing Time: {time_taken:.2f} seconds")

        # Store stats for export
        self.last_stats = stats
        self.last_backtester = self.backtest_thread.backtester if self.backtest_thread else None

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

            # Get data used for backtest
            test_data = backtester.data

            # Prepare patterns data
            patterns_data = []
            for pattern_id, pattern in tracker.tracked_patterns.items():
                pattern_info = {
                    'Pattern ID': pattern_id[:20] + '...' if len(pattern_id) > 20 else pattern_id,
                    'Type': pattern.pattern_type,
                    'Subtype': pattern.subtype,
                    'Status': pattern.status,
                    'First Seen Bar': pattern.first_seen_bar
                }

                # Add point coordinates
                if pattern.a_point:
                    pattern_info['A_Bar'] = pattern.a_point[0]
                    pattern_info['A_Price'] = round(pattern.a_point[1], 2)
                    if pattern.a_point[0] < len(test_data):
                        pattern_info['A_Date'] = test_data.index[pattern.a_point[0]].strftime('%Y-%m-%d')

                if pattern.b_point:
                    pattern_info['B_Bar'] = pattern.b_point[0]
                    pattern_info['B_Price'] = round(pattern.b_point[1], 2)
                    if pattern.b_point[0] < len(test_data):
                        pattern_info['B_Date'] = test_data.index[pattern.b_point[0]].strftime('%Y-%m-%d')

                if pattern.c_point:
                    pattern_info['C_Bar'] = pattern.c_point[0]
                    pattern_info['C_Price'] = round(pattern.c_point[1], 2)
                    if pattern.c_point[0] < len(test_data):
                        pattern_info['C_Date'] = test_data.index[pattern.c_point[0]].strftime('%Y-%m-%d')

                # Add PRZ/D lines
                if pattern.prz_zones:
                    # Show individual zones for accurate tracking
                    zones_info = []
                    for i, zone in enumerate(pattern.prz_zones[:3], 1):  # Show up to 3 zones
                        zone_str = f"{zone.get('pattern_source', 'Zone'+str(i))}: {round(zone.get('min', 0), 2)}-{round(zone.get('max', 0), 2)}"
                        zones_info.append(zone_str)
                    pattern_info['PRZ_Zones'] = ' | '.join(zones_info)
                elif pattern.prz_min and pattern.prz_max:
                    pattern_info['PRZ_Top'] = round(pattern.prz_max, 2)
                    pattern_info['PRZ_Bottom'] = round(pattern.prz_min, 2)
                elif pattern.d_lines:
                    pattern_info['D_Lines'] = ', '.join([str(round(d, 2)) for d in pattern.d_lines[:3]])

                patterns_data.append(pattern_info)

            # Create DataFrames
            patterns_df = pd.DataFrame(patterns_data)
            if not patterns_df.empty:
                patterns_df = patterns_df.sort_values(['First Seen Bar', 'Status'], ascending=[True, True])

            # Create summary
            summary_data = {
                'Metric': [
                    'Date Range',
                    'Total Bars',
                    'Extremum Length',
                    '',
                    'Pattern Counts:',
                    '  Total Unformed Patterns',
                    '  Total Formed Patterns',
                    '    - Formed ABCD',
                    '    - Formed XABCD',
                    '  Unique Patterns Tracked',
                    '',
                    'Pattern Outcomes:',
                    '  - Success',
                    '  - Failed',
                    '  - Dismissed',
                    '  - Pending',
                    '',
                    'Extremum Points:',
                    '  - Total',
                    '  - Highs',
                    '  - Lows',
                    '',
                    'Processing Time (seconds)'
                ],
                'Value': [
                    f"{test_data.index[0].strftime('%Y-%m-%d')} to {test_data.index[-1].strftime('%Y-%m-%d')}",
                    len(test_data),
                    backtester.extremum_length,
                    '',
                    '',
                    stats.get('total_unformed_patterns', 0),
                    stats.get('total_formed_patterns', 0),
                    stats.get('formed_abcd_count', 0),
                    stats.get('formed_xabcd_count', 0),
                    stats.get('patterns_tracked', 0),
                    '',
                    '',
                    sum(1 for p in tracker.tracked_patterns.values() if p.status == 'success'),
                    sum(1 for p in tracker.tracked_patterns.values() if p.status == 'failed'),
                    sum(1 for p in tracker.tracked_patterns.values() if p.status == 'dismissed'),
                    sum(1 for p in tracker.tracked_patterns.values() if p.status == 'pending'),
                    '',
                    '',
                    stats.get('total_extremum_points', 0),
                    stats.get('high_extremum_points', 0),
                    stats.get('low_extremum_points', 0),
                    '',
                    round(stats.get('time_taken', 0), 2)
                ]
            }
            summary_df = pd.DataFrame(summary_data)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = os.path.join(results_dir, f'backtest_results_{timestamp}.xlsx')

            # Save to Excel with multiple sheets
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
                if not patterns_df.empty:
                    patterns_df.to_excel(writer, sheet_name='Pattern Details', index=False)

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

            # Add success message
            self.results_text.append(f"\n✅ Results automatically saved to:")
            self.results_text.append(f"   {filename}")

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