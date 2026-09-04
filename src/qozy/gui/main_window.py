from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from qozy.gui.components import NavButton
from qozy.gui.pages import (
    CountsPage,
    HeraldedG2Page,
    PolytopePage,
    SettingsPage,
    StateTomographyPage,
    TimeTaggerSettingsPage,
from qozy.gui.pages import CountsPage, HeraldedG2Page, PolytopePage, SettingsPage, StateTomographyPage
)
from qozy.gui.theme import THEME_ORDER, THEMES, apply_theme
from qozy.hardware.manager import HardwareManager


class MainWindow(QMainWindow):
    def __init__(self, app) -> None:
        super().__init__()
        self.app = app
        self.theme_modes = THEME_ORDER
        self.theme_index = 0
        self.mode = self.theme_modes[self.theme_index]
        self.hardware = HardwareManager()

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
        for page in (
            SettingsPage(),
            TimeTaggerSettingsPage(),
            CountsPage(),
            PolytopePage(),
            HeraldedG2Page(),
            StateTomographyPage(),
        ):
            self.settings_page = SettingsPage(self.hardware)
            self.counts_page = CountsPage(hardware=self.hardware)
            self.pages.addWidget(self.settings_page)
            self.pages.addWidget(self.counts_page)
        for page in (PolytopePage(), HeraldedG2Page(), StateTomographyPage()):
            self.pages.addWidget(page)
        main.addWidget(self.pages, 1)

        self.settings_page.adapter_ready.connect(self.counts_page.set_adapter)
        self.settings_page.connection_changed.connect(self.counts_page.set_hardware_connected)
        self.counts_page.acquisition_changed.connect(self.settings_page.set_busy)

        self.setCentralWidget(root)
        apply_theme(self.app, self.mode)
        self.select_page(0)
        self._update_theme_button()

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
        for i, text in enumerate(
            [
                "Settings",
                "TimeTagger Settings",
                "Counts",
                "Polytope",
                "Heralded g2",
                "State tomography",
            ]
        ):
            button = NavButton(text, i)
            button.clicked.connect(lambda checked=False, idx=i: self.select_page(idx))
            self.buttons.append(button)
            layout.addWidget(button)
        layout.addStretch()

        self.theme_button = QPushButton()
        self.theme_button.setObjectName("Secondary")
        self.theme_button.setToolTip("Cycle through the four QOZY themes")
        self.theme_button.clicked.connect(self.cycle_theme)
        layout.addWidget(self.theme_button)
        return sidebar

    def select_page(self, index: int) -> None:
        self.pages.setCurrentIndex(index)
        for i, button in enumerate(self.buttons):
            button.set_active(i == index)

    def cycle_theme(self) -> None:
        self.theme_index = (self.theme_index + 1) % len(self.theme_modes)
        self.mode = self.theme_modes[self.theme_index]
        apply_theme(self.app, self.mode)
        self.select_page(self.pages.currentIndex())
        self._update_theme_button()

    def _update_theme_button(self) -> None:
        label, _colors = THEMES[self.mode]
        next_index = (self.theme_index + 1) % len(self.theme_modes)
        next_label, _ = THEMES[self.theme_modes[next_index]]
        self.theme_button.setText(f"{label}  →  {next_label}")
