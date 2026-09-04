"""Application settings and hardware connection controls."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qozy.gui.components import Card
from qozy.gui.hardware_worker import HardwareWorker, StageWorker
from qozy.hardware.manager import BackendName, HardwareManager, StageBackendName, StageName


class SettingsPage(QWidget):
    """Keep connection management in Settings without blocking the GUI."""

    adapter_ready = pyqtSignal(object)
    connection_changed = pyqtSignal(bool)

    _BACKENDS: tuple[tuple[str, BackendName], ...] = (
        ("Simulator", "simulator"),
        ("Time Tagger (local)", "timetagger-local"),
        ("Time Tagger (network)", "timetagger-network"),
    )
    _STAGE_BACKENDS: tuple[tuple[str, StageBackendName], ...] = (
        ("Simulator", "simulator"),
        ("Elliptec", "elliptec"),
    )

    def __init__(self, hardware: HardwareManager) -> None:
        super().__init__()
        self.hardware = hardware
        self._thread: QThread | None = None
        self._worker: HardwareWorker | None = None
        self._stage_threads: dict[StageName, QThread] = {}
        self._stage_workers: dict[StageName, StageWorker] = {}
        self._stage_widgets: dict[StageName, dict[str, QWidget]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        acquisition_card = Card()
        form = QFormLayout(acquisition_card)
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

        root.addWidget(acquisition_card)

        stages_title = QLabel("Polarization stages")
        stages_title.setObjectName("SectionTitle")
        root.addWidget(stages_title)

        stages_layout = QHBoxLayout()
        stages_layout.setSpacing(18)
        stages_layout.addWidget(self._create_stage_card("alice", "Alice"))
        stages_layout.addWidget(self._create_stage_card("bob", "Bob"))
        root.addLayout(stages_layout)

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
        for stage in ("alice", "bob"):
            self._set_stage_busy(stage, stage in self._stage_threads or busy)

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

    def _create_stage_card(self, stage: StageName, title: str) -> Card:
        card = Card()
        layout = QFormLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        backend = QComboBox()
        for label, _name in self._STAGE_BACKENDS:
            backend.addItem(label)
        backend.currentIndexChanged.connect(lambda _index, s=stage: self._stage_backend_changed(s))
        layout.addRow("Backend", backend)

        port = QLineEdit(self.hardware.stage_ports[stage])
        port.setPlaceholderText("/dev/ttyUSB0 or COM4")
        layout.addRow("Serial port", port)

        address = QLineEdit(self.hardware.stage_addresses[stage])
        address.setPlaceholderText("0")
        layout.addRow("Device address", address)

        status = QLabel("Connected")
        status.setProperty("role", "muted")
        layout.addRow("Status", status)

        angle = QLabel("0.00°")
        layout.addRow("Position", angle)

        target = QLineEdit("0.00")
        target.setPlaceholderText("angle in degrees")
        layout.addRow("Target angle", target)

        controls = QHBoxLayout()
        connect = QPushButton("Disconnect")
        connect.setObjectName("Primary")
        connect.clicked.connect(lambda _checked=False, s=stage: self._toggle_stage_connection(s))
        controls.addWidget(connect)

        move = QPushButton("Move")
        move.clicked.connect(lambda _checked=False, s=stage: self._move_stage(s))
        controls.addWidget(move)

        home = QPushButton("Home")
        home.clicked.connect(lambda _checked=False, s=stage: self._home_stage(s))
        controls.addWidget(home)
        layout.addRow("", controls)

        refresh = QPushButton("Refresh position")
        refresh.clicked.connect(lambda _checked=False, s=stage: self._read_stage_angle(s))
        layout.addRow("", refresh)

        self._stage_widgets[stage] = {
            "backend": backend,
            "port": port,
            "address": address,
            "status": status,
            "angle": angle,
            "target": target,
            "connect": connect,
            "move": move,
            "home": home,
            "refresh": refresh,
        }
        card.setProperty("stageTitle", title)
        self._stage_backend_changed(stage)
        return card

    def _selected_stage_backend(self, stage: StageName) -> StageBackendName:
        backend = self._stage_widgets[stage]["backend"]
        assert isinstance(backend, QComboBox)
        return self._STAGE_BACKENDS[backend.currentIndex()][1]

    def _stage_backend_changed(self, stage: StageName) -> None:
        widgets = self._stage_widgets[stage]
        connected = self.hardware.stage_connected[stage]
        is_elliptec = self._selected_stage_backend(stage) == "elliptec"
        assert isinstance(widgets["port"], QLineEdit)
        assert isinstance(widgets["address"], QLineEdit)
        widgets["port"].setEnabled(is_elliptec and not connected)
        widgets["address"].setEnabled(is_elliptec and not connected)

    def _toggle_stage_connection(self, stage: StageName) -> None:
        if stage in self._stage_threads:
            return
        if self.hardware.stage_connected[stage]:
            self._start_stage_worker(stage, "disconnect")
            return

        widgets = self._stage_widgets[stage]
        backend = self._selected_stage_backend(stage)
        assert isinstance(widgets["port"], QLineEdit)
        assert isinstance(widgets["address"], QLineEdit)
        port = widgets["port"].text().strip()
        address = widgets["address"].text().strip() or "0"
        if backend == "elliptec" and not port:
            widgets["status"].setText("Error: enter a serial port")
            return
        try:
            self.hardware.select_stage(stage, backend, port, address)
        except Exception as exc:  # noqa: BLE001
            widgets["status"].setText(f"Error: {exc}")
            return
        self._start_stage_worker(stage, "connect")

    def _start_stage_worker(
        self,
        stage: StageName,
        action: str,
        angle_deg: float | None = None,
    ) -> None:
        widgets = self._stage_widgets[stage]
        widgets["status"].setText(
            {
                "connect": "Connecting…",
                "disconnect": "Disconnecting…",
                "move": "Moving…",
                "home": "Homing…",
                "angle": "Reading…",
            }[action]
        )
        self._set_stage_busy(stage, True)

        thread = QThread()
        worker = StageWorker(self.hardware, stage, action, angle_deg)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.result.connect(lambda value, s=stage, a=action: self._on_stage_result(s, a, value))
        worker.error.connect(lambda message, s=stage: self._on_stage_error(s, message))
        worker.result.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(lambda s=stage: self._on_stage_worker_finished(s))
        self._stage_threads[stage] = thread
        self._stage_workers[stage] = worker
        thread.start()

    def _on_stage_result(self, stage: StageName, action: str, value: object) -> None:
        widgets = self._stage_widgets[stage]
        if action == "connect":
            widgets["status"].setText("Connected")
            widgets["connect"].setText("Disconnect")
        elif action == "disconnect":
            widgets["status"].setText("Disconnected")
            widgets["connect"].setText("Connect")
        elif action in {"move", "home", "angle"}:
            assert isinstance(value, (float, int))
            assert isinstance(widgets["angle"], QLabel)
            widgets["angle"].setText(f"{float(value):.2f}°")
            if action == "move":
                widgets["status"].setText("Connected")
            elif action == "home":
                widgets["status"].setText("Connected")

    def _on_stage_error(self, stage: StageName, message: str) -> None:
        self._stage_widgets[stage]["status"].setText(f"Error: {message}")

    def _on_stage_worker_finished(self, stage: StageName) -> None:
        self._stage_threads.pop(stage, None)
        self._stage_workers.pop(stage, None)
        self._set_stage_busy(stage, False)
        self._stage_backend_changed(stage)

    def _set_stage_busy(self, stage: StageName, busy: bool) -> None:
        widgets = self._stage_widgets[stage]
        connected = self.hardware.stage_connected[stage]
        widgets["connect"].setEnabled(not busy)
        widgets["backend"].setEnabled(not busy and not connected)
        widgets["port"].setEnabled(
            not busy and not connected and self._selected_stage_backend(stage) == "elliptec"
        )
        widgets["address"].setEnabled(
            not busy and not connected and self._selected_stage_backend(stage) == "elliptec"
        )
        for key in ("target", "move", "home", "refresh"):
            widgets[key].setEnabled(not busy and connected)

    def _move_stage(self, stage: StageName) -> None:
        if stage in self._stage_threads:
            return
        target = self._stage_widgets[stage]["target"]
        assert isinstance(target, QLineEdit)
        try:
            angle_deg = float(target.text().strip())
        except ValueError:
            self._stage_widgets[stage]["status"].setText("Error: enter a numeric angle")
            return
        self._start_stage_worker(stage, "move", angle_deg)

    def _home_stage(self, stage: StageName) -> None:
        if stage not in self._stage_threads and self.hardware.stage_connected[stage]:
            self._start_stage_worker(stage, "home")

    def _read_stage_angle(self, stage: StageName) -> None:
        if stage not in self._stage_threads and self.hardware.stage_connected[stage]:
            self._start_stage_worker(stage, "angle")
