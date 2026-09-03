from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from qozy.gui.components import NavButton
from qozy.gui.pages import (
    CountsPage,
    HeraldedG2Page,
    PolytopePage,
    SettingsPage,
    StateTomographyPage,
)
from qozy.gui.theme import apply_theme


class MainWindow(QMainWindow):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.mode = "light"

        icon_path = Path(__file__).resolve().parent / "icons" / "logo.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setWindowTitle("QOZY")
        self.resize(1180, 760)
        self.setMinimumSize(920, 600)

        root = QWidget()
        root.setObjectName("Root")
        main = QHBoxLayout(root)
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        main.addWidget(self.build_sidebar())

        self.pages = QStackedWidget()
        for page in (SettingsPage(), CountsPage(), PolytopePage(), HeraldedG2Page(), StateTomographyPage()):
            self.pages.addWidget(page)
        main.addWidget(self.pages, 1)

        self.setCentralWidget(root)
        self.select_page(0)

    def build_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 22, 16, 16)
        layout.setSpacing(8)

        brand = QLabel("QOZY")
        brand.setObjectName("Brand")
        layout.addWidget(brand)
        layout.addSpacing(20)

        self.buttons = []
        for i, text in enumerate(["Settings", "Counts", "Polytope", "Heralded g2", "State tomography"]):
            button = NavButton(text, i)
            button.clicked.connect(lambda checked=False, idx=i: self.select_page(idx))
            self.buttons.append(button)
            layout.addWidget(button)
        layout.addStretch()

        theme_button = QPushButton("Toggle dark mode")
        theme_button.setObjectName("Secondary")
        theme_button.clicked.connect(self.toggle_theme)
        layout.addWidget(theme_button)
        return sidebar

    def select_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for i, button in enumerate(self.buttons):
            button.set_active(i == index)

    def toggle_theme(self) -> None:
        self.mode = "dark" if self.mode == "light" else "light"
        apply_theme(self.app, self.mode)
        self.select_page(self.pages.currentIndex())
