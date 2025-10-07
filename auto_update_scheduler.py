"""
Auto-Update Scheduler
=====================
Background service that automatically updates charts based on their timeframes.
Enhanced with retry logic, configurable intervals, and update history tracking.
Integrated with pattern monitoring for automated alerts.
"""

import threading
import time
from datetime import datetime
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor
from watchlist_manager import WatchlistManager, ChartEntry
from binance_downloader import BinanceDataDownloader
from update_history_logger import UpdateHistoryLogger

# Pattern monitoring integration
try:
    from pattern_monitor_service import MultiSymbolMonitor
    PATTERN_MONITORING_AVAILABLE = True
except ImportError:
    PATTERN_MONITORING_AVAILABLE = False
    print("⚠️ Pattern monitoring not available")


class AutoUpdateScheduler:
    """Background scheduler for automatic chart updates"""

    def __init__(self, watchlist_manager: WatchlistManager,
                 check_interval: int = 300,  # 5 minutes default
                 max_retries: int = 3,  # Maximum retry attempts
                 retry_delay: int = 60,  # Delay between retries (seconds)
                 progress_callback: Optional[Callable] = None,
                 status_callback: Optional[Callable] = None,
                 notification_callback: Optional[Callable] = None,
                 enable_pattern_monitoring: bool = True):
        """
        Initialize the auto-update scheduler

        Args:
            watchlist_manager: WatchlistManager instance
            check_interval: How often to check for updates (seconds)
            max_retries: Maximum number of retry attempts for failed updates
            retry_delay: Delay between retry attempts (seconds)
            progress_callback: Callback for progress updates (chart, percent, message)
            status_callback: Callback for status updates (message)
            notification_callback: Callback for notifications (title, message, type)
            enable_pattern_monitoring: Enable automated pattern detection and alerts
        """
        self.watchlist = watchlist_manager
        self.check_interval = check_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.notification_callback = notification_callback

        self.running = False
        self.paused = False
        self._thread = None
        self._stop_event = threading.Event()

        self.downloader = BinanceDataDownloader()
        self.history_logger = UpdateHistoryLogger()

        # Statistics
        self.last_check_time = None
        self.total_updates = 0
        self.failed_updates = 0

        # Retry tracking: {(symbol, timeframe): retry_count}
        self._retry_counts = {}

        # Pattern monitoring
        self.pattern_monitoring_enabled = enable_pattern_monitoring and PATTERN_MONITORING_AVAILABLE
        self.pattern_monitor = None

        # Thread pool for async pattern monitoring (max 2 concurrent detections)
        self._pattern_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="PatternMonitor")

        if self.pattern_monitoring_enabled:
            # Initialize pattern monitor with watchlist
            # ONLY monitor charts with monitor_alerts=True
            watchlist_items = [
                {'symbol': chart.symbol, 'timeframe': chart.timeframe}
                for chart in self.watchlist.get_all_charts()
                if chart.enabled and chart.monitor_alerts  # Must have both enabled AND monitor_alerts
            ]
            if watchlist_items:
                # initial_load=True means first scan won't send alerts
                self.pattern_monitor = MultiSymbolMonitor(
                    watchlist_items,
                    initial_load=True
                )
                print(f"✅ Pattern monitoring enabled for {len(watchlist_items)} charts (out of {len(self.watchlist.get_all_charts())} total)")
            else:
                print("⚠️ No charts selected for pattern monitoring (enable 'Monitor Alerts' checkbox)")
        else:
            print("ℹ️ Pattern monitoring disabled")

    def start(self):
        """Start the auto-update scheduler"""
        if self.running:
            print("Scheduler already running")
            return

        self.running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()
        print(f"Auto-update scheduler started (checking every {self.check_interval}s)")
        self._notify_status("Auto-update scheduler started")

    def stop(self):
        """Stop the auto-update scheduler"""
        if not self.running:
            return

        self.running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        # Shutdown pattern monitoring thread pool
        if hasattr(self, '_pattern_executor'):
            print("Shutting down pattern monitoring threads...")
            self._pattern_executor.shutdown(wait=False)

        print("Auto-update scheduler stopped")
        self._notify_status("Auto-update scheduler stopped")

    def pause(self):
        """Pause automatic updates"""
        self.paused = True
        print("Auto-update scheduler paused")
        self._notify_status("Auto-updates paused")

    def resume(self):
        """Resume automatic updates"""
        self.paused = False
        print("Auto-update scheduler resumed")
        self._notify_status("Auto-updates resumed")

    def update_now(self, symbol: str = None, timeframe: str = None):
        """
        Manually trigger update for specific chart or all charts

        Args:
            symbol: Symbol to update (None = all)
            timeframe: Timeframe to update (None = all)
        """
        if symbol and timeframe:
            # Update specific chart
            chart = self.watchlist.find_chart(symbol, timeframe)
            if chart and chart.enabled:
                self._update_chart(chart)
            else:
                print(f"Chart not found or disabled: {symbol} {timeframe}")
        else:
            # Update all enabled charts
            charts = [c for c in self.watchlist.get_all_charts() if c.enabled]
            self._notify_status(f"Manually updating {len(charts)} charts...")
            for chart in charts:
                self._update_chart(chart)
            self._notify_status(f"Manual update complete")

    def _update_loop(self):
        """Main update loop running in background thread"""
        while self.running and not self._stop_event.is_set():
            try:
                # Update last check time
                self.last_check_time = datetime.now()

                if not self.paused:
                    # Get charts that need updating
                    charts_to_update = self.watchlist.get_charts_needing_update()

                    if charts_to_update:
                        print(f"Found {len(charts_to_update)} charts needing update")
                        self._notify_status(f"Updating {len(charts_to_update)} charts...")

                        for chart in charts_to_update:
                            if not self.running:
                                break
                            self._update_chart(chart)

                        self._notify_status("Updates complete")
                    else:
                        print("No charts need updating")

            except Exception as e:
                print(f"Error in update loop: {e}")
                self._notify_status(f"Update error: {e}")

            # Wait for next check (or until stopped)
            self._stop_event.wait(timeout=self.check_interval)

    def _update_chart(self, chart: ChartEntry, retry_attempt: int = 0):
        """Update a single chart with retry logic"""
        chart_key = (chart.symbol, chart.timeframe)

        try:
            print(f"\nUpdating {chart.symbol} {chart.timeframe}...")
            self._notify_status(f"Updating {chart.symbol} {chart.timeframe}...")

            # Determine date range for update
            # Get last candle's date and fetch from there to now
            import pandas as pd

            # Check if file exists
            if not os.path.exists(chart.file_path):
                print(f"File not found: {chart.file_path}, downloading full history")
                start_date = datetime.now() - timedelta(days=365)  # 1 year back
            else:
                # Read existing file to get last date
                existing_df = pd.read_csv(chart.file_path)
                if 'time' in existing_df.columns:
                    last_date = pd.to_datetime(existing_df['time'].iloc[-1])
                else:
                    last_date = chart.last_update

                # Start from last date
                start_date = last_date

            end_date = datetime.now()

            # Download new data
            def progress_update(percent, message):
                if self.progress_callback:
                    self.progress_callback(chart, percent, message)

            # Handle custom timeframes that Binance doesn't support
            # Check if timeframe is valid Binance interval, if not, resample from lower timeframe
            download_interval, resample_rule = self._get_download_interval(chart.timeframe)

            if resample_rule:
                print(f"Note: {chart.timeframe} is not a Binance interval, downloading {download_interval} and resampling")

            new_df = self.downloader.download_data(
                symbol=chart.symbol,
                interval=download_interval,
                start_date=start_date,
                end_date=end_date,
                progress_callback=progress_update
            )

            # Resample if needed
            if resample_rule and new_df is not None and len(new_df) > 0:
                new_df = self._resample_data(new_df, resample_rule)
                print(f"Resampled to {chart.timeframe}: {len(new_df)} candles")

            if new_df is not None and len(new_df) > 0:
                # Append or overwrite
                if os.path.exists(chart.file_path):
                    # Load existing data
                    existing_df = pd.read_csv(chart.file_path)
                    existing_df['time'] = pd.to_datetime(existing_df['time'])

                    # Combine and remove duplicates
                    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['time'], keep='last')
                    combined_df = combined_df.sort_values('time')

                    # Save combined data
                    combined_df.to_csv(chart.file_path, index=False)
                    print(f"Appended {len(new_df)} new candles to {chart.file_path}")
                else:
                    # Save new data
                    new_df.to_csv(chart.file_path, index=False)
                    print(f"Saved {len(new_df)} candles to {chart.file_path}")

                # Mark as updated
                chart.mark_updated()
                self.watchlist.save()
                self.total_updates += 1

                # Log success
                self.history_logger.log_success(chart.symbol, chart.timeframe, len(new_df))

                # Clear retry count on success
                if chart_key in self._retry_counts:
                    del self._retry_counts[chart_key]

                self._notify_status(f"✓ Updated {chart.symbol} {chart.timeframe}")
                print(f"Successfully updated {chart.symbol} {chart.timeframe}")

                # TRIGGER PATTERN MONITORING after successful update
                self._run_pattern_monitoring(chart)

            else:
                print(f"No new data for {chart.symbol} {chart.timeframe}")
                # Still mark as updated to avoid repeated attempts
                chart.mark_updated()
                self.watchlist.save()

                # Log as success with 0 candles
                self.history_logger.log_success(chart.symbol, chart.timeframe, 0)

                # Clear retry count
                if chart_key in self._retry_counts:
                    del self._retry_counts[chart_key]

        except Exception as e:
            error_msg = str(e)
            print(f"Failed to update {chart.symbol} {chart.timeframe}: {error_msg}")
            self.failed_updates += 1

            # Track retry count
            current_retry = self._retry_counts.get(chart_key, 0)

            if current_retry < self.max_retries:
                # Schedule retry
                self._retry_counts[chart_key] = current_retry + 1
                next_retry = current_retry + 1

                # Log retry attempt
                self.history_logger.log_retry(chart.symbol, chart.timeframe, next_retry, error_msg)

                self._notify_status(f"⟳ Retrying {chart.symbol} {chart.timeframe} ({next_retry}/{self.max_retries})...")
                print(f"Will retry update for {chart.symbol} {chart.timeframe} (attempt {next_retry}/{self.max_retries})")

                # Wait and retry
                time.sleep(self.retry_delay)
                self._update_chart(chart, retry_attempt=next_retry)

            else:
                # Max retries exceeded
                self._retry_counts[chart_key] = 0  # Reset for next cycle

                # Log failure
                self.history_logger.log_failure(chart.symbol, chart.timeframe, error_msg, current_retry)

                # Send notification
                self._notify_failure(chart.symbol, chart.timeframe, error_msg)

                self._notify_status(f"✗ Failed to update {chart.symbol} {chart.timeframe} after {self.max_retries} retries")
                print(f"Gave up on {chart.symbol} {chart.timeframe} after {self.max_retries} retries")

    def _get_download_interval(self, timeframe):
        """
        Determine the download interval and resample rule for a given timeframe.

        Returns:
            tuple: (download_interval, resample_rule)
                - download_interval: Valid Binance interval to download
                - resample_rule: Pandas resample rule string (e.g., '2D', '5D') or None if no resampling needed
        """
        # Valid Binance intervals
        valid_intervals = {
            '1m', '3m', '5m', '15m', '30m',
            '1h', '2h', '4h', '6h', '8h', '12h',
            '1d', '3d', '1w', '1M'
        }

        # If it's already a valid interval, no resampling needed
        if timeframe in valid_intervals:
            return timeframe, None

        # Parse custom timeframe to determine base interval and multiplier
        import re
        match = re.match(r'^(\d+)([mhdwM])$', timeframe)

        if not match:
            # If format is not recognized, default to 1d
            print(f"Warning: Unrecognized timeframe format '{timeframe}', defaulting to 1d")
            return '1d', None

        multiplier = int(match.group(1))
        unit = match.group(2)

        # Map to download interval and resample rule
        if unit == 'm':  # Minutes
            if multiplier <= 1:
                return '1m', None
            elif multiplier <= 3:
                return '1m', f'{multiplier}min'
            elif multiplier <= 5:
                return '1m', f'{multiplier}min'
            elif multiplier <= 15:
                return '1m', f'{multiplier}min'
            elif multiplier <= 30:
                return '1m', f'{multiplier}min'
            else:
                return '1h', f'{multiplier}min'

        elif unit == 'h':  # Hours
            if multiplier <= 1:
                return '1h', None
            elif multiplier <= 2:
                return '1h', f'{multiplier}H'
            elif multiplier <= 4:
                return '1h', f'{multiplier}H'
            elif multiplier <= 6:
                return '1h', f'{multiplier}H'
            elif multiplier <= 8:
                return '1h', f'{multiplier}H'
            elif multiplier <= 12:
                return '1h', f'{multiplier}H'
            else:
                return '1d', f'{multiplier}H'

        elif unit == 'd':  # Days
            if multiplier == 1:
                return '1d', None
            elif multiplier <= 3:
                return '1d', f'{multiplier}D'
            else:
                return '1d', f'{multiplier}D'

        elif unit == 'w':  # Weeks
            if multiplier == 1:
                return '1w', None
            else:
                # Use 1w as base for weekly intervals (more efficient than 1d)
                return '1w', f'{multiplier}W'

        elif unit == 'M':  # Months
            if multiplier == 1:
                return '1M', None
            else:
                # Use 1M as base for monthly intervals (more efficient than 1d)
                return '1M', f'{multiplier}M'

        # Fallback
        return '1d', None

    def _resample_data(self, df, resample_rule):
        """
        Resample OHLCV data to a higher timeframe.

        Args:
            df: DataFrame with columns [time, open, high, low, close, volume]
            resample_rule: Pandas resample rule (e.g., '2D', '5H', '10min')

        Returns:
            Resampled DataFrame
        """
        import pandas as pd

        # Make sure time is datetime
        df['time'] = pd.to_datetime(df['time'])
        df = df.set_index('time')

        # Resample to specified period
        # For OHLC data: open=first, high=max, low=min, close=last, volume=sum
        resampled = df.resample(resample_rule).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }).dropna()

        # Reset index to get time back as a column
        resampled = resampled.reset_index()

        return resampled

    def _notify_status(self, message: str):
        """Send status update via callback"""
        if self.status_callback:
            try:
                self.status_callback(message)
            except Exception as e:
                print(f"Error in status callback: {e}")

    def _notify_failure(self, symbol: str, timeframe: str, error_msg: str):
        """Send failure notification via callback"""
        if self.notification_callback:
            try:
                title = f"Update Failed: {symbol} {timeframe}"
                message = f"Failed to update {symbol} {timeframe} after {self.max_retries} retries.\n\nError: {error_msg}"
                self.notification_callback(title, message, 'error')
            except Exception as e:
                print(f"Error in notification callback: {e}")

    def set_check_interval(self, interval: int):
        """
        Change the check interval (in seconds)

        Args:
            interval: New check interval in seconds (minimum 60)
        """
        if interval < 60:
            print("Check interval must be at least 60 seconds")
            return False

        self.check_interval = interval
        print(f"Check interval updated to {interval} seconds ({interval//60} minutes)")
        return True

    def set_retry_settings(self, max_retries: int, retry_delay: int):
        """
        Update retry settings

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        print(f"Retry settings updated: max_retries={max_retries}, retry_delay={retry_delay}s")

    def get_stats(self) -> dict:
        """Get scheduler statistics"""
        history_stats = self.history_logger.get_statistics()

        return {
            'running': self.running,
            'paused': self.paused,
            'last_check': self.last_check_time.isoformat() if self.last_check_time else None,
            'total_updates': self.total_updates,
            'failed_updates': self.failed_updates,
            'check_interval': self.check_interval,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay,
            'history_stats': history_stats
        }

    def get_update_history(self, limit: int = 50):
        """Get recent update history"""
        return self.history_logger.get_recent_records(limit)

    def get_failed_updates(self, limit: int = 50):
        """Get recent failed updates"""
        return self.history_logger.get_failed_records(limit)

    def get_chart_history(self, symbol: str, timeframe: str, limit: int = 20):
        """Get update history for specific chart"""
        return self.history_logger.get_records_by_symbol(symbol, timeframe, limit)

    def _run_pattern_monitoring(self, chart: ChartEntry):
        """
        Run pattern monitoring after data update (async in separate thread)

        Args:
            chart: ChartEntry that was just updated
        """
        if not self.pattern_monitoring_enabled or not self.pattern_monitor:
            return

        # Run pattern detection in a separate thread to avoid blocking
        def monitor_in_thread():
            try:
                import pandas as pd

                # Load updated data
                if not os.path.exists(chart.file_path):
                    print(f"⚠️ File not found for pattern monitoring: {chart.file_path}")
                    return

                # Read CSV
                df = pd.read_csv(chart.file_path)

                # Normalize column names to Title Case
                df.columns = [col.capitalize() for col in df.columns]

                # Set time index
                if 'Time' in df.columns:
                    df['Time'] = pd.to_datetime(df['Time'])
                    df.set_index('Time', inplace=True)
                elif 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    df.set_index('Date', inplace=True)

                print(f"\n🔍 Running pattern monitoring for {chart.symbol} {chart.timeframe}...")

                # Run pattern monitoring
                results = self.pattern_monitor.process_update(
                    symbol=chart.symbol,
                    timeframe=chart.timeframe,
                    data=df
                )

                # Log results
                if results.get('new_patterns_detected', 0) > 0:
                    print(f"🎯 {results['new_patterns_detected']} new patterns detected!")

                if results.get('patterns_entered', 0) > 0:
                    print(f"⚡ {results['patterns_entered']} patterns entered PRZ!")

                if results.get('alerts_sent', 0) > 0:
                    print(f"🔔 {results['alerts_sent']} alerts sent")

            except Exception as e:
                print(f"⚠️ Pattern monitoring error for {chart.symbol} {chart.timeframe}: {e}")
                import traceback
                traceback.print_exc()

        # Submit to thread pool (limited concurrency)
        self._pattern_executor.submit(monitor_in_thread)

    def enable_pattern_monitoring(self):
        """Enable pattern monitoring"""
        if not PATTERN_MONITORING_AVAILABLE:
            print("❌ Pattern monitoring not available (missing dependencies)")
            return False

        if not self.pattern_monitor:
            # Initialize pattern monitor
            # ONLY monitor charts with monitor_alerts=True
            watchlist_items = [
                {'symbol': chart.symbol, 'timeframe': chart.timeframe}
                for chart in self.watchlist.get_all_charts()
                if chart.enabled and chart.monitor_alerts
            ]
            if watchlist_items:
                self.pattern_monitor = MultiSymbolMonitor(watchlist_items)
                print(f"✅ Pattern monitoring enabled for {len(watchlist_items)} charts")
            else:
                print("⚠️ No charts selected for pattern monitoring (enable 'Monitor Alerts' checkbox)")
                return False

        self.pattern_monitoring_enabled = True
        print("✅ Pattern monitoring enabled")
        return True

    def disable_pattern_monitoring(self):
        """Disable pattern monitoring"""
        self.pattern_monitoring_enabled = False
        print("ℹ️ Pattern monitoring disabled")

    def rebuild_pattern_monitor(self):
        """Rebuild pattern monitor based on current watchlist settings"""
        if not PATTERN_MONITORING_AVAILABLE or not self.pattern_monitoring_enabled:
            return False

        # Get charts with monitor_alerts=True
        watchlist_items = [
            {'symbol': chart.symbol, 'timeframe': chart.timeframe}
            for chart in self.watchlist.get_all_charts()
            if chart.enabled and chart.monitor_alerts
        ]

        if watchlist_items:
            # Recreate pattern monitor with updated list
            self.pattern_monitor = MultiSymbolMonitor(
                watchlist_items,
                initial_load=False  # Don't suppress alerts on rebuild
            )
            print(f"✅ Pattern monitor rebuilt: {len(watchlist_items)} charts (out of {len(self.watchlist.get_all_charts())} total)")
            return True
        else:
            self.pattern_monitor = None
            print("⚠️ No charts selected for pattern monitoring")
            return False

    def get_active_signals(self):
        """Get all active trading signals from pattern monitor"""
        if not self.pattern_monitor:
            return []
        return self.pattern_monitor.get_all_active_signals()


# Import for file operations
import os
from datetime import timedelta
