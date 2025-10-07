"""
Pattern Monitor Service - Core monitoring logic for automated pattern detection

This service:
1. Monitors for newly detected patterns after data updates
2. Tracks price movement toward PRZ zones
3. Detects PRZ entry
4. Sends alerts through AlertManager
5. Updates signal database

Designed to be triggered after auto-updater downloads new data.
"""

import pandas as pd
import json
from typing import Dict, List, Optional, Set
from datetime import datetime
from pathlib import Path

# Import detection modules
from extremum import detect_extremum_points
from formed_xabcd import detect_xabcd_patterns
from formed_abcd import detect_strict_abcd_patterns
from unformed_abcd import detect_unformed_abcd_patterns_optimized
from unformed_xabcd import detect_strict_unformed_xabcd_patterns

# Import our new modules
from signal_database import (
    SignalDatabase,
    TradingSignal,
    generate_signal_id,
    create_signal_from_pattern,
    create_price_alerts_for_signal
)
from alert_manager import AlertManager, AlertConfig


class PatternMonitorService:
    """
    Core pattern monitoring service

    Monitors patterns for a single symbol/timeframe combination.
    Should be instantiated per symbol-timeframe pair.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        signal_db: Optional[SignalDatabase] = None,
        alert_manager: Optional[AlertManager] = None,
        extremum_length: int = 1,
        approaching_threshold_pct: float = 5.0,  # Alert when within 5% of PRZ
        initial_load: bool = False  # If True, this is initial load (no alerts)
    ):
        """
        Initialize pattern monitor

        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '4h', '1d')
            signal_db: Optional SignalDatabase instance (creates new if None)
            alert_manager: Optional AlertManager instance (creates new if None)
            extremum_length: Length parameter for extremum detection
            approaching_threshold_pct: Distance % to trigger 'approaching' alert
            initial_load: If True, suppress alerts for existing patterns
        """
        self.symbol = symbol
        self.timeframe = timeframe
        self.extremum_length = extremum_length
        self.approaching_threshold_pct = approaching_threshold_pct
        self.initial_load = initial_load

        # Initialize database and alert manager
        self.db = signal_db or SignalDatabase()
        self.alert_manager = alert_manager or AlertManager()

        # Track which alerts we've already sent for each signal
        # Format: {signal_id: set(['detected', 'approaching', 'entered'])}
        self.sent_alerts: Dict[str, Set[str]] = {}

        # Track existing pattern IDs from startup (to avoid alerting on them)
        self.startup_pattern_ids: Set[str] = set()

        print(f"✅ Pattern Monitor initialized for {symbol} {timeframe}")

    def process_new_data(self, data: pd.DataFrame) -> Dict:
        """
        Process new data after auto-update

        This is the main entry point called after data is updated.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            Dictionary with processing results
        """
        print(f"\n{'='*80}")
        print(f"🔍 Pattern Monitor Processing: {self.symbol} {self.timeframe}")
        print(f"{'='*80}")
        print(f"Data bars: {len(data)}")
        print(f"Date range: {data.index[0]} to {data.index[-1]}")

        results = {
            'new_patterns_detected': 0,
            'patterns_approaching': 0,
            'patterns_entered': 0,
            'alerts_sent': 0,
            'errors': []
        }

        try:
            # Get current price
            current_price = float(data['Close'].iloc[-1])
            print(f"Current price: ${current_price:.2f}")

            # OPTIMIZATION: Only run pattern detection if latest candle is an extremum
            # Regular candles cannot complete patterns, only extremum points can
            print("\n🔍 Checking if latest candle is an extremum point...")
            extremum_points = detect_extremum_points(data, length=self.extremum_length)

            if len(extremum_points) == 0:
                print("  ⏭️ No extremum points found - skipping pattern detection")
                detected_patterns = []
            else:
                # Check if the last extremum is at the latest candle
                last_extremum = extremum_points[-1]
                last_extremum_bar_index = last_extremum[3]  # (timestamp, price, is_high, bar_index)
                latest_bar_index = len(data) - 1

                if last_extremum_bar_index == latest_bar_index:
                    print(f"  ✅ Latest candle IS an extremum (bar {latest_bar_index}) - running pattern detection")
                    # Step 1: Detect patterns
                    detected_patterns = self._detect_patterns(data)
                    print(f"\n📊 Detected {len(detected_patterns)} formed patterns")
                else:
                    print(f"  ⏭️ Latest candle is NOT an extremum (last extremum at bar {last_extremum_bar_index}, current bar {latest_bar_index})")
                    print(f"  ⏭️ Skipping pattern detection - no new patterns can form without extremum")
                    detected_patterns = []

            # Step 2: Check for new patterns and update database
            # Note: This only runs if latest candle is an extremum
            # If not an extremum, detected_patterns = [] and this loop is skipped
            for pattern in detected_patterns:
                signal_id = generate_signal_id(self.symbol, self.timeframe, pattern)

                # Check if this is a new pattern
                existing_signal = self.db.get_signal(signal_id)

                if not existing_signal:
                    # NEW PATTERN DETECTED!

                    # Create signal object
                    signal = create_signal_from_pattern(
                        self.symbol,
                        self.timeframe,
                        pattern,
                        current_price
                    )

                    # Add to database
                    if self.db.add_signal(signal):
                        results['new_patterns_detected'] += 1

                        # Create price alerts for Fibonacci levels and harmonic points (disabled by default)
                        create_price_alerts_for_signal(self.db, signal, pattern)

                        # Only alert if NOT initial load
                        if self.initial_load:
                            # Mark as existing pattern from startup (no alert)
                            self.startup_pattern_ids.add(signal_id)
                            print(f"  📝 Loaded existing pattern (no alert): {pattern.get('name', 'Unknown')}")
                        else:
                            # This is genuinely new - send alert!
                            print(f"\n🎯 NEW PATTERN: {pattern.get('name', 'Unknown')}")
                            self._send_alert_if_needed(signal_id, signal.__dict__, 'detected')
                            results['alerts_sent'] += 1
                else:
                    # Track existing patterns on initial load
                    if self.initial_load and signal_id not in self.startup_pattern_ids:
                        self.startup_pattern_ids.add(signal_id)

            # Step 3: Update existing signals and check for status changes
            # This ALWAYS runs (even when no new patterns) to track price movements
            # and update statuses (detected → approaching → entered)
            active_signals = self.db.get_signals_by_symbol(self.symbol, active_only=True)
            print(f"\n📋 Monitoring {len(active_signals)} active signals")

            for signal in active_signals:
                signal_id = signal['signal_id']

                # Update current price and distance
                updates = {
                    'current_price': current_price,
                    'distance_to_prz_pct': self._calculate_distance_to_prz(
                        current_price,
                        signal['prz_min'],
                        signal['prz_max']
                    )
                }

                # Check status transitions
                old_status = signal['status']
                is_formed = bool(signal.get('is_formed', 0))  # Convert from int (SQLite) to bool

                # Check for pattern outcome (completed/invalidated) if pattern has entered PRZ
                if old_status == 'entered' and is_formed:
                    outcome_status = self._check_pattern_outcome(
                        signal,
                        current_price,
                        data
                    )
                    if outcome_status:
                        new_status = outcome_status
                        print(f"  ✅ Pattern outcome: {old_status} → {new_status}")
                    else:
                        # No outcome yet, maintain current status
                        new_status = old_status
                else:
                    # Normal status progression for patterns not yet entered
                    new_status = self._determine_status(
                        current_price,
                        signal['prz_min'],
                        signal['prz_max'],
                        old_status,
                        is_formed
                    )

                if new_status != old_status:
                    updates['status'] = new_status
                    print(f"  📌 Status change: {old_status} → {new_status}")

                # Check price alerts for this signal (Fibonacci and harmonic points)
                self._check_price_alerts(signal_id, current_price, results)

                # Update database
                self.db.update_signal(signal_id, updates)

                # Create updated signal dict for alerts
                updated_signal = {**signal, **updates}

                # Send alerts based on status
                if new_status == 'approaching' and old_status == 'detected':
                    self._send_alert_if_needed(signal_id, updated_signal, 'approaching')
                    results['patterns_approaching'] += 1
                    results['alerts_sent'] += 1

                elif new_status == 'entered' and old_status in ('detected', 'approaching'):
                    self._send_alert_if_needed(signal_id, updated_signal, 'entered')
                    results['patterns_entered'] += 1
                    results['alerts_sent'] += 1

                elif new_status == 'completed' and old_status == 'entered':
                    self._send_alert_if_needed(signal_id, updated_signal, 'completed')
                    results['alerts_sent'] += 1
                    print(f"  🎯 Pattern completed successfully!")

                    # Remove all price alerts when pattern completes (hits 161.8% Fib)
                    self.db.delete_signal_alerts(signal_id)
                    print(f"  🗑️ Removed all price alerts for completed pattern")

                elif new_status == 'invalidated' and old_status == 'entered':
                    self._send_alert_if_needed(signal_id, updated_signal, 'invalidated')
                    results['alerts_sent'] += 1
                    print(f"  ❌ Pattern invalidated!")

            # Summary
            print(f"\n{'='*80}")
            print(f"📊 MONITORING SUMMARY")
            print(f"{'='*80}")
            print(f"New patterns detected: {results['new_patterns_detected']}")
            print(f"Patterns approaching PRZ: {results['patterns_approaching']}")
            print(f"Patterns entered PRZ: {results['patterns_entered']}")
            print(f"Total alerts sent: {results['alerts_sent']}")

        except Exception as e:
            error_msg = f"Error in pattern monitoring: {e}"
            print(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            import traceback
            traceback.print_exc()

        return results

    def _detect_patterns(self, data: pd.DataFrame) -> List[Dict]:
        """
        Detect both formed and unformed patterns in data

        Returns:
            List of detected pattern dictionaries
        """
        all_patterns = []

        try:
            # Use ALL available data for 100% accuracy
            # Pattern detection only runs when new candles arrive (based on timeframe)
            # so it's not wasteful - 4h chart only checks every 4 hours
            print(f"  ℹ️ Analyzing {len(data)} candles for pattern detection")

            # Detect extremum points
            extremum_points = detect_extremum_points(data, length=self.extremum_length)

            if len(extremum_points) < 4:
                print("  ⚠️ Not enough extremum points for pattern detection")
                return all_patterns

            # Convert to indexed format
            extremums_indexed = []
            for ext in extremum_points:
                timestamp, price, is_high, bar_index = ext
                extremums_indexed.append((bar_index, price, is_high, bar_index))

            # Prepare data for detection (needs 'Date' column)
            data_with_date = data.reset_index()
            if data.index.name == 'Time':
                data_with_date.rename(columns={'Time': 'Date'}, inplace=True)
            elif 'Date' not in data_with_date.columns and data.index.name:
                data_with_date['Date'] = data_with_date.index

            # Detect FORMED ABCD patterns
            if len(extremums_indexed) >= 4:
                try:
                    formed_abcd = detect_strict_abcd_patterns(
                        extremums_indexed,
                        df=data_with_date
                    )
                    # Filter to only formed (with D point)
                    formed_abcd = [p for p in formed_abcd if 'D' in p.get('points', {})]
                    # Mark as formed
                    for p in formed_abcd:
                        p['is_formed'] = True
                    all_patterns.extend(formed_abcd)
                    print(f"  Found {len(formed_abcd)} formed ABCD patterns")
                except Exception as e:
                    print(f"  ⚠️ Formed ABCD detection error: {e}")

            # Detect UNFORMED ABCD patterns
            if len(extremums_indexed) >= 3:
                try:
                    unformed_abcd = detect_unformed_abcd_patterns_optimized(
                        extremums_indexed,
                        df=data_with_date
                    )
                    # Mark as unformed
                    for p in unformed_abcd:
                        p['is_formed'] = False
                    all_patterns.extend(unformed_abcd)
                    print(f"  Found {len(unformed_abcd)} unformed ABCD patterns")
                except Exception as e:
                    print(f"  ⚠️ Unformed ABCD detection error: {e}")

            # Detect FORMED XABCD patterns
            if len(extremums_indexed) >= 5:
                try:
                    formed_xabcd = detect_xabcd_patterns(
                        extremums_indexed,
                        df=data_with_date
                    )
                    # Filter to only formed (with D point)
                    formed_xabcd = [p for p in formed_xabcd if 'D' in p.get('points', {})]
                    # Mark as formed
                    for p in formed_xabcd:
                        p['is_formed'] = True
                    all_patterns.extend(formed_xabcd)
                    print(f"  Found {len(formed_xabcd)} formed XABCD patterns")
                except Exception as e:
                    print(f"  ⚠️ Formed XABCD detection error: {e}")

            # Detect UNFORMED XABCD patterns
            if len(extremums_indexed) >= 4:
                try:
                    unformed_xabcd = detect_strict_unformed_xabcd_patterns(
                        extremums_indexed,
                        df=data_with_date
                    )
                    # Mark as unformed
                    for p in unformed_xabcd:
                        p['is_formed'] = False
                    all_patterns.extend(unformed_xabcd)
                    print(f"  Found {len(unformed_xabcd)} unformed XABCD patterns")
                except Exception as e:
                    print(f"  ⚠️ Unformed XABCD detection error: {e}")

        except Exception as e:
            print(f"❌ Pattern detection error: {e}")
            import traceback
            traceback.print_exc()

        return all_patterns

    def _calculate_distance_to_prz(
        self,
        current_price: float,
        prz_min: float,
        prz_max: float
    ) -> float:
        """
        Calculate percentage distance to PRZ

        Returns:
            Percentage distance (positive = away from PRZ, 0 = inside PRZ)
        """
        if prz_min <= 0:
            return 999.0  # Invalid PRZ

        if current_price < prz_min:
            # Below PRZ
            return ((prz_min - current_price) / current_price) * 100
        elif current_price > prz_max:
            # Above PRZ
            return ((current_price - prz_max) / current_price) * 100
        else:
            # Inside PRZ
            return 0.0

    def _determine_status(
        self,
        current_price: float,
        prz_min: float,
        prz_max: float,
        current_status: str,
        is_formed: bool = False
    ) -> str:
        """
        Determine signal status based on price position and pattern formation

        Args:
            is_formed: True if pattern has completed D point, False if D is projected

        Returns:
            'detected', 'approaching', or 'entered'
        """
        distance_pct = self._calculate_distance_to_prz(current_price, prz_min, prz_max)

        # FORMED patterns (D point exists)
        if is_formed:
            # If D exists, price should already be in/near PRZ
            if distance_pct == 0.0:
                return 'entered'
            elif distance_pct <= self.approaching_threshold_pct:
                return 'approaching'
            else:
                # Formed but price has moved away - keep as detected
                return 'detected'

        # UNFORMED patterns (D is projected)
        else:
            # Inside PRZ = would mean pattern has formed
            if distance_pct == 0.0:
                return 'entered'

            # Within threshold = approaching the projected D
            if distance_pct <= self.approaching_threshold_pct:
                return 'approaching'

            # Otherwise = just detected, waiting for price to approach
            return 'detected'

    def _check_pattern_outcome(
        self,
        signal: Dict,
        current_price: float,
        data: pd.DataFrame
    ) -> Optional[str]:
        """
        Check if an entered pattern has completed or been invalidated

        Logic based on backtesting outcome tracking:
        - Completed: Price reversed 2% in expected direction
        - Invalidated: Price broke 2% in opposite direction

        Args:
            signal: Signal dictionary from database
            current_price: Current price
            data: Full price data

        Returns:
            'completed', 'invalidated', or None (still pending)
        """
        try:
            # Extract pattern info
            direction = signal['direction']
            is_bullish = (direction == 'bullish')

            # Get D point from pattern points
            import json
            points_json = signal.get('points_json', '{}')
            points = json.loads(points_json) if points_json else {}

            # Find D point price
            d_point = points.get('D')
            if not d_point:
                return None  # Can't check outcome without D point

            # Extract D price from different possible formats
            if isinstance(d_point, (list, tuple)) and len(d_point) > 1:
                d_price = float(d_point[1])
                d_index = int(d_point[0])
            elif isinstance(d_point, dict):
                d_price = float(d_point.get('price', 0))
                d_index = int(d_point.get('index', 0))
            else:
                return None

            if d_price <= 0:
                return None

            # Find D bar in data
            if d_index < 0 or d_index >= len(data):
                return None

            # Check up to 10 bars after D point
            reversal_threshold = 0.02  # 2% movement
            max_bars_to_check = min(10, len(data) - d_index - 1)

            if max_bars_to_check <= 0:
                return None  # Not enough data after D

            # Check price action after D
            for i in range(1, max_bars_to_check + 1):
                bar_index = d_index + i
                if bar_index >= len(data):
                    break

                bar = data.iloc[bar_index]

                if is_bullish:
                    # Bullish: D is low, should reverse up
                    reversal_amount = (bar['High'] - d_price) / d_price
                    if reversal_amount > reversal_threshold:
                        return 'completed'
                    # Check failure: price goes 2% below D
                    if bar['Low'] < d_price * 0.98:
                        return 'invalidated'
                else:
                    # Bearish: D is high, should reverse down
                    reversal_amount = (d_price - bar['Low']) / d_price
                    if reversal_amount > reversal_threshold:
                        return 'completed'
                    # Check failure: price goes 2% above D
                    if bar['High'] > d_price * 1.02:
                        return 'invalidated'

            # No outcome yet - still pending
            return None

        except Exception as e:
            print(f"  ⚠️ Error checking pattern outcome: {e}")
            return None

    def _check_price_alerts(self, signal_id: str, current_price: float, results: Dict) -> None:
        """
        Check if current price has triggered any enabled price alerts

        Args:
            signal_id: Signal ID to check alerts for
            current_price: Current market price
            results: Results dict to update alert count
        """
        # Get active (enabled, non-triggered) price alerts
        active_alerts = self.db.get_active_price_alerts(signal_id)

        if not active_alerts:
            return  # No enabled alerts

        for alert in active_alerts:
            alert_id = alert['alert_id']
            price_level = alert['price_level']
            level_name = alert['level_name']
            alert_type = alert['alert_type']

            # Check if price has touched this level (simple touch detection)
            # For more accuracy, could use high/low data, but current_price works for real-time
            tolerance = price_level * 0.001  # 0.1% tolerance
            if abs(current_price - price_level) <= tolerance:
                # Price touched this level - trigger alert
                print(f"  🔔 Price alert triggered: {level_name} at ${price_level:.2f}")

                # Mark as triggered in database
                self.db.mark_price_alert_triggered(alert_id)

                # Send alert notification
                # Create a simple alert dict for the alert manager
                alert_signal = {
                    'symbol': self.symbol,
                    'timeframe': self.timeframe,
                    'pattern_name': f"{alert_type.replace('_', ' ').title()} - {level_name}",
                    'direction': 'Price Alert',
                    'current_price': current_price,
                    'prz_min': price_level,
                    'prz_max': price_level,
                    'distance_to_prz_pct': 0
                }

                # Send alert with custom type
                self.alert_manager.send_alert(alert_signal, 'price_level')
                results['alerts_sent'] = results.get('alerts_sent', 0) + 1

    def _send_alert_if_needed(
        self,
        signal_id: str,
        signal: Dict,
        alert_type: str
    ) -> bool:
        """
        Send alert if not already sent

        Returns:
            True if alert was sent
        """
        # Check if we've already sent this alert
        if signal_id not in self.sent_alerts:
            self.sent_alerts[signal_id] = set()

        if alert_type in self.sent_alerts[signal_id]:
            # Already sent this alert type for this signal
            return False

        # Send alert
        success = self.alert_manager.send_alert(signal, alert_type)

        if success:
            # Mark as sent
            self.sent_alerts[signal_id].add(alert_type)

            # Also update database
            alerts_sent = json.loads(signal.get('alerts_sent_json', '[]'))
            if alert_type not in alerts_sent:
                alerts_sent.append(alert_type)
                self.db.update_signal(signal_id, {
                    'alerts_sent_json': json.dumps(alerts_sent)
                })

        return success

    def cleanup_old_signals(self, days: int = 30):
        """Remove old completed/invalidated signals"""
        removed = self.db.cleanup_old_signals(days)
        print(f"🗑️ Cleaned up {removed} old signals (older than {days} days)")
        return removed

    def get_active_signals_summary(self) -> Dict:
        """Get summary of active signals"""
        active = self.db.get_signals_by_symbol(self.symbol, active_only=True)

        summary = {
            'total_active': len(active),
            'by_status': {},
            'signals': active
        }

        for signal in active:
            status = signal['status']
            summary['by_status'][status] = summary['by_status'].get(status, 0) + 1

        return summary


# Multi-symbol monitor
class MultiSymbolMonitor:
    """
    Manages monitoring for multiple symbol/timeframe combinations
    """

    def __init__(
        self,
        watchlist: List[Dict],  # [{'symbol': 'BTCUSDT', 'timeframe': '4h'}, ...]
        shared_db: Optional[SignalDatabase] = None,
        shared_alert_manager: Optional[AlertManager] = None,
        initial_load: bool = True  # First run - don't alert on existing patterns
    ):
        """
        Initialize multi-symbol monitor

        Args:
            watchlist: List of symbol/timeframe dicts to monitor
            shared_db: Shared database instance for all monitors
            shared_alert_manager: Shared alert manager for all monitors
            initial_load: If True, suppress alerts for existing patterns on first scan
        """
        self.watchlist = watchlist
        self.db = shared_db or SignalDatabase()
        self.alert_manager = shared_alert_manager or AlertManager()
        self.initial_load_complete = False

        # Create monitor for each symbol/timeframe
        self.monitors: Dict[str, PatternMonitorService] = {}

        for item in watchlist:
            symbol = item['symbol']
            timeframe = item['timeframe']
            key = f"{symbol}_{timeframe}"

            self.monitors[key] = PatternMonitorService(
                symbol=symbol,
                timeframe=timeframe,
                signal_db=self.db,
                alert_manager=self.alert_manager,
                initial_load=initial_load
            )

        print(f"\n✅ Multi-Symbol Monitor initialized for {len(self.monitors)} pairs")
        if initial_load:
            print("ℹ️  Initial load mode: Existing patterns will be loaded silently (no alerts)")

    def process_update(self, symbol: str, timeframe: str, data: pd.DataFrame) -> Dict:
        """
        Process data update for a specific symbol/timeframe

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            data: Updated OHLCV data

        Returns:
            Processing results
        """
        key = f"{symbol}_{timeframe}"

        if key not in self.monitors:
            print(f"⚠️ No monitor found for {symbol} {timeframe}")
            return {'error': 'Monitor not found'}

        # Process the update
        results = self.monitors[key].process_new_data(data)

        # After first update of all monitors, switch off initial_load mode
        if not self.initial_load_complete:
            # Check if all monitors have processed at least once
            all_processed = all(
                monitor.startup_pattern_ids or not monitor.initial_load
                for monitor in self.monitors.values()
            )
            if all_processed:
                self.initial_load_complete = True
                # Disable initial_load flag on all monitors
                for monitor in self.monitors.values():
                    monitor.initial_load = False
                print("\n✅ Initial load complete - alerts enabled for new patterns")

        return results

    def get_all_active_signals(self) -> List[Dict]:
        """Get all active signals across all monitored pairs"""
        return self.db.get_active_signals()

    def cleanup_all_old_signals(self, days: int = 30):
        """Cleanup old signals from database"""
        return self.db.cleanup_old_signals(days)


# Standalone test
if __name__ == '__main__':
    print("=" * 80)
    print("PATTERN MONITOR SERVICE TEST")
    print("=" * 80)

    # Load test data
    test_file = Path('data/hypeusdt_4h.csv')

    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
    else:
        # Load data
        df = pd.read_csv(test_file)
        df.columns = [col.capitalize() for col in df.columns]

        if 'Time' in df.columns:
            df['Time'] = pd.to_datetime(df['Time'])
            df.set_index('Time', inplace=True)
        elif 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)

        # Use last 300 bars for test
        test_data = df.tail(300).copy()

        print(f"\nLoaded {len(test_data)} bars")
        print(f"Date range: {test_data.index[0]} to {test_data.index[-1]}")

        # Create monitor
        monitor = PatternMonitorService(
            symbol='HYPEUSDT',
            timeframe='4h'
        )

        # Process data
        results = monitor.process_new_data(test_data)

        # Show summary
        print("\n" + "=" * 80)
        print("📊 TEST RESULTS")
        print("=" * 80)
        print(f"New patterns: {results['new_patterns_detected']}")
        print(f"Approaching: {results['patterns_approaching']}")
        print(f"Entered: {results['patterns_entered']}")
        print(f"Alerts sent: {results['alerts_sent']}")

        # Show active signals
        summary = monitor.get_active_signals_summary()
        print(f"\nActive signals: {summary['total_active']}")
        for status, count in summary['by_status'].items():
            print(f"  {status}: {count}")
