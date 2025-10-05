"""
Auto-Update Scheduler
=====================
Background service that automatically updates charts based on their timeframes.
Enhanced with retry logic, configurable intervals, and update history tracking.
"""

import threading
import time
from datetime import datetime
from typing import Callable, Optional
from watchlist_manager import WatchlistManager, ChartEntry
from binance_downloader import BinanceDataDownloader
from update_history_logger import UpdateHistoryLogger


class AutoUpdateScheduler:
    """Background scheduler for automatic chart updates"""

    def __init__(self, watchlist_manager: WatchlistManager,
                 check_interval: int = 300,  # 5 minutes default
                 max_retries: int = 3,  # Maximum retry attempts
                 retry_delay: int = 60,  # Delay between retries (seconds)
                 progress_callback: Optional[Callable] = None,
                 status_callback: Optional[Callable] = None,
                 notification_callback: Optional[Callable] = None):
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

            new_df = self.downloader.download_data(
                symbol=chart.symbol,
                interval=chart.timeframe,
                start_date=start_date,
                end_date=end_date,
                progress_callback=progress_update
            )

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


# Import for file operations
import os
from datetime import timedelta
