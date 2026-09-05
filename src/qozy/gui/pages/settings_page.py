"""Application settings, including Time Tagger backend selection."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qozy.gui.components import Card
from qozy.gui.hardware_worker import HardwareWorker
from qozy.hardware.manager import BackendName, HardwareManager


class SettingsPage(QWidget):
    """Keep connection management in Settings without blocking the GUI."""

    adapter_ready = pyqtSignal(object)
    connection_changed = pyqtSignal(bool)

    _BACKENDS: tuple[tuple[str, BackendName], ...] = (
        ("Simulator", "simulator"),
        ("Time Tagger (local)", "timetagger-local"),
        ("Time Tagger (network)", "timetagger-network"),
    )

    def __init__(self, hardware: HardwareManager) -> None:
        super().__init__()
        self.hardware = hardware
        self._thread: QThread | None = None
        self._worker: HardwareWorker | None = None

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

        self.backend = QComboBox()
        for label, _name in self._BACKENDS:
            self.backend.addItem(label)
        self.backend.currentIndexChanged.connect(self._backend_changed)
        form.addRow("Acquisition backend", self.backend)

        self.network_address = QLineEdit(self.hardware.network_address)
        self.network_address.setPlaceholderText("host:41101")
        form.addRow("Network server", self.network_address)

        self.export_dir = QLineEdit("~/qozy_data")
        form.addRow("Export directory", self.export_dir)

        self.connect_button = QPushButton("Disconnect")
        self.connect_button.setObjectName("Primary")
        self.connect_button.clicked.connect(self._toggle_connection)
        form.addRow("", self.connect_button)

        self.status_label = QLabel("Simulator connected")
        self.status_label.setProperty("role", "muted")
        self.status_label.setWordWrap(True)
        form.addRow("Status", self.status_label)

        root.addWidget(card)
        root.addStretch()
        self._backend_changed(0)

    def set_busy(self, busy: bool) -> None:
        if busy:
            self.connect_button.setEnabled(False)
            self.backend.setEnabled(False)
            self.network_address.setEnabled(False)
        else:
            self.connect_button.setEnabled(self._thread is None)
            self.backend.setEnabled(not self.hardware.connected)
            self.network_address.setEnabled(
                not self.hardware.connected and self._selected_backend() == "timetagger-network"
            )

    def _selected_backend(self) -> BackendName:
        return self._BACKENDS[self.backend.currentIndex()][1]

    def _backend_changed(self, _index: int) -> None:
        is_network = self._selected_backend() == "timetagger-network"
        self.network_address.setEnabled(is_network and not self.hardware.connected)

    def _toggle_connection(self) -> None:
        if self._thread is not None:
            return
        if self.hardware.connected:
            self._start_hardware_worker("disconnect")
            return

        backend = self._selected_backend()
        address = self.network_address.text().strip()
        if backend == "timetagger-network" and not address:
            self.status_label.setText("Error: enter a network server address")
            return
        try:
            self.hardware.select(backend, address)
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Error: {exc}")
            return
        self._start_hardware_worker("connect")

    def _start_hardware_worker(self, action: str) -> None:
        self.connect_button.setEnabled(False)
        self.backend.setEnabled(False)
        self.network_address.setEnabled(False)
        self.status_label.setText("Connecting…" if action == "connect" else "Disconnecting…")

        self._thread = QThread()
        self._worker = HardwareWorker(self.hardware, action)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.connected.connect(self._on_connected)
        self._worker.disconnected.connect(self._on_disconnected)
        self._worker.error.connect(self._on_connection_error)
        self._worker.connected.connect(self._thread.quit)
        self._worker.disconnected.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._on_worker_finished)
        self._thread.start()

    def _on_connected(self, adapter: object) -> None:
        self.status_label.setText("Connected")
        self.connect_button.setText("Disconnect")
        self.adapter_ready.emit(adapter)
        self.connection_changed.emit(True)

    def _on_disconnected(self) -> None:
        self.status_label.setText("Disconnected")
        self.connect_button.setText("Connect")
        self.connection_changed.emit(False)

    def _on_connection_error(self, message: str) -> None:
        self.status_label.setText(f"Connection error: {message}")
        self.connect_button.setText("Connect")

    def _on_worker_finished(self) -> None:
        self._thread = None
        self._worker = None
        self.backend.setEnabled(not self.hardware.connected)
        self._backend_changed(self.backend.currentIndex())
        self.connect_button.setEnabled(True)
