"""
Active Signals Window - Display and manage active trading signals

Shows all active pattern signals being monitored by the automated system.
"""

import sys
from datetime import datetime
from typing import Optional, List, Dict
import pandas as pd

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QGroupBox, QComboBox, QHeaderView, QMessageBox,
    QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont

from signal_database import SignalDatabase
from pattern_chart_window import PatternChartWindow


class ActiveSignalsWindow(QMainWindow):
    """Window to display and manage active trading signals"""

    def __init__(self, signal_db: Optional[SignalDatabase] = None, parent=None):
        super().__init__(parent)

        print("ActiveSignalsWindow.__init__ called")

        try:
            self.signal_db = signal_db or SignalDatabase()
            print(f"Signal DB initialized: {self.signal_db}")

            # Auto-refresh timer
            self.auto_refresh_enabled = True
            self.refresh_timer = QTimer(self)
            self.refresh_timer.timeout.connect(self.refreshSignals)
            print("Timer created")

            self.initUI()
            print("UI initialized")

            self.refreshSignals()
            print("Initial refresh done")

            # Start timer after everything is ready
            self.refresh_timer.start(30000)  # Refresh every 30 seconds (reduced from 10s to improve performance)
            print("Timer started")

        except Exception as e:
            print(f"Error in ActiveSignalsWindow.__init__: {e}")
            import traceback
            traceback.print_exc()
            raise

    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle("Active Trading Signals")
        self.setGeometry(100, 100, 1400, 900)  # Increased window size for better visibility

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel("🔔 Active Trading Signals")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Auto-refresh toggle
        self.auto_refresh_btn = QPushButton("⏸ Pause Auto-Refresh")
        self.auto_refresh_btn.clicked.connect(self.toggleAutoRefresh)
        header_layout.addWidget(self.auto_refresh_btn)

        # Manual refresh button
        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.clicked.connect(self.refreshSignals)
        header_layout.addWidget(refresh_btn)

        main_layout.addLayout(header_layout)

        # Filters
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout()

        # Symbol filter
        filter_layout.addWidget(QLabel("Symbol:"))
        self.symbol_filter = QComboBox()
        self.symbol_filter.addItem('All')
        self.symbol_filter.currentTextChanged.connect(self.refreshSignals)
        filter_layout.addWidget(self.symbol_filter)

        # Timeframe filter
        filter_layout.addWidget(QLabel("TF:"))
        self.tf_filter = QComboBox()
        self.tf_filter.addItem('All')
        self.tf_filter.currentTextChanged.connect(self.refreshSignals)
        filter_layout.addWidget(self.tf_filter)

        # Pattern filter
        filter_layout.addWidget(QLabel("Pattern:"))
        self.pattern_filter = QComboBox()
        self.pattern_filter.addItem('All')
        self.pattern_filter.currentTextChanged.connect(self.refreshSignals)
        filter_layout.addWidget(self.pattern_filter)

        # Direction filter
        filter_layout.addWidget(QLabel("Direction:"))
        self.direction_filter = QComboBox()
        self.direction_filter.addItems(['All', 'Bullish', 'Bearish'])
        self.direction_filter.currentTextChanged.connect(self.refreshSignals)
        filter_layout.addWidget(self.direction_filter)

        # Status filter
        filter_layout.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(['All', 'Detected', 'Approaching', 'Entered', 'Completed', 'Invalidated'])
        self.status_filter.currentTextChanged.connect(self.refreshSignals)
        filter_layout.addWidget(self.status_filter)

        filter_layout.addStretch()

        # Stats
        self.stats_label = QLabel()
        filter_layout.addWidget(self.stats_label)

        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)

        # Remove from Monitoring button (below filters)
        remove_btn_layout = QHBoxLayout()
        self.delete_btn = QPushButton("🗑️ Remove from Monitoring")
        self.delete_btn.clicked.connect(self.deleteSignal)
        self.delete_btn.setEnabled(False)
        self.delete_btn.setStyleSheet("QPushButton { background-color: #FFCDD2; color: #C62828; font-weight: bold; padding: 8px; }")
        remove_btn_layout.addWidget(self.delete_btn)
        remove_btn_layout.addStretch()
        main_layout.addLayout(remove_btn_layout)

        # Splitter for table and details
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Signals table
        self.signals_table = QTableWidget()
        self.signals_table.setColumnCount(13)
        self.signals_table.setHorizontalHeaderLabels([
            'Symbol', 'TF', 'Pattern', 'Direction', 'Status',
            'Current Price', 'PRZ Min', 'PRZ Max', 'Distance %',
            'Age', 'Detected', 'Alerts', 'Chart'
        ])

        # Set column widths
        header = self.signals_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # Symbol
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # TF
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # Pattern
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Direction
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # Status
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)  # Current Price
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # PRZ Min
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # PRZ Max
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)  # Distance %
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)  # Age
        header.setSectionResizeMode(10, QHeaderView.ResizeMode.Fixed)  # Detected
        header.setSectionResizeMode(11, QHeaderView.ResizeMode.Fixed)  # Alerts
        header.setSectionResizeMode(12, QHeaderView.ResizeMode.Fixed)  # Chart

        self.signals_table.setColumnWidth(0, 100)  # Symbol
        self.signals_table.setColumnWidth(1, 50)   # TF
        self.signals_table.setColumnWidth(3, 80)   # Direction
        self.signals_table.setColumnWidth(4, 120)  # Status (wider for NEW badge)
        self.signals_table.setColumnWidth(5, 100)  # Current Price
        self.signals_table.setColumnWidth(6, 100)  # PRZ Min
        self.signals_table.setColumnWidth(7, 100)  # PRZ Max
        self.signals_table.setColumnWidth(8, 80)   # Distance %
        self.signals_table.setColumnWidth(9, 80)   # Age
        self.signals_table.setColumnWidth(10, 120)  # Detected
        self.signals_table.setColumnWidth(11, 150)  # Alerts (wider to show full text)
        self.signals_table.setColumnWidth(12, 80)   # Chart button

        self.signals_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.signals_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.signals_table.setAlternatingRowColors(True)
        self.signals_table.setSortingEnabled(True)  # Enable column sorting
        self.signals_table.setWordWrap(True)  # Enable text wrapping for long content
        self.signals_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)  # Auto-adjust row heights
        self.signals_table.itemSelectionChanged.connect(self.onSignalSelected)

        splitter.addWidget(self.signals_table)

        # Signal details - Use horizontal split for better space usage
        details_group = QGroupBox("Signal Details & Price Alerts")
        details_layout = QHBoxLayout()

        # Left side: Signal details (more compact)
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("<b>Pattern Information:</b>"))

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumWidth(400)
        left_layout.addWidget(self.details_text)

        details_layout.addLayout(left_layout, 1)

        # Right side: Price Alerts Table
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("<b>Price Alerts Control:</b>"))

        self.price_alerts_table = QTableWidget()
        self.price_alerts_table.setColumnCount(4)
        self.price_alerts_table.setHorizontalHeaderLabels(["Enable", "Type", "Level", "Price"])
        self.price_alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.price_alerts_table.setMinimumWidth(400)
        self.price_alerts_table.itemChanged.connect(self.onAlertCheckboxChanged)
        right_layout.addWidget(self.price_alerts_table)

        details_layout.addLayout(right_layout, 1)

        details_group.setLayout(details_layout)

        splitter.addWidget(details_group)
        splitter.setStretchFactor(0, 2)  # Table gets less space
        splitter.setStretchFactor(1, 2)  # Details gets equal space - no more scrolling!

        main_layout.addWidget(splitter)

        # Status bar message
        self.last_refresh_label = QLabel()
        main_layout.addWidget(self.last_refresh_label)

    def refreshSignals(self):
        """Refresh signals from database"""
        try:
            print("refreshSignals() called")

            # Get all signals (including completed/invalidated)
            print("Getting all signals from database...")
            all_signals = self.signal_db.get_all_signals_with_outcomes()
            print(f"Found {len(all_signals)} total signals")

            # Get current filter values
            status_filter = self.status_filter.currentText().lower()
            symbol_filter = self.symbol_filter.currentText()
            tf_filter = self.tf_filter.currentText()
            pattern_filter = self.pattern_filter.currentText()
            direction_filter = self.direction_filter.currentText().lower()

            print(f"Filters - Symbol: {symbol_filter}, TF: {tf_filter}, Pattern: {pattern_filter}, Direction: {direction_filter}, Status: {status_filter}")

            # Update filter dropdown options (block signals to avoid recursive refresh)
            symbols = sorted(set(s['symbol'] for s in all_signals))
            timeframes = sorted(set(s['timeframe'] for s in all_signals))
            patterns = sorted(set(s['pattern_name'] for s in all_signals))

            current_symbol = self.symbol_filter.currentText()
            current_tf = self.tf_filter.currentText()
            current_pattern = self.pattern_filter.currentText()

            # Update Symbol filter
            self.symbol_filter.blockSignals(True)
            self.symbol_filter.clear()
            self.symbol_filter.addItem('All')
            self.symbol_filter.addItems(symbols)
            if current_symbol in ['All'] + symbols:
                self.symbol_filter.setCurrentText(current_symbol)
            self.symbol_filter.blockSignals(False)

            # Update TF filter
            self.tf_filter.blockSignals(True)
            self.tf_filter.clear()
            self.tf_filter.addItem('All')
            self.tf_filter.addItems(timeframes)
            if current_tf in ['All'] + timeframes:
                self.tf_filter.setCurrentText(current_tf)
            self.tf_filter.blockSignals(False)

            # Update Pattern filter
            self.pattern_filter.blockSignals(True)
            self.pattern_filter.clear()
            self.pattern_filter.addItem('All')
            self.pattern_filter.addItems(patterns)
            if current_pattern in ['All'] + patterns:
                self.pattern_filter.setCurrentText(current_pattern)
            self.pattern_filter.blockSignals(False)

            # Apply filters
            filtered_signals = all_signals

            if symbol_filter != 'All':
                filtered_signals = [s for s in filtered_signals if s['symbol'] == symbol_filter]

            if tf_filter != 'All':
                filtered_signals = [s for s in filtered_signals if s['timeframe'] == tf_filter]

            if pattern_filter != 'All':
                filtered_signals = [s for s in filtered_signals if s['pattern_name'] == pattern_filter]

            if direction_filter != 'all':
                filtered_signals = [s for s in filtered_signals if s['direction'] == direction_filter]

            if status_filter != 'all':
                filtered_signals = [s for s in filtered_signals if s['status'] == status_filter]

            print(f"Filtered to {len(filtered_signals)} signals")

            # Update stats
            stats_by_status = {}
            for signal in all_signals:
                status = signal['status']
                stats_by_status[status] = stats_by_status.get(status, 0) + 1

            stats_text = f"Total: {len(all_signals)} | "
            stats_text += " | ".join([f"{k}: {v}" for k, v in stats_by_status.items()])
            self.stats_label.setText(stats_text)

            print("Updating table...")
            # Update table
            self.updateTable(filtered_signals)
            print("Table updated")

            # Update last refresh time
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.last_refresh_label.setText(f"Last refreshed: {now}")

            print("refreshSignals() completed successfully")

        except Exception as e:
            error_msg = f"Failed to refresh signals: {e}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", error_msg)

    def updateTable(self, signals: List[Dict]):
        """Update table with signals"""
        # Disable sorting while updating for better performance
        self.signals_table.setSortingEnabled(False)
        self.signals_table.setRowCount(len(signals))

        for row, signal in enumerate(signals):
            # Symbol
            self.signals_table.setItem(row, 0, QTableWidgetItem(signal['symbol']))

            # Timeframe
            self.signals_table.setItem(row, 1, QTableWidgetItem(signal['timeframe']))

            # Pattern name
            pattern_name = signal['pattern_name'].replace('_', ' ').title()
            self.signals_table.setItem(row, 2, QTableWidgetItem(pattern_name))

            # Direction
            direction_item = QTableWidgetItem(signal['direction'].title())
            if signal['direction'] == 'bullish':
                direction_item.setForeground(QColor('green'))
            else:
                direction_item.setForeground(QColor('red'))
            self.signals_table.setItem(row, 3, direction_item)

            # Status (with NEW indicator for recent patterns)
            status_text = signal['status'].title()

            # Mark patterns detected within last 5 minutes as NEW
            detected_time = datetime.fromisoformat(signal['detected_at'])
            time_since_detection = (datetime.now() - detected_time).total_seconds() / 60  # minutes

            if time_since_detection < 5:
                status_text = f"🆕 {status_text}"

            status_item = QTableWidgetItem(status_text)
            status_color = {
                'detected': QColor(100, 100, 100),
                'approaching': QColor(255, 140, 0),
                'entered': QColor(0, 150, 0),
                'completed': QColor(0, 100, 255),  # Blue for completed
                'invalidated': QColor(255, 0, 0)    # Red for invalidated
            }.get(signal['status'], QColor('black'))
            status_item.setForeground(status_color)

            # Highlight new patterns with yellow background
            if time_since_detection < 5:
                status_item.setBackground(QColor(255, 255, 200))

            self.signals_table.setItem(row, 4, status_item)

            # Current price
            self.signals_table.setItem(row, 5, QTableWidgetItem(f"${signal['current_price']:.2f}"))

            # PRZ Min
            self.signals_table.setItem(row, 6, QTableWidgetItem(f"${signal['prz_min']:.2f}"))

            # PRZ Max
            self.signals_table.setItem(row, 7, QTableWidgetItem(f"${signal['prz_max']:.2f}"))

            # Distance %
            distance_item = QTableWidgetItem(f"{signal['distance_to_prz_pct']:.1f}%")
            if signal['distance_to_prz_pct'] == 0:
                distance_item.setBackground(QColor(200, 255, 200))
            self.signals_table.setItem(row, 8, distance_item)

            # Age (how long ago pattern was detected)
            age_minutes = time_since_detection
            if age_minutes < 60:
                age_text = f"{int(age_minutes)}m"
            elif age_minutes < 1440:  # Less than 24 hours
                age_text = f"{int(age_minutes / 60)}h"
            else:
                age_text = f"{int(age_minutes / 1440)}d"

            age_item = QTableWidgetItem(age_text)
            # Color code by age: green = new, yellow = medium, gray = old
            if age_minutes < 5:
                age_item.setForeground(QColor(0, 150, 0))  # Green
            elif age_minutes < 60:
                age_item.setForeground(QColor(255, 140, 0))  # Orange
            else:
                age_item.setForeground(QColor(100, 100, 100))  # Gray
            self.signals_table.setItem(row, 9, age_item)

            # Detected time
            self.signals_table.setItem(row, 10, QTableWidgetItem(detected_time.strftime('%Y-%m-%d %H:%M')))

            # Alerts sent
            import json
            alerts = json.loads(signal['alerts_sent_json'])
            alerts_text = ', '.join(alerts) if alerts else 'None'
            self.signals_table.setItem(row, 11, QTableWidgetItem(alerts_text))

            # Chart button
            chart_btn = QPushButton("📊 View")
            chart_btn.setStyleSheet("QPushButton { background-color: #E3F2FD; color: #1976D2; font-weight: bold; padding: 4px; }")
            chart_btn.clicked.connect(lambda checked, sig=signal: self.openPatternChart(sig))
            self.signals_table.setCellWidget(row, 12, chart_btn)

            # Store signal_id as row data
            self.signals_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, signal['signal_id'])

        # Re-enable sorting after populating table
        self.signals_table.setSortingEnabled(True)

    def onSignalSelected(self):
        """Handle signal selection"""
        selected_rows = self.signals_table.selectedItems()

        if not selected_rows:
            self.details_text.clear()
            self.delete_btn.setEnabled(False)
            return

        # Get signal_id from first column
        row = self.signals_table.currentRow()
        signal_id = self.signals_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        # Load full signal details
        signal = self.signal_db.get_signal(signal_id)

        if signal:
            self.showSignalDetails(signal)
            self.delete_btn.setEnabled(True)
        else:
            self.details_text.setText("Signal not found")
            self.delete_btn.setEnabled(False)

    def showSignalDetails(self, signal: Dict):
        """Display historical statistics only - other details shown in chart"""
        import json

        # Simple header
        details = f"""
<div style="background-color: #E3F2FD; padding: 10px; margin-bottom: 10px; border-radius: 5px;">
<h3 style="margin: 0; color: #1976D2;">{signal['symbol']} {signal['timeframe']} - {signal['pattern_name'].replace('_', ' ').title()}</h3>
<p style="margin: 5px 0 0 0; color: #666;"><b>Pattern Type:</b> {signal['pattern_type']} | <b>Direction:</b> {signal['direction'].title()} | <b>Status:</b> {signal['status'].title()}</p>
<p style="margin: 5px 0 0 0; color: #1976D2; font-size: 11px;">💡 Click the <b>"📊 View Chart"</b> button in the table to see price levels, targets, and pattern visualization.</p>
</div>
"""

        # Add historical statistics section (THE MOST IMPORTANT PART)
        details += self.getHistoricalStatisticsHTML(signal)

        details += "</html>"

        self.details_text.setHtml(details)

        # Load price alerts table
        self.loadPriceAlerts(signal['signal_id'])

    def getHistoricalStatisticsHTML(self, signal: Dict) -> str:
        """Generate HTML for historical statistics from backtesting"""
        html = ""

        try:
            # Get pattern info
            symbol = signal['symbol']
            timeframe = signal['timeframe']
            pattern_type = signal['pattern_type']
            pattern_name = signal['pattern_name']
            direction = signal['direction']

            # Query statistics
            stats = self.signal_db.get_pattern_statistics(
                symbol=symbol,
                timeframe=timeframe,
                pattern_type=pattern_type,
                pattern_name=pattern_name,
                direction=direction
            )

            if not stats:
                html += """
                <hr>
                <h4>📊 Historical Statistics (From Backtesting):</h4>
                <p style='color: gray;'>No historical data available yet. Run Fibonacci and Harmonic Points analysis in backtesting to generate statistics.</p>
                """
                return html

            # Separate by type
            fib_stats = [s for s in stats if s['stat_type'] == 'fibonacci']
            harmonic_stats = [s for s in stats if s['stat_type'] == 'harmonic_point']

            html += """
            <hr>
            <h4>📊 Historical Statistics (From Backtesting):</h4>
            <p style='font-size: 10px; color: #666;'>Based on {sample_count} historical {pattern_type} {pattern_name} {direction} patterns for {symbol} {timeframe}</p>
            """.format(
                sample_count=stats[0]['sample_count'] if stats else 0,
                pattern_type=pattern_type,
                pattern_name=pattern_name,
                direction=direction,
                symbol=symbol,
                timeframe=timeframe
            )

            if fib_stats:
                html += "<p><b>Fibonacci Levels (Most Hit):</b></p><ul>"
                # Sort by hit percentage, show top 5
                fib_stats_sorted = sorted(fib_stats, key=lambda x: x['hit_percentage'], reverse=True)[:5]
                for stat in fib_stats_sorted:
                    color = "green" if stat['hit_percentage'] >= 70 else ("orange" if stat['hit_percentage'] >= 50 else "gray")
                    html += f"<li style='color: {color};'><b>{stat['level_name']}</b>: {stat['hit_percentage']:.1f}% hit rate, {stat['avg_touches']:.1f} avg touches</li>"
                html += "</ul>"

            if harmonic_stats:
                html += "<p><b>Harmonic Points:</b></p><ul>"
                for stat in harmonic_stats:
                    color = "green" if stat['hit_percentage'] >= 70 else ("orange" if stat['hit_percentage'] >= 50 else "gray")
                    html += f"<li style='color: {color};'><b>{stat['level_name']}</b>: {stat['hit_percentage']:.1f}% hit rate, {stat['avg_touches']:.1f} avg touches</li>"
                html += "</ul>"

            html += "<p style='color: blue; font-size: 10px;'>💡 <b>Trading Tip:</b> High hit rates (70%+) suggest reliable levels for take-profit targets. High touch counts indicate oscillation zones.</p>"

        except Exception as e:
            print(f"Error generating historical statistics: {e}")
            import traceback
            traceback.print_exc()

        return html

    def loadPriceAlerts(self, signal_id: str):
        """Load price alerts for the selected signal into the table"""
        # Disconnect signal to prevent triggering during load
        self.price_alerts_table.itemChanged.disconnect(self.onAlertCheckboxChanged)

        try:
            price_alerts = self.signal_db.get_price_alerts(signal_id)

            self.price_alerts_table.setRowCount(len(price_alerts))

            for row, alert in enumerate(price_alerts):
                # Checkbox for enable/disable
                checkbox_item = QTableWidgetItem()
                checkbox_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                checkbox_item.setCheckState(Qt.CheckState.Checked if alert['is_enabled'] else Qt.CheckState.Unchecked)
                # Store alert_id in checkbox item
                checkbox_item.setData(Qt.ItemDataRole.UserRole, alert['alert_id'])
                self.price_alerts_table.setItem(row, 0, checkbox_item)

                # Type
                type_text = "Fibonacci" if alert['alert_type'] == 'fibonacci' else "Harmonic Point"
                type_item = QTableWidgetItem(type_text)
                type_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.price_alerts_table.setItem(row, 1, type_item)

                # Level name
                level_item = QTableWidgetItem(alert['level_name'])
                level_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.price_alerts_table.setItem(row, 2, level_item)

                # Price
                price_item = QTableWidgetItem(f"${alert['price_level']:.2f}")
                price_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.price_alerts_table.setItem(row, 3, price_item)

                # Color code triggered alerts
                if alert['was_triggered']:
                    for col in range(4):
                        self.price_alerts_table.item(row, col).setBackground(QColor(200, 255, 200))  # Light green

        finally:
            # Reconnect signal
            self.price_alerts_table.itemChanged.connect(self.onAlertCheckboxChanged)

    def onAlertCheckboxChanged(self, item: QTableWidgetItem):
        """Handle checkbox state change for price alerts"""
        if item.column() != 0:  # Only handle checkbox column
            return

        alert_id = item.data(Qt.ItemDataRole.UserRole)
        is_enabled = item.checkState() == Qt.CheckState.Checked

        # Update database
        if self.signal_db.toggle_price_alert(alert_id, is_enabled):
            print(f"Price alert {alert_id} {'enabled' if is_enabled else 'disabled'}")
        else:
            print(f"Failed to toggle price alert {alert_id}")

    def deleteSignal(self):
        """Remove signal from monitoring (user choice, not pattern validation)"""
        row = self.signals_table.currentRow()
        if row < 0:
            return

        signal_id = self.signals_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        signal = self.signal_db.get_signal(signal_id)

        if not signal:
            return

        reply = QMessageBox.question(
            self,
            'Remove from Monitoring',
            f'Remove this signal from your monitoring list?\n\n'
            f'Pattern: {signal["pattern_name"]} ({signal["direction"]})\n'
            f'Symbol: {signal["symbol"]} {signal["timeframe"]}\n\n'
            f'Note: This removes the signal from YOUR view only.\n'
            f'The system will continue automatic tracking for statistics.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete from database
            try:
                conn = self.signal_db._get_connection()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM signals WHERE signal_id = ?', (signal_id,))
                conn.commit()
                conn.close()

                QMessageBox.information(self, "Removed", "Signal removed from your monitoring list")
                self.refreshSignals()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to remove signal: {e}")

    def toggleAutoRefresh(self):
        """Toggle auto-refresh on/off"""
        self.auto_refresh_enabled = not self.auto_refresh_enabled

        if self.auto_refresh_enabled:
            self.refresh_timer.start()
            self.auto_refresh_btn.setText("⏸ Pause Auto-Refresh")
        else:
            self.refresh_timer.stop()
            self.auto_refresh_btn.setText("▶ Resume Auto-Refresh")

    def closeEvent(self, event):
        """Handle window close"""
        self.refresh_timer.stop()
        event.accept()

    def openPatternChart(self, signal: Dict):
        """Open pattern chart window to visualize the pattern"""
        try:
            print(f"Opening pattern chart for {signal['symbol']} {signal['timeframe']} - {signal['pattern_name']}")
            chart_window = PatternChartWindow(signal, parent=self)
            chart_window.show()
        except Exception as e:
            print(f"Error opening pattern chart: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to open pattern chart: {e}")


# Standalone test
if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = ActiveSignalsWindow()
    window.show()
    sys.exit(app.exec())
