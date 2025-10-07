"""
Keyboard Shortcuts Module
Provides centralized keyboard shortcut management for the application

Features:
- Consistent shortcuts across all windows
- Easy customization
- Help dialog showing all shortcuts
- Context-aware shortcuts
"""

from PyQt6.QtGui import QShortcut, QKeySequence, QAction
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
from PyQt6.QtCore import Qt
from typing import Dict, Callable, Optional


class ShortcutManager:
    """
    Centralized keyboard shortcut management.

    Manages all keyboard shortcuts for the application with
    automatic registration and help system.
    """

    def __init__(self):
        self.shortcuts: Dict[str, Dict] = {}

    def register_shortcut(self, parent, key_sequence: str, callback: Callable,
                         description: str, category: str = "General"):
        """
        Register a keyboard shortcut.

        Args:
            parent: Parent widget for the shortcut
            key_sequence: Key sequence (e.g., "Ctrl+D")
            callback: Function to call when shortcut is triggered
            description: Human-readable description
            category: Category for grouping (e.g., "Navigation", "Detection")

        Returns:
            QShortcut instance
        """
        shortcut = QShortcut(QKeySequence(key_sequence), parent)
        shortcut.activated.connect(callback)

        # Store for help system
        shortcut_id = f"{category}:{key_sequence}"
        self.shortcuts[shortcut_id] = {
            'key': key_sequence,
            'description': description,
            'category': category,
            'callback': callback
        }

        return shortcut

    def get_shortcuts_by_category(self) -> Dict[str, list]:
        """
        Get all shortcuts organized by category.

        Returns:
            Dictionary mapping category to list of shortcuts
        """
        by_category = {}

        for shortcut_id, shortcut_info in self.shortcuts.items():
            category = shortcut_info['category']
            if category not in by_category:
                by_category[category] = []

            by_category[category].append({
                'key': shortcut_info['key'],
                'description': shortcut_info['description']
            })

        return by_category

    def show_help_dialog(self, parent=None):
        """Show dialog with all keyboard shortcuts"""
        dialog = ShortcutHelpDialog(self, parent)
        dialog.exec()


class ShortcutHelpDialog(QDialog):
    """Dialog displaying all keyboard shortcuts"""

    def __init__(self, manager: ShortcutManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(600, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Table for shortcuts
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Category", "Shortcut", "Action"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Populate table
        shortcuts_by_category = self.manager.get_shortcuts_by_category()
        row = 0

        for category in sorted(shortcuts_by_category.keys()):
            shortcuts = shortcuts_by_category[category]

            for shortcut in shortcuts:
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(category))
                table.setItem(row, 1, QTableWidgetItem(shortcut['key']))
                table.setItem(row, 2, QTableWidgetItem(shortcut['description']))
                row += 1

        layout.addWidget(table)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)


def setup_main_window_shortcuts(main_window, shortcut_manager: ShortcutManager):
    """
    Setup keyboard shortcuts for main window.

    Args:
        main_window: Main application window
        shortcut_manager: ShortcutManager instance
    """

    # Pattern Detection
    if hasattr(main_window, 'detect_patterns'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+D",
            main_window.detect_patterns,
            "Detect patterns",
            "Detection"
        )

    # Navigation
    if hasattr(main_window, 'next_pattern'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+Right",
            main_window.next_pattern,
            "Next pattern",
            "Navigation"
        )

    if hasattr(main_window, 'prev_pattern'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+Left",
            main_window.prev_pattern,
            "Previous pattern",
            "Navigation"
        )

    # Windows
    if hasattr(main_window, 'open_backtesting'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+B",
            main_window.open_backtesting,
            "Open backtesting window",
            "Windows"
        )

    if hasattr(main_window, 'show_active_signals_window'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+S",
            main_window.show_active_signals_window,
            "Open active signals window",
            "Windows"
        )

    if hasattr(main_window, 'open_watchlist_panel'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+W",
            main_window.open_watchlist_panel,
            "Open watchlist panel",
            "Windows"
        )

    # Chart Control
    if hasattr(main_window, 'zoom_in'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl++",
            main_window.zoom_in,
            "Zoom in",
            "Chart"
        )

    if hasattr(main_window, 'zoom_out'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+-",
            main_window.zoom_out,
            "Zoom out",
            "Chart"
        )

    if hasattr(main_window, 'reset_zoom'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+0",
            main_window.reset_zoom,
            "Reset zoom",
            "Chart"
        )

    # Data
    if hasattr(main_window, 'refresh_data'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+R",
            main_window.refresh_data,
            "Refresh data",
            "Data"
        )

    if hasattr(main_window, 'load_data'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+O",
            main_window.load_data,
            "Load data file",
            "Data"
        )

    # Application
    if hasattr(main_window, 'show_settings'):
        shortcut_manager.register_shortcut(
            main_window,
            "Ctrl+,",
            main_window.show_settings,
            "Open settings",
            "Application"
        )

    # Help
    shortcut_manager.register_shortcut(
        main_window,
        "F1",
        lambda: shortcut_manager.show_help_dialog(main_window),
        "Show keyboard shortcuts",
        "Help"
    )

    shortcut_manager.register_shortcut(
        main_window,
        "Ctrl+Q",
        main_window.close,
        "Quit application",
        "Application"
    )


# Default shortcuts configuration
DEFAULT_SHORTCUTS = {
    "Detection": {
        "Ctrl+D": "Detect patterns",
        "Ctrl+Shift+D": "Detect all pattern types",
    },
    "Navigation": {
        "Ctrl+Right": "Next pattern",
        "Ctrl+Left": "Previous pattern",
        "Ctrl+Home": "First pattern",
        "Ctrl+End": "Last pattern",
        "PgUp": "Previous page",
        "PgDown": "Next page",
    },
    "Windows": {
        "Ctrl+B": "Open backtesting",
        "Ctrl+S": "Open signals window",
        "Ctrl+W": "Open watchlist",
        "Ctrl+H": "Show history",
    },
    "Chart": {
        "Ctrl++": "Zoom in",
        "Ctrl+-": "Zoom out",
        "Ctrl+0": "Reset zoom",
        "Ctrl+F": "Fit to window",
    },
    "Data": {
        "Ctrl+R": "Refresh data",
        "Ctrl+O": "Load file",
        "Ctrl+E": "Export data",
    },
    "Application": {
        "Ctrl+,": "Settings",
        "F1": "Help",
        "Ctrl+Q": "Quit",
    }
}


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
    import sys

    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Keyboard Shortcuts Test")
            self.setGeometry(100, 100, 600, 400)

            label = QLabel("Press F1 to see keyboard shortcuts\nOr try Ctrl+D, Ctrl+B, etc.")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.setCentralWidget(label)

        def detect_patterns(self):
            print("Detecting patterns... (Ctrl+D)")

        def next_pattern(self):
            print("Next pattern (Ctrl+Right)")

        def prev_pattern(self):
            print("Previous pattern (Ctrl+Left)")

        def open_backtesting(self):
            print("Opening backtesting... (Ctrl+B)")

    app = QApplication(sys.argv)

    # Create shortcut manager
    manager = ShortcutManager()

    # Create window
    window = TestWindow()

    # Setup shortcuts
    setup_main_window_shortcuts(window, manager)

    window.show()

    print("✅ Keyboard shortcuts test window opened")
    print("Press F1 to see all shortcuts")

    sys.exit(app.exec())
