"""TODO: wire to real app settings (data export directory, TimeTagger vs
simulator backend, theme). Currently a placeholder carried over from the
modern_pyqt_starter template — see plan.md, this isn't in scope until the
core Counts/Bell flow (Phases 1-5) is done.
"""

from PyQt6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from qozy.gui.components import Card


class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
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

        backend = QComboBox()
        backend.addItems(["Simulator", "TimeTagger (hardware)"])
        export_dir = QLineEdit("~/qozy_data")
        notifications = QCheckBox("Enable desktop notifications")

        form.addRow("Acquisition backend", backend)
        form.addRow("Export directory", export_dir)
        form.addRow("", notifications)

        save = QPushButton("Save changes")
        save.setObjectName("Primary")
        form.addRow("", save)
        root.addWidget(card)
        root.addStretch()
