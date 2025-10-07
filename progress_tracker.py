"""
Progress Tracking System for Long Operations

Provides progress feedback during pattern detection and other long-running tasks.

Features:
- QProgressDialog integration
- Time remaining estimation
- Cancellation support
- Progress callbacks
- Console progress bars (for CLI)
"""

from PyQt6.QtWidgets import QProgressDialog, QApplication
from PyQt6.QtCore import Qt
from typing import Callable, Optional
import time


class ProgressTracker:
    """
    Track progress of long-running operations with UI feedback.

    Supports both GUI (QProgressDialog) and console (text) progress display.
    """

    def __init__(self, title: str = "Processing", message: str = "Please wait...",
                 total_steps: int = 100, show_gui: bool = True, parent=None):
        """
        Initialize progress tracker.

        Args:
            title: Dialog title
            message: Initial message
            total_steps: Total number of steps
            show_gui: Whether to show GUI dialog (False for console only)
            parent: Parent widget for dialog
        """
        self.title = title
        self.message = message
        self.total_steps = total_steps
        self.current_step = 0
        self.show_gui = show_gui
        self.parent = parent

        self.start_time = time.time()
        self.canceled = False

        # GUI progress dialog
        self.dialog = None
        if show_gui:
            self.dialog = QProgressDialog(message, "Cancel", 0, total_steps, parent)
            self.dialog.setWindowTitle(title)
            self.dialog.setWindowModality(Qt.WindowModality.WindowModal)
            self.dialog.setMinimumDuration(500)  # Show after 500ms
            self.dialog.canceled.connect(self._on_cancel)

    def update(self, step: Optional[int] = None, message: Optional[str] = None):
        """
        Update progress.

        Args:
            step: Current step number (if None, increments by 1)
            message: New message to display
        """
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1

        if message:
            self.message = message

        # Update GUI
        if self.dialog:
            self.dialog.setValue(self.current_step)
            if message:
                self.dialog.setLabelText(message)

            # Calculate time remaining
            elapsed = time.time() - self.start_time
            if self.current_step > 0:
                progress_pct = self.current_step / self.total_steps
                estimated_total = elapsed / progress_pct
                remaining = estimated_total - elapsed

                if remaining > 1:
                    time_msg = f"{message} ({int(remaining)}s remaining)" if message else f"{int(remaining)}s remaining"
                    self.dialog.setLabelText(time_msg)

            # Process events to keep UI responsive
            QApplication.processEvents()

        # Console output
        else:
            progress_pct = (self.current_step / self.total_steps) * 100
            elapsed = time.time() - self.start_time
            print(f"\r{self.message} [{progress_pct:.1f}%] {elapsed:.1f}s", end='', flush=True)

    def _on_cancel(self):
        """Handle cancellation"""
        self.canceled = True

    def is_canceled(self) -> bool:
        """Check if operation was canceled"""
        return self.canceled

    def finish(self, message: Optional[str] = None):
        """
        Complete progress tracking.

        Args:
            message: Final completion message
        """
        if self.dialog:
            self.dialog.setValue(self.total_steps)
            if message:
                self.dialog.setLabelText(message)
            self.dialog.close()
        else:
            if message:
                print(f"\r{message}")
            else:
                print()  # New line

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        if exc_type is None:
            self.finish("Complete")
        else:
            self.finish("Failed")
        return False


class ConsoleProgressBar:
    """Simple console progress bar (no Qt dependency)"""

    def __init__(self, total: int, prefix: str = "", width: int = 50):
        self.total = total
        self.prefix = prefix
        self.width = width
        self.current = 0
        self.start_time = time.time()

    def update(self, current: Optional[int] = None):
        """Update progress bar"""
        if current is not None:
            self.current = current
        else:
            self.current += 1

        filled = int(self.width * self.current / self.total)
        bar = '█' * filled + '-' * (self.width - filled)
        percent = 100 * self.current / self.total
        elapsed = time.time() - self.start_time

        print(f'\r{self.prefix} |{bar}| {percent:.1f}% {elapsed:.1f}s', end='', flush=True)

        if self.current >= self.total:
            print()  # New line when complete

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.current < self.total:
            self.update(self.total)
        return False


# Decorator for automatic progress tracking
def track_progress(title: str = "Processing", message: str = "Working..."):
    """
    Decorator to automatically track progress of a function.

    Args:
        title: Progress dialog title
        message: Initial message

    Example:
        @track_progress("Detecting Patterns", "Analyzing data...")
        def detect_patterns(data, progress_callback=None):
            for i in range(100):
                # Do work
                if progress_callback:
                    progress_callback(i, 100, f"Processing item {i}")
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Check if function accepts progress_callback parameter
            import inspect
            sig = inspect.signature(func)

            if 'progress_callback' in sig.parameters:
                # Create progress tracker
                with ProgressTracker(title, message, 100) as progress:
                    def callback(current, total, msg=None):
                        if progress.is_canceled():
                            raise InterruptedError("Operation canceled by user")
                        progress.update(int(current * 100 / total), msg)

                    kwargs['progress_callback'] = callback
                    return func(*args, **kwargs)
            else:
                # Function doesn't support progress callbacks
                return func(*args, **kwargs)

        return wrapper
    return decorator


if __name__ == "__main__":
    print("Testing Progress Tracking System...")
    print()

    # Test 1: Console progress bar
    print("Test 1: Console Progress Bar")
    with ConsoleProgressBar(50, prefix="Processing") as progress:
        for i in range(51):
            time.sleep(0.02)
            progress.update()

    print()

    # Test 2: Progress with messages
    print("\nTest 2: Progress with Messages")
    with ConsoleProgressBar(10, prefix="Loading data") as progress:
        for i in range(11):
            time.sleep(0.1)
            progress.update()

    # Test 3: Decorator
    print("\nTest 3: Progress Decorator")

    @track_progress("Test Operation", "Processing items...")
    def process_items(items, progress_callback=None):
        for i, item in enumerate(items):
            time.sleep(0.05)
            if progress_callback:
                progress_callback(i+1, len(items), f"Processing {item}")
        return "Done"

    result = process_items(['A', 'B', 'C', 'D', 'E'])
    print(f"Result: {result}")

    print("\n✅ Progress tracking system ready!")
