"""GUI package — PySide6 desktop toolbox."""

import sys
from typing import NoReturn


def launch_gui() -> NoReturn:
    """Launch the main application window (Qt event loop)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    from .main_app import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("ToolBox")
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


__all__ = ["launch_gui"]
