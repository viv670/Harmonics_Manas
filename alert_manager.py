"""
Alert Manager - Desktop notifications and sound alerts for trading signals

This module handles all alert mechanisms for the pattern monitoring system.
For the basic version, it supports:
- Windows desktop notifications
- System beep sound alerts
- Alert logging to file
"""

import winsound
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass

# Try to import Windows toast notifications
try:
    from win10toast import ToastNotifier
    TOAST_AVAILABLE = True
except ImportError:
    TOAST_AVAILABLE = False
    print("⚠️ win10toast not available. Desktop notifications disabled.")


@dataclass
class AlertConfig:
    """Configuration for alert system"""
    desktop_notifications: bool = True
    sound_alerts: bool = True
    log_alerts: bool = True
    log_file: str = "data/alerts.log"


class AlertManager:
    """Manages desktop notifications and sound alerts for trading signals"""

    def __init__(self, config: Optional[AlertConfig] = None):
        """Initialize alert manager"""
        self.config = config or AlertConfig()

        # Initialize toast notifier for Windows desktop notifications
        self.toaster = None
        if TOAST_AVAILABLE and self.config.desktop_notifications:
            self.toaster = ToastNotifier()

        # Setup logging
        if self.config.log_alerts:
            self._setup_logging()

    def _setup_logging(self):
        """Setup alert logging to file"""
        log_path = Path(self.config.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger('AlertManager')
        self.logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        if not self.logger.handlers:
            # File handler
            fh = logging.FileHandler(log_path)
            fh.setLevel(logging.INFO)

            # Format
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            fh.setFormatter(formatter)

            self.logger.addHandler(fh)

    def send_alert(self, signal: Dict, alert_type: str) -> bool:
        """
        Send alert for a trading signal

        Args:
            signal: Signal dictionary from database
            alert_type: 'detected', 'approaching', or 'entered'

        Returns:
            True if alert sent successfully
        """
        try:
            # Format alert message
            title, message = self._format_alert(signal, alert_type)

            # Send desktop notification
            if self.config.desktop_notifications and self.toaster:
                self._send_desktop_notification(title, message)

            # Play sound
            if self.config.sound_alerts:
                self._play_alert_sound(alert_type)

            # Log alert
            if self.config.log_alerts:
                self._log_alert(signal, alert_type, title, message)

            return True

        except Exception as e:
            print(f"❌ Error sending alert: {e}")
            return False

    def _format_alert(self, signal: Dict, alert_type: str) -> tuple[str, str]:
        """
        Format alert title and message

        Returns:
            (title, message) tuple
        """
        symbol = signal['symbol']
        timeframe = signal['timeframe']
        pattern_name = signal['pattern_name']
        direction = signal['direction']

        # Direction emoji
        direction_emoji = "🟢" if direction == 'bullish' else "🔴"

        # Alert type specific formatting
        if alert_type == 'detected':
            title = f"🎯 Pattern Detected: {symbol}"
            message = (
                f"{direction_emoji} {pattern_name.replace('_', ' ').title()}\n"
                f"Timeframe: {timeframe}\n"
                f"Direction: {direction.title()}\n"
                f"PRZ: ${signal['prz_min']:.2f} - ${signal['prz_max']:.2f}\n"
                f"Distance: {signal['distance_to_prz_pct']:.1f}%"
            )

        elif alert_type == 'approaching':
            title = f"⚡ Approaching PRZ: {symbol}"
            message = (
                f"{direction_emoji} {pattern_name.replace('_', ' ').title()}\n"
                f"Timeframe: {timeframe}\n"
                f"Current Price: ${signal['current_price']:.2f}\n"
                f"PRZ: ${signal['prz_min']:.2f} - ${signal['prz_max']:.2f}\n"
                f"Distance: {signal['distance_to_prz_pct']:.1f}%"
            )

        elif alert_type == 'entered':
            title = f"🎯 ENTERED PRZ: {symbol}"
            message = (
                f"{direction_emoji} {pattern_name.replace('_', ' ').title()}\n"
                f"Timeframe: {timeframe}\n"
                f"Entry: ${signal['entry_price']:.2f}\n"
                f"Stop Loss: ${signal['stop_loss']:.2f}\n"
                f"⚠️ READY TO TRADE!"
            )

        elif alert_type == 'price_level':
            title = f"📍 Price Level Alert: {symbol}"
            message = (
                f"{pattern_name}\n"
                f"Timeframe: {timeframe}\n"
                f"Current Price: ${signal['current_price']:.2f}\n"
                f"Level Hit: ${signal['prz_min']:.2f}"
            )

        else:
            title = f"Alert: {symbol}"
            message = f"{pattern_name} - {alert_type}"

        return title, message

    def _send_desktop_notification(self, title: str, message: str):
        """Send Windows desktop notification"""
        if not self.toaster:
            return

        try:
            # Show toast notification
            # Note: win10toast blocks thread, so we use threaded=True for non-blocking
            self.toaster.show_toast(
                title=title,
                msg=message,
                duration=10,  # seconds
                icon_path=None,  # Could add custom icon later
                threaded=True
            )
        except Exception as e:
            print(f"⚠️ Desktop notification error: {e}")

    def _play_alert_sound(self, alert_type: str):
        """Play system beep alert"""
        try:
            # Different beep patterns for different alert types
            if alert_type == 'detected':
                # Single beep (1000 Hz, 200ms)
                winsound.Beep(1000, 200)

            elif alert_type == 'approaching':
                # Double beep (1200 Hz, 150ms each)
                winsound.Beep(1200, 150)
                winsound.Beep(1200, 150)

            elif alert_type == 'entered':
                # Triple beep (1500 Hz, 200ms each) - most urgent
                winsound.Beep(1500, 200)
                winsound.Beep(1500, 200)
                winsound.Beep(1500, 200)

        except Exception as e:
            print(f"⚠️ Sound alert error: {e}")

    def _log_alert(self, signal: Dict, alert_type: str, title: str, message: str):
        """Log alert to file"""
        try:
            # Remove emojis and newlines for clean logging
            clean_title = title.encode('ascii', 'ignore').decode('ascii')
            clean_message = message.replace('\n', ' ').encode('ascii', 'ignore').decode('ascii')

            log_msg = (
                f"{alert_type.upper()} | {signal['symbol']} {signal['timeframe']} | "
                f"{signal['pattern_name']} | {clean_title} | {clean_message}"
            )
            self.logger.info(log_msg)
        except Exception as e:
            print(f"Alert logging error: {e}")

    def test_alerts(self):
        """Test all alert mechanisms"""
        print("\n🔔 Testing Alert System...")

        # Create test signal
        test_signal = {
            'symbol': 'BTCUSDT',
            'timeframe': '4h',
            'pattern_name': 'Gartley_bull',
            'direction': 'bullish',
            'prz_min': 95000.0,
            'prz_max': 96000.0,
            'current_price': 92000.0,
            'distance_to_prz_pct': 3.2,
            'entry_price': 95500.0,
            'stop_loss': 94000.0
        }

        # Test each alert type
        for alert_type in ['detected', 'approaching', 'entered']:
            print(f"\n  Testing {alert_type} alert...")
            self.send_alert(test_signal, alert_type)

            # Small delay between alerts
            import time
            time.sleep(1)

        print("\n✅ Alert test complete! Check notifications and alert log.")


# Standalone test
if __name__ == '__main__':
    print("=" * 80)
    print("ALERT MANAGER TEST")
    print("=" * 80)

    # Create alert manager
    config = AlertConfig(
        desktop_notifications=True,
        sound_alerts=True,
        log_alerts=True
    )

    manager = AlertManager(config)

    # Run tests
    manager.test_alerts()
