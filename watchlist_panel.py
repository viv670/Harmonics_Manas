"""
Watchlist Management Panel
===========================
PyQt6 GUI panel for viewing and managing the watchlist and update history.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QSpinBox,
                             QGroupBox, QTabWidget, QHeaderView, QMessageBox,
                             QCheckBox, QDialog, QDialogButtonBox, QFormLayout)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from datetime import datetime
from typing import Optional
from watchlist_manager import WatchlistManager
from auto_update_scheduler import AutoUpdateScheduler


class SettingsDialog(QDialog):
    """Dialog for configuring scheduler settings"""

    def __init__(self, current_interval: int, max_retries: int, retry_delay: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scheduler Settings")
        self.setModal(True)
        self.resize(400, 200)

        layout = QFormLayout()

        # Check interval
        self.interval_spin = QSpinBox()
        self.interval_spin.setMinimum(1)
        self.interval_spin.setMaximum(120)
        self.interval_spin.setSuffix(" minutes")
        self.interval_spin.setValue(current_interval // 60)
        layout.addRow("Check Interval:", self.interval_spin)

        # Max retries
        self.retries_spin = QSpinBox()
        self.retries_spin.setMinimum(0)
        self.retries_spin.setMaximum(10)
        self.retries_spin.setValue(max_retries)
        layout.addRow("Max Retries:", self.retries_spin)

        # Retry delay
        self.delay_spin = QSpinBox()
        self.delay_spin.setMinimum(10)
        self.delay_spin.setMaximum(600)
        self.delay_spin.setSuffix(" seconds")
        self.delay_spin.setValue(retry_delay)
        layout.addRow("Retry Delay:", self.delay_spin)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

    def get_values(self):
        """Get the configured values"""
        return {
            'interval': self.interval_spin.value() * 60,  # Convert to seconds
            'max_retries': self.retries_spin.value(),
            'retry_delay': self.delay_spin.value()
        }


class WatchlistPanel(QWidget):
    """GUI panel for watchlist and update history management"""

    # Signals
    update_requested = pyqtSignal(str, str)  # symbol, timeframe

    def __init__(self, watchlist_manager: WatchlistManager,
                 auto_updater: Optional[AutoUpdateScheduler] = None,
                 parent=None):
        super().__init__(parent)
        self.watchlist = watchlist_manager
        self.auto_updater = auto_updater

        self.initUI()

        # Auto-refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

    def initUI(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()

        # Title
        title = QLabel("Watchlist & Update Manager")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Tab widget
        tabs = QTabWidget()

        # Tab 1: Watchlist
        watchlist_tab = self.create_watchlist_tab()
        tabs.addTab(watchlist_tab, "Watchlist")

        # Tab 2: Update History
        history_tab = self.create_history_tab()
        tabs.addTab(history_tab, "Update History")

        # Tab 3: Failed Updates
        failed_tab = self.create_failed_tab()
        tabs.addTab(failed_tab, "Failed Updates")

        # Tab 4: Statistics
        stats_tab = self.create_stats_tab()
        tabs.addTab(stats_tab, "Statistics")

        # Tab 5: Notification History
        notification_tab = self.create_notification_history_tab()
        tabs.addTab(notification_tab, "Notifications")

        layout.addWidget(tabs)

        # Control buttons at bottom
        controls = self.create_controls()
        layout.addWidget(controls)

        self.setLayout(layout)

    def create_watchlist_tab(self):
        """Create the watchlist tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Table
        self.watchlist_table = QTableWidget()
        self.watchlist_table.setColumnCount(7)
        self.watchlist_table.setHorizontalHeaderLabels([
            "Symbol", "Timeframe", "Enabled", "Last Update", "Next Update",
            "Status", "Actions"
        ])
        self.watchlist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.watchlist_table.setAlternatingRowColors(True)
        layout.addWidget(self.watchlist_table)

        widget.setLayout(layout)
        return widget

    def create_history_tab(self):
        """Create the update history tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels([
            "Timestamp", "Symbol", "Timeframe", "Status", "Candles", "Error"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)

        widget.setLayout(layout)
        return widget

    def create_failed_tab(self):
        """Create the failed updates tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Table
        self.failed_table = QTableWidget()
        self.failed_table.setColumnCount(5)
        self.failed_table.setHorizontalHeaderLabels([
            "Timestamp", "Symbol", "Timeframe", "Retries", "Error Message"
        ])
        self.failed_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.failed_table.setAlternatingRowColors(True)
        layout.addWidget(self.failed_table)

        widget.setLayout(layout)
        return widget

    def create_stats_tab(self):
        """Create the statistics tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Overall statistics group
        overall_group = QGroupBox("Overall Statistics")
        overall_layout = QVBoxLayout()

        self.total_updates_label = QLabel("Total Updates: 0")
        self.successful_label = QLabel("Successful: 0")
        self.failed_label = QLabel("Failed: 0")
        self.success_rate_label = QLabel("Success Rate: 0%")
        self.total_candles_label = QLabel("Total Candles Updated: 0")

        overall_layout.addWidget(self.total_updates_label)
        overall_layout.addWidget(self.successful_label)
        overall_layout.addWidget(self.failed_label)
        overall_layout.addWidget(self.success_rate_label)
        overall_layout.addWidget(self.total_candles_label)

        overall_group.setLayout(overall_layout)
        layout.addWidget(overall_group)

        # Scheduler status group
        scheduler_group = QGroupBox("Scheduler Status")
        scheduler_layout = QVBoxLayout()

        self.scheduler_status_label = QLabel("Status: Unknown")
        self.last_check_label = QLabel("Last Check: Never")
        self.check_interval_label = QLabel("Check Interval: 0 minutes")
        self.retry_settings_label = QLabel("Retry Settings: 0 retries, 0s delay")

        scheduler_layout.addWidget(self.scheduler_status_label)
        scheduler_layout.addWidget(self.last_check_label)
        scheduler_layout.addWidget(self.check_interval_label)
        scheduler_layout.addWidget(self.retry_settings_label)

        scheduler_group.setLayout(scheduler_layout)
        layout.addWidget(scheduler_group)

        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def create_notification_history_tab(self):
        """Create the notification history tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Info label
        info_label = QLabel("History of all toast notifications shown")
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)

        # Table
        self.notification_table = QTableWidget()
        self.notification_table.setColumnCount(4)
        self.notification_table.setHorizontalHeaderLabels([
            "Timestamp", "Type", "Title", "Message"
        ])
        self.notification_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.notification_table.setAlternatingRowColors(True)
        layout.addWidget(self.notification_table)

        # Clear history button
        clear_btn = QPushButton("Clear History")
        clear_btn.clicked.connect(self.clear_notification_history)
        layout.addWidget(clear_btn)

        widget.setLayout(layout)
        return widget

    def create_controls(self):
        """Create control buttons"""
        group = QGroupBox("Controls")
        layout = QHBoxLayout()

        # Scheduler controls
        self.pause_btn = QPushButton("Pause Auto-Updates")
        self.pause_btn.clicked.connect(self.toggle_pause)
        layout.addWidget(self.pause_btn)

        self.update_all_btn = QPushButton("Update All Now")
        self.update_all_btn.clicked.connect(self.update_all_charts)
        layout.addWidget(self.update_all_btn)

        # Settings button
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self.show_settings)
        layout.addWidget(self.settings_btn)

        # Refresh button
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_data)
        layout.addWidget(refresh_btn)

        layout.addStretch()

        group.setLayout(layout)
        return group

    def refresh_data(self):
        """Refresh all data from watchlist and history"""
        self.refresh_watchlist_table()
        self.refresh_history_table()
        self.refresh_failed_table()
        self.refresh_statistics()
        self.refresh_notification_history()

    def refresh_watchlist_table(self):
        """Refresh the watchlist table"""
        charts = self.watchlist.get_all_charts()
        self.watchlist_table.setRowCount(len(charts))

        for row, chart in enumerate(charts):
            # Symbol
            self.watchlist_table.setItem(row, 0, QTableWidgetItem(chart.symbol))

            # Timeframe
            self.watchlist_table.setItem(row, 1, QTableWidgetItem(chart.timeframe))

            # Enabled checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(chart.enabled)
            checkbox.stateChanged.connect(
                lambda state, s=chart.symbol, t=chart.timeframe: self.toggle_chart(s, t, state == Qt.CheckState.Checked.value)
            )
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.watchlist_table.setCellWidget(row, 2, checkbox_widget)

            # Last update
            last_update = chart.last_update.strftime("%Y-%m-%d %H:%M")
            self.watchlist_table.setItem(row, 3, QTableWidgetItem(last_update))

            # Next update
            next_update = chart.next_update.strftime("%Y-%m-%d %H:%M")
            self.watchlist_table.setItem(row, 4, QTableWidgetItem(next_update))

            # Status
            needs_update = chart.needs_update()
            status_item = QTableWidgetItem("Needs Update" if needs_update else "Up to date")
            if needs_update:
                status_item.setForeground(QColor(255, 165, 0))  # Orange
            else:
                status_item.setForeground(QColor(0, 200, 0))  # Green
            self.watchlist_table.setItem(row, 5, status_item)

            # Actions button
            update_btn = QPushButton("Update Now")
            update_btn.clicked.connect(lambda checked, s=chart.symbol, t=chart.timeframe: self.update_chart(s, t))
            self.watchlist_table.setCellWidget(row, 6, update_btn)

    def refresh_history_table(self):
        """Refresh the update history table"""
        if not self.auto_updater:
            return

        history = self.auto_updater.get_update_history(50)
        self.history_table.setRowCount(len(history))

        for row, record in enumerate(reversed(history)):  # Most recent first
            # Timestamp
            timestamp = datetime.fromisoformat(record.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            self.history_table.setItem(row, 0, QTableWidgetItem(timestamp))

            # Symbol
            self.history_table.setItem(row, 1, QTableWidgetItem(record.symbol))

            # Timeframe
            self.history_table.setItem(row, 2, QTableWidgetItem(record.timeframe))

            # Status
            status_item = QTableWidgetItem(record.status.upper())
            if record.status == 'success':
                status_item.setForeground(QColor(0, 200, 0))  # Green
            elif record.status == 'failed':
                status_item.setForeground(QColor(255, 0, 0))  # Red
            else:  # retrying
                status_item.setForeground(QColor(255, 165, 0))  # Orange
            self.history_table.setItem(row, 3, status_item)

            # Candles
            self.history_table.setItem(row, 4, QTableWidgetItem(str(record.candles_updated)))

            # Error
            error = record.error_message or ""
            self.history_table.setItem(row, 5, QTableWidgetItem(error))

    def refresh_failed_table(self):
        """Refresh the failed updates table"""
        if not self.auto_updater:
            return

        failed = self.auto_updater.get_failed_updates(50)
        self.failed_table.setRowCount(len(failed))

        for row, record in enumerate(reversed(failed)):  # Most recent first
            # Timestamp
            timestamp = datetime.fromisoformat(record.timestamp).strftime("%Y-%m-%d %H:%M:%S")
            self.failed_table.setItem(row, 0, QTableWidgetItem(timestamp))

            # Symbol
            self.failed_table.setItem(row, 1, QTableWidgetItem(record.symbol))

            # Timeframe
            self.failed_table.setItem(row, 2, QTableWidgetItem(record.timeframe))

            # Retries
            self.failed_table.setItem(row, 3, QTableWidgetItem(str(record.retry_attempt)))

            # Error message
            self.failed_table.setItem(row, 4, QTableWidgetItem(record.error_message or ""))

    def refresh_statistics(self):
        """Refresh statistics"""
        if not self.auto_updater:
            return

        stats = self.auto_updater.get_stats()
        history_stats = stats.get('history_stats', {})

        # Overall statistics
        self.total_updates_label.setText(f"Total Updates: {history_stats.get('total_updates', 0)}")
        self.successful_label.setText(f"Successful: {history_stats.get('successful', 0)}")
        self.failed_label.setText(f"Failed: {history_stats.get('failed', 0)}")
        self.success_rate_label.setText(f"Success Rate: {history_stats.get('success_rate', 0):.1f}%")
        self.total_candles_label.setText(f"Total Candles Updated: {history_stats.get('total_candles_updated', 0)}")

        # Scheduler status
        if stats['running']:
            status = "Paused" if stats['paused'] else "Running"
            color = "orange" if stats['paused'] else "green"
            self.scheduler_status_label.setText(f"<font color='{color}'>Status: {status}</font>")
        else:
            self.scheduler_status_label.setText("<font color='red'>Status: Stopped</font>")

        last_check = stats.get('last_check')
        if last_check:
            last_check_dt = datetime.fromisoformat(last_check)
            self.last_check_label.setText(f"Last Check: {last_check_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            self.last_check_label.setText("Last Check: Never")

        interval_min = stats.get('check_interval', 0) // 60
        self.check_interval_label.setText(f"Check Interval: {interval_min} minutes")

        max_retries = stats.get('max_retries', 0)
        retry_delay = stats.get('retry_delay', 0)
        self.retry_settings_label.setText(f"Retry Settings: {max_retries} retries, {retry_delay}s delay")

    def refresh_notification_history(self):
        """Refresh notification history table"""
        # Get history from toast manager (if available in parent)
        parent = self.parent()
        if not parent or not hasattr(parent, 'toast_manager'):
            return

        history = parent.toast_manager.get_history(100)
        self.notification_table.setRowCount(len(history))

        for row, record in enumerate(history):
            # Timestamp
            timestamp = datetime.fromisoformat(record['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            self.notification_table.setItem(row, 0, QTableWidgetItem(timestamp))

            # Type
            type_item = QTableWidgetItem(record['type'].upper())
            if record['type'] == 'success':
                type_item.setForeground(QColor(0, 200, 0))  # Green
            elif record['type'] == 'error':
                type_item.setForeground(QColor(255, 0, 0))  # Red
            elif record['type'] == 'warning':
                type_item.setForeground(QColor(255, 165, 0))  # Orange
            else:  # info
                type_item.setForeground(QColor(0, 100, 200))  # Blue
            self.notification_table.setItem(row, 1, type_item)

            # Title
            self.notification_table.setItem(row, 2, QTableWidgetItem(record['title']))

            # Message
            self.notification_table.setItem(row, 3, QTableWidgetItem(record['message']))

    def clear_notification_history(self):
        """Clear notification history"""
        parent = self.parent()
        if parent and hasattr(parent, 'toast_manager'):
            parent.toast_manager.history.clear()
            self.refresh_notification_history()
            QMessageBox.information(self, "History Cleared", "Notification history has been cleared.")

    def toggle_chart(self, symbol: str, timeframe: str, enabled: bool):
        """Toggle chart enabled/disabled"""
        self.watchlist.enable_chart(symbol, timeframe, enabled)
        print(f"Chart {symbol} {timeframe} {'enabled' if enabled else 'disabled'}")

    def update_chart(self, symbol: str, timeframe: str):
        """Manually update a specific chart"""
        if self.auto_updater:
            self.auto_updater.update_now(symbol, timeframe)
            QMessageBox.information(self, "Update Started",
                                   f"Updating {symbol} {timeframe}...")

    def update_all_charts(self):
        """Manually update all charts"""
        if self.auto_updater:
            reply = QMessageBox.question(self, "Update All Charts",
                                        "Update all enabled charts now?",
                                        QMessageBox.StandardButton.Yes |
                                        QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.auto_updater.update_now()
                QMessageBox.information(self, "Update Started",
                                       "Updating all enabled charts...")

    def toggle_pause(self):
        """Toggle pause/resume scheduler"""
        if not self.auto_updater:
            return

        stats = self.auto_updater.get_stats()
        if stats['paused']:
            self.auto_updater.resume()
            self.pause_btn.setText("Pause Auto-Updates")
        else:
            self.auto_updater.pause()
            self.pause_btn.setText("Resume Auto-Updates")

        self.refresh_statistics()

    def show_settings(self):
        """Show scheduler settings dialog"""
        if not self.auto_updater:
            QMessageBox.warning(self, "No Scheduler", "Auto-updater is not initialized")
            return

        stats = self.auto_updater.get_stats()

        dialog = SettingsDialog(
            stats['check_interval'],
            stats['max_retries'],
            stats['retry_delay'],
            self
        )

        if dialog.exec() == QDialog.DialogCode.Accepted:
            values = dialog.get_values()

            # Apply settings
            self.auto_updater.set_check_interval(values['interval'])
            self.auto_updater.set_retry_settings(values['max_retries'], values['retry_delay'])

            QMessageBox.information(self, "Settings Updated",
                                   "Scheduler settings have been updated successfully.")
            self.refresh_statistics()
