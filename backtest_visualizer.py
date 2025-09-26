"""
Backtest Results Visualization Window
=====================================
Displays backtest results with charts and statistics
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTabWidget, QTextEdit,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QComboBox, QGroupBox, QSplitter,
    QMessageBox, QDateEdit, QCheckBox, QLineEdit,
    QFileDialog, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtGui import QFont, QColor
import pyqtgraph as pg
import pandas as pd
import numpy as np
from typing import Dict, List
import json


class BacktestWorker(QThread):
    """Background worker for running backtests"""
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, data, mode, start_date=None, end_date=None, pattern_filters=None):
        super().__init__()
        self.data = data
        self.mode = mode
        self.start_date = start_date
        self.end_date = end_date
        self.pattern_filters = pattern_filters or {}

    def run(self):
        """Run backtest in background"""
        try:
            from harmonic_backtester import HarmonicBacktester, BacktestMode

            self.status.emit("Initializing backtester...")
            self.progress.emit(10)

            # Filter data by date range if specified
            data_to_test = self.data.copy()
            if self.start_date:
                data_to_test = data_to_test[data_to_test.index >= self.start_date]
            if self.end_date:
                data_to_test = data_to_test[data_to_test.index <= self.end_date]

            if len(data_to_test) < 20:
                self.error.emit("Not enough data in selected date range. Need at least 20 bars.")
                return

            self.status.emit(f"Testing {len(data_to_test)} bars of data...")
            self.progress.emit(20)

            # Map mode string to enum
            mode_map = {
                "snapshot": BacktestMode.SNAPSHOT,
                "evolution": BacktestMode.EVOLUTION,
                "both": BacktestMode.BOTH
            }
            backtest_mode = mode_map.get(self.mode.lower(), BacktestMode.BOTH)

            # Create backtester with filtered data
            backtester = HarmonicBacktester(data_to_test, backtest_mode)

            self.status.emit("Detecting patterns...")
            self.progress.emit(30)

            # Run backtest
            results = backtester.run_backtest()

            # Apply pattern filters if specified
            if self.pattern_filters:
                results = self._filter_results(results, self.pattern_filters)

            self.progress.emit(90)
            self.status.emit("Backtest complete!")
            self.progress.emit(100)

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))

    def _filter_results(self, results, filters):
        """Apply pattern type filters to results"""
        # Filter based on selected pattern types
        filtered_results = results.copy()

        # If specific patterns are selected, filter results
        if filters.get('pattern_types'):
            selected_types = filters['pattern_types']
            if 'results' in filtered_results:
                filtered_results['results'] = [
                    r for r in filtered_results['results']
                    if any(ptype in r.formed_pattern.get('pattern_type', '')
                          for ptype in selected_types)
                ]

        return filtered_results


class BacktestVisualizerWindow(QMainWindow):
    """Window for displaying backtest results"""

    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.data = data
        self.results = None
        self.initUI()

    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle("Harmonic Pattern Backtest Configuration")
        self.setGeometry(100, 100, 1400, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create configuration panel
        config_panel = self.create_config_panel()
        main_layout.addWidget(config_panel)

        # Progress and status
        progress_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready to run backtest")
        progress_layout.addWidget(self.status_label)

        main_layout.addLayout(progress_layout)

        # Create tab widget for results
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Summary Statistics
        self.create_summary_tab()

        # Tab 2: Pattern Performance
        self.create_pattern_performance_tab()

        # Tab 3: Success Rate Chart
        self.create_chart_tab()

        # Tab 4: Detailed Results
        self.create_detailed_results_tab()

        # Tab 5: Raw Output
        self.create_raw_output_tab()

    def create_config_panel(self):
        """Create configuration panel for backtest settings"""
        config_group = QGroupBox("Backtest Configuration")
        config_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)

        config_layout = QGridLayout()

        # Row 0: Data Source Information
        config_layout.addWidget(QLabel("Data Source:"), 0, 0)
        self.data_source_label = QLabel("Current loaded data")
        if self.data is not None:
            data_info = f"{len(self.data)} bars from {self.data.index[0].strftime('%Y-%m-%d')} to {self.data.index[-1].strftime('%Y-%m-%d')}"
            self.data_source_label.setText(data_info)
        config_layout.addWidget(self.data_source_label, 0, 1, 1, 3)

        # Row 1: Date Range Selection
        config_layout.addWidget(QLabel("Test Period:"), 1, 0)

        # Start date
        config_layout.addWidget(QLabel("From:"), 1, 1)
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("yyyy-MM-dd")
        if self.data is not None and len(self.data) > 0:
            self.start_date_edit.setDate(QDate(self.data.index[0].year,
                                               self.data.index[0].month,
                                               self.data.index[0].day))
        config_layout.addWidget(self.start_date_edit, 1, 2)

        # End date
        config_layout.addWidget(QLabel("To:"), 1, 3)
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        if self.data is not None and len(self.data) > 0:
            self.end_date_edit.setDate(QDate(self.data.index[-1].year,
                                            self.data.index[-1].month,
                                            self.data.index[-1].day))
        config_layout.addWidget(self.end_date_edit, 1, 4)

        # Row 2: Use all data checkbox
        self.use_all_data_cb = QCheckBox("Use entire dataset")
        self.use_all_data_cb.setChecked(True)
        self.use_all_data_cb.stateChanged.connect(self.toggle_date_range)
        config_layout.addWidget(self.use_all_data_cb, 2, 1, 1, 2)

        # Initially disable date editors
        self.start_date_edit.setEnabled(False)
        self.end_date_edit.setEnabled(False)

        # Row 3: Backtest Mode Selection
        config_layout.addWidget(QLabel("Backtest Mode:"), 3, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Both", "Snapshot", "Evolution"])
        self.mode_combo.setToolTip("Snapshot: Test patterns at point C\n"
                                  "Evolution: Track pattern changes\n"
                                  "Both: Run both modes")
        config_layout.addWidget(self.mode_combo, 3, 1, 1, 2)

        # Row 4-5: Pattern Type Filters
        config_layout.addWidget(QLabel("Pattern Types:"), 4, 0)

        pattern_filter_layout = QHBoxLayout()
        self.abcd_formed_cb = QCheckBox("Formed ABCD")
        self.abcd_formed_cb.setChecked(True)
        self.xabcd_formed_cb = QCheckBox("Formed XABCD")
        self.xabcd_formed_cb.setChecked(True)
        self.abcd_unformed_cb = QCheckBox("Unformed ABCD")
        self.abcd_unformed_cb.setChecked(True)
        self.xabcd_unformed_cb = QCheckBox("Unformed XABCD")
        self.xabcd_unformed_cb.setChecked(True)

        pattern_filter_layout.addWidget(self.abcd_formed_cb)
        pattern_filter_layout.addWidget(self.xabcd_formed_cb)
        pattern_filter_layout.addWidget(self.abcd_unformed_cb)
        pattern_filter_layout.addWidget(self.xabcd_unformed_cb)

        config_layout.addLayout(pattern_filter_layout, 4, 1, 1, 4)

        # Row 6: Buttons
        button_layout = QHBoxLayout()

        # Load different data button
        self.load_data_btn = QPushButton("Load Different Data")
        self.load_data_btn.clicked.connect(self.load_different_data)
        button_layout.addWidget(self.load_data_btn)

        # Run button
        self.run_btn = QPushButton("Run Backtest")
        self.run_btn.clicked.connect(self.run_backtest)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.run_btn)

        # Export button
        self.export_btn = QPushButton("Export Results")
        self.export_btn.clicked.connect(self.export_results)
        self.export_btn.setEnabled(False)
        button_layout.addWidget(self.export_btn)

        config_layout.addLayout(button_layout, 6, 0, 1, 5)

        config_group.setLayout(config_layout)
        return config_group

    def toggle_date_range(self):
        """Toggle date range editors based on checkbox"""
        use_all = self.use_all_data_cb.isChecked()
        self.start_date_edit.setEnabled(not use_all)
        self.end_date_edit.setEnabled(not use_all)

    def load_different_data(self):
        """Load different dataset for backtesting"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Select Data File",
            "",
            "CSV Files (*.csv);;All Files (*)"
        )

        if filepath:
            try:
                # Load the CSV file
                data = pd.read_csv(filepath)

                # Try to detect and parse date column
                date_columns = ['Date', 'date', 'Time', 'time', 'Datetime', 'datetime']
                date_col = None
                for col in date_columns:
                    if col in data.columns:
                        date_col = col
                        break

                if date_col:
                    data[date_col] = pd.to_datetime(data[date_col])
                    data.set_index(date_col, inplace=True)
                else:
                    # Try to parse the first column as date
                    data.iloc[:, 0] = pd.to_datetime(data.iloc[:, 0])
                    data.set_index(data.columns[0], inplace=True)

                # Rename columns to standard format
                column_mapping = {
                    'open': 'Open', 'high': 'High', 'low': 'Low',
                    'close': 'Close', 'volume': 'Volume'
                }
                data.rename(columns=column_mapping, inplace=True)

                self.data = data

                # Update UI
                data_info = f"{len(self.data)} bars from {self.data.index[0].strftime('%Y-%m-%d')} to {self.data.index[-1].strftime('%Y-%m-%d')}"
                self.data_source_label.setText(data_info)

                # Update date editors
                self.start_date_edit.setDate(QDate(self.data.index[0].year,
                                                   self.data.index[0].month,
                                                   self.data.index[0].day))
                self.end_date_edit.setDate(QDate(self.data.index[-1].year,
                                                 self.data.index[-1].month,
                                                 self.data.index[-1].day))

                QMessageBox.information(self, "Success", f"Loaded {len(self.data)} bars from {filepath}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load data:\n{str(e)}")

    def create_summary_tab(self):
        """Create summary statistics tab"""
        summary_widget = QWidget()
        layout = QVBoxLayout(summary_widget)

        # Summary text area
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.summary_text)

        self.tabs.addTab(summary_widget, "Summary")

    def create_pattern_performance_tab(self):
        """Create pattern performance table tab"""
        perf_widget = QWidget()
        layout = QVBoxLayout(perf_widget)

        # Performance table
        self.perf_table = QTableWidget()
        self.perf_table.setColumnCount(5)
        self.perf_table.setHorizontalHeaderLabels([
            "Pattern Name", "Total Predictions", "Successful",
            "Success Rate (%)", "Mode"
        ])
        self.perf_table.horizontalHeader().setStretchLastSection(True)
        self.perf_table.setSortingEnabled(True)
        layout.addWidget(self.perf_table)

        self.tabs.addTab(perf_widget, "Pattern Performance")

    def create_chart_tab(self):
        """Create success rate chart tab"""
        chart_widget = QWidget()
        layout = QVBoxLayout(chart_widget)

        # Create plot widget
        self.chart = pg.PlotWidget()
        self.chart.setBackground('w')
        self.chart.setLabel('left', 'Success Rate (%)')
        self.chart.setLabel('bottom', 'Pattern')
        self.chart.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self.chart)

        self.tabs.addTab(chart_widget, "Success Rate Chart")

    def create_detailed_results_tab(self):
        """Create detailed results tab"""
        detail_widget = QWidget()
        layout = QVBoxLayout(detail_widget)

        # Create splitter for two tables
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Snapshot results group
        snapshot_group = QGroupBox("Snapshot Mode Results")
        snapshot_layout = QVBoxLayout(snapshot_group)
        self.snapshot_table = QTableWidget()
        self.snapshot_table.setColumnCount(4)
        self.snapshot_table.setHorizontalHeaderLabels([
            "Pattern", "Predictions", "Successful", "Success Rate"
        ])
        snapshot_layout.addWidget(self.snapshot_table)
        splitter.addWidget(snapshot_group)

        # Evolution results group
        evolution_group = QGroupBox("Evolution Mode Results")
        evolution_layout = QVBoxLayout(evolution_group)
        self.evolution_table = QTableWidget()
        self.evolution_table.setColumnCount(4)
        self.evolution_table.setHorizontalHeaderLabels([
            "Pattern", "Predictions", "Successful", "Success Rate"
        ])
        evolution_layout.addWidget(self.evolution_table)
        splitter.addWidget(evolution_group)

        layout.addWidget(splitter)
        self.tabs.addTab(detail_widget, "Detailed Results")

    def create_raw_output_tab(self):
        """Create raw output tab"""
        raw_widget = QWidget()
        layout = QVBoxLayout(raw_widget)

        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.raw_text)

        self.tabs.addTab(raw_widget, "Raw Output")

    def run_backtest(self):
        """Run the backtest with configured parameters"""
        if self.data is None:
            QMessageBox.warning(self, "Warning", "No data loaded for backtesting")
            return

        # Get date range if not using all data
        start_date = None
        end_date = None
        if not self.use_all_data_cb.isChecked():
            start_date = pd.Timestamp(self.start_date_edit.date().toPyDate())
            end_date = pd.Timestamp(self.end_date_edit.date().toPyDate())

            # Validate date range
            if start_date >= end_date:
                QMessageBox.warning(self, "Warning", "Start date must be before end date")
                return

        # Get pattern filters
        pattern_filters = {
            'pattern_types': []
        }

        # Check which pattern types to include
        selected_types = []
        if self.abcd_formed_cb.isChecked():
            selected_types.append('strict_abcd')
        if self.xabcd_formed_cb.isChecked():
            selected_types.append('strict_xabcd')
        if self.abcd_unformed_cb.isChecked():
            selected_types.append('comprehensive_abcd')
        if self.xabcd_unformed_cb.isChecked():
            selected_types.append('comprehensive_xabcd')

        if not selected_types:
            QMessageBox.warning(self, "Warning", "Please select at least one pattern type")
            return

        pattern_filters['pattern_types'] = selected_types

        # Disable controls during backtest
        self.run_btn.setEnabled(False)
        self.mode_combo.setEnabled(False)
        self.load_data_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        # Create and start worker thread with all parameters
        self.worker = BacktestWorker(
            self.data,
            self.mode_combo.currentText(),
            start_date,
            end_date,
            pattern_filters
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.status.connect(self.update_status)
        self.worker.finished.connect(self.display_results)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def update_progress(self, value):
        """Update progress bar"""
        self.progress_bar.setValue(value)

    def update_status(self, message):
        """Update status label"""
        self.status_label.setText(message)

    def handle_error(self, error_msg):
        """Handle backtest error"""
        QMessageBox.critical(self, "Backtest Error", f"Error during backtest:\n{error_msg}")
        self.run_btn.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.load_data_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Error occurred")

    def display_results(self, results):
        """Display backtest results"""
        self.results = results

        # Re-enable controls
        self.run_btn.setEnabled(True)
        self.mode_combo.setEnabled(True)
        self.load_data_btn.setEnabled(True)
        self.export_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("Backtest complete")

        # Update summary
        summary = results.get('summary', 'No summary available')
        self.summary_text.setText(summary)

        # Update performance table
        self.update_performance_table(results.get('statistics', {}))

        # Update chart
        self.update_success_chart(results.get('statistics', {}))

        # Update detailed results
        self.update_detailed_results(results.get('results', []))

        # Update raw output
        self.update_raw_output(results)

    def update_performance_table(self, statistics):
        """Update pattern performance table"""
        self.perf_table.setRowCount(0)

        # Add rows for each pattern
        pattern_stats = statistics.get('by_pattern_name', {})
        for pattern_name, data in pattern_stats.items():
            if data['total'] > 0:
                row_position = self.perf_table.rowCount()
                self.perf_table.insertRow(row_position)

                # Pattern name
                self.perf_table.setItem(row_position, 0,
                                       QTableWidgetItem(pattern_name))

                # Total predictions
                self.perf_table.setItem(row_position, 1,
                                       QTableWidgetItem(str(data['total'])))

                # Successful
                self.perf_table.setItem(row_position, 2,
                                       QTableWidgetItem(str(data['successful'])))

                # Success rate
                success_rate = (data['successful'] / data['total']) * 100
                rate_item = QTableWidgetItem(f"{success_rate:.2f}")
                if success_rate >= 70:
                    rate_item.setForeground(QColor(0, 128, 0))  # Green
                elif success_rate >= 50:
                    rate_item.setForeground(QColor(255, 165, 0))  # Orange
                else:
                    rate_item.setForeground(QColor(255, 0, 0))  # Red
                self.perf_table.setItem(row_position, 3, rate_item)

                # Mode
                self.perf_table.setItem(row_position, 4,
                                       QTableWidgetItem(self.mode_combo.currentText()))

        # Resize columns
        self.perf_table.resizeColumnsToContents()

    def update_success_chart(self, statistics):
        """Update success rate bar chart"""
        self.chart.clear()

        # Get best patterns data
        best_patterns = statistics.get('best_patterns', [])[:10]

        if best_patterns:
            # Prepare data
            pattern_names = [p['name'] for p in best_patterns]
            success_rates = [p['success_rate'] for p in best_patterns]

            # Create bar chart
            x = np.arange(len(pattern_names))
            bars = pg.BarGraphItem(x=x, height=success_rates, width=0.8,
                                  brush=pg.mkBrush(color=(76, 175, 80, 150)))
            self.chart.addItem(bars)

            # Set x-axis labels
            axis = self.chart.getAxis('bottom')
            axis.setTicks([[(i, name[:10]) for i, name in enumerate(pattern_names)]])

            # Set y-axis range
            self.chart.setYRange(0, 100)

            # Add horizontal lines
            for y in [25, 50, 75]:
                line = pg.InfiniteLine(pos=y, angle=0,
                                      pen=pg.mkPen(color=(128, 128, 128, 50), style=Qt.PenStyle.DashLine))
                self.chart.addItem(line)

    def update_detailed_results(self, results):
        """Update detailed results tables"""
        # Clear tables
        self.snapshot_table.setRowCount(0)
        self.evolution_table.setRowCount(0)

        # Separate results by mode
        snapshot_results = [r for r in results if r.mode.value == 'snapshot']
        evolution_results = [r for r in results if r.mode.value == 'evolution']

        # Fill snapshot table
        for result in snapshot_results[:50]:  # Limit to 50 rows
            row = self.snapshot_table.rowCount()
            self.snapshot_table.insertRow(row)

            pattern_name = result.formed_pattern.get('name', 'Unknown')
            predictions = len(result.predictions)
            successful = len(result.successful_predictions)
            success_rate = result.success_rate * 100

            self.snapshot_table.setItem(row, 0, QTableWidgetItem(pattern_name))
            self.snapshot_table.setItem(row, 1, QTableWidgetItem(str(predictions)))
            self.snapshot_table.setItem(row, 2, QTableWidgetItem(str(successful)))
            self.snapshot_table.setItem(row, 3, QTableWidgetItem(f"{success_rate:.1f}%"))

        # Fill evolution table
        for result in evolution_results[:50]:  # Limit to 50 rows
            row = self.evolution_table.rowCount()
            self.evolution_table.insertRow(row)

            pattern_name = result.formed_pattern.get('name', 'Unknown')
            predictions = len(result.predictions)
            successful = len(result.successful_predictions)
            success_rate = result.success_rate * 100

            self.evolution_table.setItem(row, 0, QTableWidgetItem(pattern_name))
            self.evolution_table.setItem(row, 1, QTableWidgetItem(str(predictions)))
            self.evolution_table.setItem(row, 2, QTableWidgetItem(str(successful)))
            self.evolution_table.setItem(row, 3, QTableWidgetItem(f"{success_rate:.1f}%"))

    def update_raw_output(self, results):
        """Update raw output tab"""
        # Convert results to JSON string
        output = json.dumps({
            'statistics': results.get('statistics', {}),
            'summary': results.get('summary', ''),
            'total_results': len(results.get('results', []))
        }, indent=2, default=str)

        self.raw_text.setText(output)

    def export_results(self):
        """Export results to file"""
        if not self.results:
            return

        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Backtest Results",
            f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if filepath:
            try:
                with open(filepath, 'w') as f:
                    json.dump(self.results, f, indent=2, default=str)
                QMessageBox.information(self, "Success", f"Results exported to {filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export results:\n{str(e)}")