"""
Toast Notification System
=========================
Temporary popup notifications that appear in the bottom-right corner and fade out.
"""

from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime
from typing import List, Optional


class ToastNotification(QWidget):
    """A single toast notification that appears and fades out"""

    closed = pyqtSignal(object)  # Emits self when closed

    def __init__(self, title: str, message: str, notification_type: str = 'info',
                 duration: int = 5000, parent=None):
        super().__init__(parent)
        self.notification_type = notification_type
        self.duration = duration
        self.timestamp = datetime.now()

        # Set window flags for floating widget
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.initUI(title, message)
        self.setupAnimations()

        # Auto-dismiss timer
        self.dismiss_timer = QTimer()
        self.dismiss_timer.timeout.connect(self.fadeOut)
        self.dismiss_timer.start(duration)

    def initUI(self, title: str, message: str):
        """Initialize the toast UI"""
        # Set fixed width
        self.setFixedWidth(350)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # Header with icon, title, and close button
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        # Icon
        icon_label = QLabel(self.get_icon())
        icon_font = QFont()
        icon_font.setPointSize(18)
        icon_label.setFont(icon_font)
        header_layout.addWidget(icon_label)

        # Title
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, 1)

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.close_notification)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 0.1);
                border-radius: 12px;
            }
        """)
        header_layout.addWidget(close_btn)

        layout.addLayout(header_layout)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setMaximumHeight(100)
        layout.addWidget(message_label)

        # Timestamp
        timestamp_label = QLabel(self.timestamp.strftime("%H:%M:%S"))
        timestamp_label.setStyleSheet("color: rgba(0, 0, 0, 0.5); font-size: 9px;")
        layout.addWidget(timestamp_label)

        self.setLayout(layout)

        # Set style based on type
        self.set_style_by_type()

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
                QWidget {
                    background-color: #d4edda;
                    border: 2px solid #c3e6cb;
                    border-radius: 8px;
                }
                QLabel { color: #155724; }
            """,
            'error': """
                QWidget {
                    background-color: #f8d7da;
                    border: 2px solid #f5c6cb;
                    border-radius: 8px;
                }
                QLabel { color: #721c24; }
            """,
            'warning': """
                QWidget {
                    background-color: #fff3cd;
                    border: 2px solid #ffeaa7;
                    border-radius: 8px;
                }
                QLabel { color: #856404; }
            """,
            'info': """
                QWidget {
                    background-color: #d1ecf1;
                    border: 2px solid #bee5eb;
                    border-radius: 8px;
                }
                QLabel { color: #0c5460; }
            """
        }
        self.setStyleSheet(styles.get(self.notification_type, styles['info']))

    def setupAnimations(self):
        """Setup fade in/out animations"""
        # Opacity effect
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)

        # Fade in animation
        self.fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_animation.setDuration(300)
        self.fade_in_animation.setStartValue(0.0)
        self.fade_in_animation.setEndValue(1.0)
        self.fade_in_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # Fade out animation
        self.fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_animation.setDuration(300)
        self.fade_out_animation.setStartValue(1.0)
        self.fade_out_animation.setEndValue(0.0)
        self.fade_out_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_out_animation.finished.connect(self.on_fade_out_finished)

    def showToast(self):
        """Show the toast with fade-in animation"""
        self.show()
        self.fade_in_animation.start()

    def fadeOut(self):
        """Fade out the toast"""
        self.dismiss_timer.stop()
        self.fade_out_animation.start()

    def on_fade_out_finished(self):
        """Called when fade out animation finishes"""
        self.close_notification()

    def close_notification(self):
        """Close and remove this notification"""
        self.closed.emit(self)
        self.hide()
        self.deleteLater()

    def enterEvent(self, event):
        """Pause auto-dismiss when mouse hovers"""
        self.dismiss_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Resume auto-dismiss when mouse leaves"""
        # Restart with remaining time (simplified: just use 2 seconds)
        self.dismiss_timer.start(2000)
        super().leaveEvent(event)


class ToastManager:
    """Manages multiple toast notifications"""

    def __init__(self, parent_widget: QWidget, max_toasts: int = 5):
        """
        Initialize toast manager

        Args:
            parent_widget: Parent widget (usually main window)
            max_toasts: Maximum number of toasts to show at once
        """
        self.parent = parent_widget
        self.max_toasts = max_toasts
        self.toasts: List[ToastNotification] = []
        self.spacing = 10  # Spacing between toasts
        self.margin_bottom = 20  # Margin from bottom of screen
        self.margin_right = 20  # Margin from right of screen

        # History storage for notification panel
        self.history: List[dict] = []
        self.max_history = 100

    def show_toast(self, title: str, message: str, notification_type: str = 'info',
                   duration: int = 5000):
        """
        Show a new toast notification

        Args:
            title: Notification title
            message: Notification message
            notification_type: Type ('success', 'error', 'warning', 'info')
            duration: Duration in milliseconds (default 5 seconds)
        """
        # Store in history
        self.history.insert(0, {
            'timestamp': datetime.now().isoformat(),
            'title': title,
            'message': message,
            'type': notification_type
        })
        if len(self.history) > self.max_history:
            self.history.pop()

        # Remove oldest toast if max reached
        if len(self.toasts) >= self.max_toasts:
            oldest = self.toasts.pop(0)
            oldest.close_notification()

        # Create new toast
        toast = ToastNotification(title, message, notification_type, duration, self.parent)
        toast.closed.connect(self.on_toast_closed)

        # Add to list
        self.toasts.append(toast)

        # Position toast
        self.reposition_toasts()

        # Show with animation
        toast.showToast()

    def on_toast_closed(self, toast: ToastNotification):
        """Handle toast closure"""
        if toast in self.toasts:
            self.toasts.remove(toast)
            self.reposition_toasts()

    def reposition_toasts(self):
        """Reposition all visible toasts"""
        if not self.parent:
            return

        # Get parent widget geometry
        parent_rect = self.parent.geometry()

        # Start position (bottom-right)
        y_pos = parent_rect.height() - self.margin_bottom

        # Position each toast from bottom to top
        for toast in reversed(self.toasts):
            toast_height = toast.sizeHint().height()
            toast_width = toast.width()

            # Calculate position
            x_pos = parent_rect.width() - toast_width - self.margin_right
            y_pos = y_pos - toast_height

            # Move toast to position (relative to parent)
            toast.move(self.parent.mapToGlobal(QPoint(x_pos, y_pos)))

            # Update y for next toast
            y_pos = y_pos - self.spacing

    def clear_all(self):
        """Clear all active toasts"""
        for toast in self.toasts[:]:
            toast.close_notification()
        self.toasts.clear()

    def get_history(self, limit: int = 50) -> List[dict]:
        """Get notification history"""
        return self.history[:limit]

    # Convenience methods
    def notify_success(self, title: str, message: str, duration: int = 5000):
        """Show success toast"""
        self.show_toast(title, message, 'success', duration)

    def notify_error(self, title: str, message: str, duration: int = 8000):
        """Show error toast (longer duration)"""
        self.show_toast(title, message, 'error', duration)

    def notify_warning(self, title: str, message: str, duration: int = 6000):
        """Show warning toast"""
        self.show_toast(title, message, 'warning', duration)

    def notify_info(self, title: str, message: str, duration: int = 4000):
        """Show info toast"""
        self.show_toast(title, message, 'info', duration)

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
