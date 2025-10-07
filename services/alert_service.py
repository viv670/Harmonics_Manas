"""
Alert Service

Business logic for price alerts and notifications.
"""

from typing import List, Dict, Optional, Callable
from datetime import datetime
import logging
from pathlib import Path

from exceptions import AlertError, AlertDeliveryError, InvalidAlertError
from logging_config import get_logger


class AlertService:
    """
    Service for alert management.

    Handles alert creation, triggering, and delivery.
    """

    def __init__(self, alert_log_path: str = 'data/alerts.log'):
        """
        Initialize alert service.

        Args:
            alert_log_path: Path to alert log file
        """
        self.alert_log_path = Path(alert_log_path)
        self.alert_log_path.parent.mkdir(exist_ok=True)
        self.logger = get_logger()

        self.active_alerts = []
        self.alert_handlers = []

    def register_alert_handler(self, handler: Callable):
        """
        Register alert delivery handler.

        Args:
            handler: Callable that takes (alert_data) and delivers alert
        """
        self.alert_handlers.append(handler)
        self.logger.info(f"Registered alert handler: {handler.__name__}")

    def create_alert(
        self,
        alert_type: str,
        symbol: str,
        condition: str,
        target_price: float,
        message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create new alert.

        Args:
            alert_type: Type of alert ('price', 'pattern', 'signal')
            symbol: Trading symbol
            condition: Condition ('above', 'below', 'cross_above', 'cross_below')
            target_price: Target price
            message: Optional custom message
            metadata: Optional metadata

        Returns:
            Alert dictionary
        """
        try:
            alert = {
                'id': len(self.active_alerts) + 1,
                'type': alert_type,
                'symbol': symbol,
                'condition': condition,
                'target_price': target_price,
                'message': message or f"{symbol} {condition} {target_price}",
                'created_at': datetime.now(),
                'status': 'active',
                'metadata': metadata or {}
            }

            self.active_alerts.append(alert)
            self.logger.info(f"Created alert {alert['id']}: {alert['message']}")

            return alert

        except Exception as e:
            raise AlertError(f"Failed to create alert: {e}") from e

    def check_alerts(self, symbol: str, current_price: float, previous_price: Optional[float] = None):
        """
        Check if any alerts should be triggered.

        Args:
            symbol: Trading symbol
            current_price: Current price
            previous_price: Previous price (for cross conditions)

        Returns:
            List of triggered alerts
        """
        triggered = []

        for alert in self.active_alerts:
            if alert['status'] != 'active' or alert['symbol'] != symbol:
                continue

            should_trigger = False

            condition = alert['condition']
            target = alert['target_price']

            if condition == 'above' and current_price > target:
                should_trigger = True

            elif condition == 'below' and current_price < target:
                should_trigger = True

            elif condition == 'cross_above' and previous_price is not None:
                if previous_price <= target < current_price:
                    should_trigger = True

            elif condition == 'cross_below' and previous_price is not None:
                if previous_price >= target > current_price:
                    should_trigger = True

            if should_trigger:
                self._trigger_alert(alert, current_price)
                triggered.append(alert)

        return triggered

    def _trigger_alert(self, alert: Dict, current_price: float):
        """
        Trigger alert and deliver via handlers.

        Args:
            alert: Alert dictionary
            current_price: Current price that triggered alert
        """
        alert['status'] = 'triggered'
        alert['triggered_at'] = datetime.now()
        alert['trigger_price'] = current_price

        self.logger.info(f"Alert triggered: {alert['message']} at {current_price}")

        # Log to file
        self._log_alert(alert)

        # Deliver via handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Alert delivery failed: {e}")

    def _log_alert(self, alert: Dict):
        """Log alert to file"""
        try:
            with open(self.alert_log_path, 'a') as f:
                timestamp = alert.get('triggered_at', datetime.now()).isoformat()
                f.write(f"{timestamp} | {alert['symbol']} | {alert['message']} | {alert.get('trigger_price')}\n")
        except Exception as e:
            self.logger.error(f"Failed to log alert: {e}")

    def get_active_alerts(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get active alerts.

        Args:
            symbol: Optional symbol filter

        Returns:
            List of active alerts
        """
        alerts = [a for a in self.active_alerts if a['status'] == 'active']

        if symbol:
            alerts = [a for a in alerts if a['symbol'] == symbol]

        return alerts

    def cancel_alert(self, alert_id: int):
        """
        Cancel alert.

        Args:
            alert_id: Alert ID
        """
        for alert in self.active_alerts:
            if alert['id'] == alert_id:
                alert['status'] = 'cancelled'
                self.logger.info(f"Cancelled alert {alert_id}")
                return

        raise InvalidAlertError(f"Alert {alert_id} not found")

    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """
        Get alert history.

        Args:
            limit: Maximum number of alerts to return

        Returns:
            List of triggered/cancelled alerts
        """
        history = [a for a in self.active_alerts if a['status'] in ('triggered', 'cancelled')]
        history.sort(key=lambda a: a.get('triggered_at', a['created_at']), reverse=True)

        return history[:limit]

    def cleanup_old_alerts(self):
        """Remove triggered and cancelled alerts"""
        before_count = len(self.active_alerts)

        self.active_alerts = [a for a in self.active_alerts if a['status'] == 'active']

        removed = before_count - len(self.active_alerts)
        if removed > 0:
            self.logger.info(f"Cleaned up {removed} old alerts")


# Default alert handlers
def console_alert_handler(alert: Dict):
    """Print alert to console"""
    print(f"\n🔔 ALERT: {alert['message']}")
    print(f"   Symbol: {alert['symbol']}")
    print(f"   Price: {alert.get('trigger_price')}")
    print()


def log_alert_handler(alert: Dict):
    """Log alert using logger"""
    logger = get_logger()
    logger.warning(f"ALERT: {alert['message']} - {alert['symbol']} @ {alert.get('trigger_price')}")


if __name__ == "__main__":
    print("Testing Alert Service...")
    print()

    service = AlertService('test_alerts.log')

    # Register handlers
    service.register_alert_handler(console_alert_handler)
    service.register_alert_handler(log_alert_handler)

    # Create alerts
    alert1 = service.create_alert(
        'price',
        'BTCUSDT',
        'above',
        50000,
        "BTC above 50k!"
    )

    alert2 = service.create_alert(
        'price',
        'BTCUSDT',
        'below',
        45000,
        "BTC below 45k!"
    )

    print(f"Created {len(service.active_alerts)} alerts")

    # Check alerts
    triggered = service.check_alerts('BTCUSDT', 51000, 49000)
    print(f"Triggered: {len(triggered)} alerts")

    # Get active
    active = service.get_active_alerts('BTCUSDT')
    print(f"Active: {len(active)} alerts")

    print()
    print("✅ Alert Service ready!")
