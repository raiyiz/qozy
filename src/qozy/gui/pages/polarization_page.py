"""Alice/Bob polarization stage controls.

Split out of Settings into its own page so stage configuration and motion
controls have dedicated space, and so a real Bell scan's angle presets live
next to the controls that set them by hand.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread
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

from qozy.core.app_config import AppConfig, StageConfig
from qozy.core.bell_math import BELL_ANGLES_DEG
from qozy.gui.components import Card
from qozy.gui.hardware_worker import StageWorker
from qozy.hardware.manager import HardwareManager, StageBackendName, StageName

# Quick-set buttons for the angles a Bell scan actually uses, plus 0° as a
# neutral reference point, so lining a stage up by hand doesn't require
# typing and confirming a target angle every time.
_QUICK_ANGLES_DEG: tuple[float, ...] = (0.0, *BELL_ANGLES_DEG)


class PolarizationPage(QWidget):
    """Keep polarization-stage configuration and motion controls together."""

    _STAGE_BACKENDS: tuple[tuple[str, StageBackendName], ...] = (
        ("Simulator", "simulator"),
        ("Elliptec", "elliptec"),
    )

    def __init__(self, hardware: HardwareManager, initial: AppConfig | None = None) -> None:
        super().__init__()
        self.hardware = hardware
        self._initial = initial or AppConfig()
        self._stage_threads: dict[StageName, QThread] = {}
        self._stage_workers: dict[StageName, StageWorker] = {}
        self._stage_widgets: dict[StageName, dict[str, QWidget]] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("Polarization")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        subtitle = QLabel(
            "Configure and move the Alice and Bob polarization stages used by "
            "the Counts page's Bell scan."
        )
        subtitle.setProperty("role", "muted")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        stages_layout = QHBoxLayout()
        stages_layout.setSpacing(18)
        stages_layout.addWidget(
            self._create_stage_card("alice", "Alice", self._initial.alice_stage)
        )
        stages_layout.addWidget(self._create_stage_card("bob", "Bob", self._initial.bob_stage))
        root.addLayout(stages_layout)

        root.addStretch()

    def export_config(self, config: AppConfig) -> None:
        """Copy the current widget selections into ``config`` for saving."""
        config.alice_stage = self._stage_config("alice")
        config.bob_stage = self._stage_config("bob")

    def _stage_config(self, stage: StageName) -> StageConfig:
        widgets = self._stage_widgets[stage]
        assert isinstance(widgets["port"], QLineEdit)
        assert isinstance(widgets["address"], QLineEdit)
        return StageConfig(
            backend=self._selected_stage_backend(stage),
            port=widgets["port"].text().strip(),
            address=widgets["address"].text().strip() or "0",
        )

    def _create_stage_card(self, stage: StageName, title: str, initial: StageConfig) -> Card:
        card = Card()
        layout = QFormLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        layout.addRow(heading)

        backend = QComboBox()
        for label, _name in self._STAGE_BACKENDS:
            backend.addItem(label)
        backend_names = [name for _label, name in self._STAGE_BACKENDS]
        if initial.backend in backend_names:
            backend.setCurrentIndex(backend_names.index(initial.backend))
        backend.currentIndexChanged.connect(lambda _index, s=stage: self._stage_backend_changed(s))
        layout.addRow("Backend", backend)

        port = QLineEdit(initial.port or self.hardware.stage_ports[stage])
        port.setPlaceholderText("/dev/ttyUSB0 or COM4")
        layout.addRow("Serial port", port)

        address = QLineEdit(initial.address or self.hardware.stage_addresses[stage])
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

        presets_label = QLabel("Bell angles")
        presets_label.setProperty("role", "muted")
        layout.addRow(presets_label)

        presets = QHBoxLayout()
        presets.setSpacing(6)
        preset_buttons = []
        for deg in _QUICK_ANGLES_DEG:
            button = QPushButton(f"{deg:g}°")
            button.setObjectName("Secondary")
            button.clicked.connect(
                lambda _checked=False, s=stage, d=deg: self._move_stage_to(s, d)
            )
            presets.addWidget(button)
            preset_buttons.append(button)
        layout.addRow("", presets)

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
            "presets": preset_buttons,
        }
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
            if action in {"move", "home"}:
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
        for button in widgets["presets"]:
            button.setEnabled(not busy and connected)

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

    def _move_stage_to(self, stage: StageName, angle_deg: float) -> None:
        if stage in self._stage_threads or not self.hardware.stage_connected[stage]:
            return
        target = self._stage_widgets[stage]["target"]
        assert isinstance(target, QLineEdit)
        target.setText(f"{angle_deg:.2f}")
        self._start_stage_worker(stage, "move", angle_deg)

    def _home_stage(self, stage: StageName) -> None:
        if stage not in self._stage_threads and self.hardware.stage_connected[stage]:
            self._start_stage_worker(stage, "home")

    def _read_stage_angle(self, stage: StageName) -> None:
        if stage not in self._stage_threads and self.hardware.stage_connected[stage]:
            self._start_stage_worker(stage, "angle")

    def set_busy(self, busy: bool) -> None:
        """Freeze stage controls while acquisition is running (Bell scan
        needs exclusive control of both stages)."""
        for stage in ("alice", "bob"):
            self._set_stage_busy(stage, busy or stage in self._stage_threads)
