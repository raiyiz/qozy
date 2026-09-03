import sys
from PyQt6.QtWidgets import QApplication
from app.window import MainWindow
from app.theme import apply_theme

app = QApplication(sys.argv)
app.setApplicationName("ModernApp")
apply_theme(app, "light")
window = MainWindow(app)
window.show()
sys.exit(app.exec())
