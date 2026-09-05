"""General application settings."""

from __future__ import annotations

from PyQt6.QtWidgets import QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from qozy.core.app_config import AppConfig
from qozy.gui.components import Card


class SettingsPage(QWidget):
    """Application-level settings that are not Time Tagger or polarization hardware."""

    def __init__(self, initial: AppConfig | None = None) -> None:
        super().__init__()
        initial = initial or AppConfig()

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(16)

        self.export_dir = QLineEdit(initial.export_dir)
        self.export_dir.setPlaceholderText("~/qozy_data")
        form.addRow("Export directory", self.export_dir)

        note = QLabel(
            "Time Tagger connection, detector channels, timing, trigger levels, "
            "and acquisition parameters are configured on the Time Tagger Settings page."
        )
        note.setWordWrap(True)
        note.setProperty("role", "muted")
        form.addRow("Hardware", note)

        root.addWidget(card)
        root.addStretch()

    def export_config(self, config: AppConfig) -> None:
        config.export_dir = self.export_dir.text().strip() or config.export_dir

    def set_busy(self, busy: bool) -> None:
        self.export_dir.setEnabled(not busy)
