#!/bin/env python
import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from app.window import MainWindow
from app.theme import apply_theme

app = QApplication(sys.argv)
app.setApplicationName("QOZY")
app.setApplicationDisplayName("QOZY")
app.setDesktopFileName("QOZY")

icon_path = Path(__file__) / "icons" / "logo.png"
icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
app.setWindowIcon(icon)

apply_theme(app, "light")
window = MainWindow(app)
window.setWindowTitle("QOZY")
window.setWindowIcon(icon)
window.show()
sys.exit(app.exec())
