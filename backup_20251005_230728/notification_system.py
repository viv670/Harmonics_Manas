"""
Notification System
===================
In-app notification system for displaying update alerts and errors.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette
from datetime import datetime
from typing import List


class NotificationItem(QFrame):
    """A single notification item"""

    closed = pyqtSignal(object)  # Emits self when closed

    def __init__(self, title: str, message: str, notification_type: str = 'info', parent=None):
        super().__init__(parent)
        self.notification_type = notification_type
        self.timestamp = datetime.now()

        self.initUI(title, message)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)

        # Set background color based on type
        self.set_style_by_type()

        # Auto-dismiss timer for success/info notifications
        if notification_type in ['success', 'info']:
            self.dismiss_timer = QTimer()
            self.dismiss_timer.timeout.connect(self.close_notification)
            self.dismiss_timer.start(10000)  # 10 seconds

    def initUI(self, title: str, message: str):
        """Initialize the notification UI"""
        layout = QVBoxLayout()

        # Header with title and close button
        header_layout = QHBoxLayout()

        # Icon and title
        title_layout = QHBoxLayout()

        icon_label = QLabel(self.get_icon())
        icon_font = QFont()
        icon_font.setPointSize(16)
        icon_label.setFont(icon_font)
        title_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        header_layout.addLayout(title_layout)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setMaximumWidth(30)
        close_btn.clicked.connect(self.close_notification)
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)

        # Timestamp
        timestamp_label = QLabel(self.timestamp.strftime("%H:%M:%S"))
        timestamp_label.setStyleSheet("color: gray; font-size: 9px;")
        layout.addWidget(timestamp_label)

        self.setLayout(layout)

    def get_icon(self) -> str:
        """Get icon based on notification type"""
        icons = {
            'success': '✓',
            'error': '✗',
            'warning': '⚠',
            'info': 'ℹ'
        }
        return icons.get(self.notification_type, 'ℹ')

    def set_style_by_type(self):
        """Set stylesheet based on notification type"""
        styles = {
            'success': """
                QFrame {
                    background-color: #d4edda;
                    border: 1px solid #c3e6cb;
                    border-radius: 4px;
                    padding: 10px;
                }
                QLabel { color: #155724; }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #155724;
                    font-weight: bold;
                }
            """,
            'error': """
                QFrame {
                    background-color: #f8d7da;
                    border: 1px solid #f5c6cb;
                    border-radius: 4px;
                    padding: 10px;
                }
                QLabel { color: #721c24; }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #721c24;
                    font-weight: bold;
                }
            """,
            'warning': """
                QFrame {
                    background-color: #fff3cd;
                    border: 1px solid #ffeaa7;
                    border-radius: 4px;
                    padding: 10px;
                }
                QLabel { color: #856404; }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #856404;
                    font-weight: bold;
                }
            """,
            'info': """
                QFrame {
                    background-color: #d1ecf1;
                    border: 1px solid #bee5eb;
                    border-radius: 4px;
                    padding: 10px;
                }
                QLabel { color: #0c5460; }
                QPushButton {
                    background-color: transparent;
                    border: none;
                    color: #0c5460;
                    font-weight: bold;
                }
            """
        }
        self.setStyleSheet(styles.get(self.notification_type, styles['info']))

    def close_notification(self):
        """Close and remove this notification"""
        self.closed.emit(self)


class NotificationPanel(QWidget):
    """Panel for displaying notifications"""

    def __init__(self, max_notifications: int = 10, parent=None):
        super().__init__(parent)
        self.max_notifications = max_notifications
        self.notifications: List[NotificationItem] = []

        self.initUI()

    def initUI(self):
        """Initialize the notification panel UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 5, 10, 5)

        title = QLabel("Notifications")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)

        # Clear all button
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        header_layout.addWidget(self.clear_btn)

        header.setLayout(header_layout)
        layout.addWidget(header)

        # Scroll area for notifications
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Container for notifications
        self.notification_container = QWidget()
        self.notification_layout = QVBoxLayout()
        self.notification_layout.setSpacing(5)
        self.notification_layout.addStretch()  # Push notifications to top
        self.notification_container.setLayout(self.notification_layout)

        scroll.setWidget(self.notification_container)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def add_notification(self, title: str, message: str, notification_type: str = 'info'):
        """Add a new notification"""
        # Create notification item
        notification = NotificationItem(title, message, notification_type, self)
        notification.closed.connect(self.remove_notification)

        # Add to list and layout
        self.notifications.insert(0, notification)  # Add to front
        self.notification_layout.insertWidget(0, notification)  # Insert at top

        # Remove oldest if exceeding max
        if len(self.notifications) > self.max_notifications:
            oldest = self.notifications.pop()
            self.notification_layout.removeWidget(oldest)
            oldest.deleteLater()

        print(f"Notification added: [{notification_type}] {title}")

    def remove_notification(self, notification: NotificationItem):
        """Remove a specific notification"""
        if notification in self.notifications:
            self.notifications.remove(notification)
            self.notification_layout.removeWidget(notification)
            notification.deleteLater()

    def clear_all(self):
        """Clear all notifications"""
        for notification in self.notifications[:]:  # Copy list to avoid modification during iteration
            self.notification_layout.removeWidget(notification)
            notification.deleteLater()
        self.notifications.clear()

    def get_notification_count(self) -> int:
        """Get current number of notifications"""
        return len(self.notifications)


class NotificationManager:
    """Manager for coordinating notifications across the app"""

    def __init__(self, notification_panel: NotificationPanel):
        self.panel = notification_panel

    def notify_success(self, title: str, message: str):
        """Show a success notification"""
        self.panel.add_notification(title, message, 'success')

    def notify_error(self, title: str, message: str):
        """Show an error notification"""
        self.panel.add_notification(title, message, 'error')

    def notify_warning(self, title: str, message: str):
        """Show a warning notification"""
        self.panel.add_notification(title, message, 'warning')

    def notify_info(self, title: str, message: str):
        """Show an info notification"""
        self.panel.add_notification(title, message, 'info')

    def notify_update_success(self, symbol: str, timeframe: str, candles: int):
        """Notification for successful update"""
        self.notify_success(
            f"Updated: {symbol} {timeframe}",
            f"Successfully updated {candles} candles"
        )

    def notify_update_failed(self, symbol: str, timeframe: str, error: str):
        """Notification for failed update"""
        self.notify_error(
            f"Update Failed: {symbol} {timeframe}",
            f"Failed after retries: {error}"
        )

    def notify_update_retry(self, symbol: str, timeframe: str, attempt: int, max_retries: int):
        """Notification for update retry"""
        self.notify_warning(
            f"Retrying: {symbol} {timeframe}",
            f"Retry attempt {attempt} of {max_retries}"
        )
