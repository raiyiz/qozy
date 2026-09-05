"""Counts page and live acquisition UI."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QMetaObject, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qozy.core.bell_math import POLARIZATION_LABELS
from qozy.core.controller import MeasurementController
from qozy.core.data_model import ChannelConfig, MeasurementConfig, MeasurementState
from qozy.core.scan_controller import BellScanController
from qozy.core.settings_store import TimeTaggerSettingsStore
from qozy.gui.components import Card
from qozy.gui.plot_panel import PlotPanel
from qozy.gui.scan_worker import make_scan_thread
from qozy.gui.worker import make_worker_thread
from qozy.hardware.base import MeasurementAdapter
from qozy.hardware.manager import HardwareManager
from qozy.hardware.simulator import SimulatorAdapter, SimulatorStage
from qozy.hardware.timetagger_adapter import TimeTaggerAdapter


def _parse_channels(text: str) -> list[ChannelConfig]:
    channels = []
    for part in text.split(","):
        part = part.strip()
        if part:
            channels.append(ChannelConfig(channel=int(part)))
    return channels


class CountsPage(QWidget):
    acquisition_changed = pyqtSignal(bool)

    def __init__(
        self,
        hardware: HardwareManager | None = None,
        controller: MeasurementController | None = None,
    ) -> None:
        super().__init__()
        self.hardware = hardware
        if controller is not None:
            self.controller = controller
        elif hardware is not None:
            self.controller = MeasurementController(hardware.adapter, MeasurementConfig())
        else:
            raise ValueError("CountsPage requires a HardwareManager or MeasurementController")

        self.alice_stage = SimulatorStage()
        self.bob_stage = SimulatorStage()
        self._thread = None
        self._worker = None
        self._scan_thread = None
        self._scan_worker = None
        self._settings_store = TimeTaggerSettingsStore()

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("Counts")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        body = QHBoxLayout()
        body.addWidget(self._build_controls(), 0)
        self.plot_panel = PlotPanel()
        body.addWidget(self.plot_panel, 1)
        root.addLayout(body)

        root.addWidget(self._build_bell_section())
        self._load_timetagger_defaults()

    def _load_timetagger_defaults(self) -> None:
        settings = self._settings_store.load()
        self.alice_edit.setText(", ".join(str(v) for v in settings.alice_channels))
        self.bob_edit.setText(", ".join(str(v) for v in settings.bob_channels))

    def _apply_runtime_settings(self) -> None:
        settings = self._settings_store.load()
        errors = settings.validate()
        if errors:
            raise ValueError(" | ".join(errors))

        if settings.backend_mode == "hardware":
            adapter = TimeTaggerAdapter()
        else:
            adapter = SimulatorAdapter()
        adapter.connect()

        delay_by_channel = settings.channel_delay_map()
        alice_channels = [
            ChannelConfig(channel=ch, delay_ns=delay_by_channel.get(ch, 0.0))
            for ch in settings.alice_channels
        ]
        bob_channels = [
            ChannelConfig(channel=ch, delay_ns=delay_by_channel.get(ch, 0.0))
            for ch in settings.bob_channels
        ]
        self.controller.adapter = adapter
        self.controller.config.alice_channels = alice_channels
        self.controller.config.bob_channels = bob_channels
        self.controller.config.counts_bin_width_ms = settings.counts_bin_width_ms
        self.controller.config.counts_time_frame_s = settings.counts_time_frame_s
        self.controller.config.coincidence_window_ns = settings.coincidence_window_ns
        self.controller.config.correlation_bin_width_ns = settings.correlation_bin_width_ns
        self.controller.config.correlation_time_frame_ns = settings.correlation_time_frame_ns
        self.controller._configured = False

    def set_adapter(self, adapter: MeasurementAdapter) -> None:
        """Switch to a newly connected acquisition backend."""
        if self._worker is not None:
            raise RuntimeError("Cannot replace the adapter during live acquisition")
        self.controller = MeasurementController(adapter, self.controller.config)
        self.status_label.setText("Backend connected; ready")

    def _build_controls(self) -> QWidget:
        card = Card()
        card.setFixedWidth(280)
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)

        self.alice_edit = QLineEdit("1, 2")
        self.bob_edit = QLineEdit("3, 4")
        form.addRow("Alice channels", self.alice_edit)
        form.addRow("Bob channels", self.bob_edit)

        self.live_checkbox = QCheckBox("Live acquisition")
        form.addRow("", self.live_checkbox)

        self.start_button = QPushButton("Start")
        self.start_button.setObjectName("Primary")
        self.start_button.clicked.connect(self._start)
        form.addRow("", self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop)
        form.addRow("", self.stop_button)

        self.status_label = QLabel("Idle")
        self.status_label.setProperty("role", "muted")
        self.status_label.setWordWrap(True)
        form.addRow("", self.status_label)

        return card

    def _build_bell_section(self) -> QWidget:
        card = Card()
        row = QHBoxLayout(card)
        row.setContentsMargins(20, 16, 20, 16)
        row.setSpacing(24)

        table_col = QVBoxLayout()
        label = QLabel("Coincidence matrix")
        label.setObjectName("SectionTitle")
        table_col.addWidget(label)

        self.bell_table = QTableWidget(4, 4)
        self.bell_table.setVerticalHeaderLabels(list(POLARIZATION_LABELS))
        self.bell_table.setHorizontalHeaderLabels(["22.5°", "67.5°", "112.5°", "157.5°"])
        self.bell_table.setFixedHeight(150)
        self.bell_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for r in range(4):
            for c in range(4):
                self.bell_table.setItem(r, c, QTableWidgetItem("—"))
        table_col.addWidget(self.bell_table)
        row.addLayout(table_col, 1)

        summary_col = QVBoxLayout()
        label2 = QLabel("Bell summary")
        label2.setObjectName("SectionTitle")
        summary_col.addWidget(label2)

        self.scan_button = QPushButton("Run Bell scan")
        self.scan_button.clicked.connect(self._run_bell_scan)
        summary_col.addWidget(self.scan_button)

        self.bell_e_label = QLabel("E: —")
        self.bell_s_label = QLabel("S: —")
        self.bell_s_label.setObjectName("MetricValue")
        summary_col.addWidget(self.bell_e_label)
        summary_col.addWidget(self.bell_s_label)
        summary_col.addStretch()
        row.addLayout(summary_col, 1)

        return card

    def _start(self) -> None:
        try:
            self._apply_runtime_settings()
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            self.status_label.setText(f"Settings error: {exc}")
            return

        delay_by_channel = {
            c.channel: c.delay_ns for c in self._settings_store.load().channel_settings if c.enabled
        }
        self.controller.config.alice_channels = [
            ChannelConfig(channel=c.channel, delay_ns=delay_by_channel.get(c.channel, 0.0))
            for c in _parse_channels(self.alice_edit.text())
        ]
        self.controller.config.bob_channels = [
            ChannelConfig(channel=c.channel, delay_ns=delay_by_channel.get(c.channel, 0.0))
            for c in _parse_channels(self.bob_edit.text())
        ]
        self.controller._configured = False
        self.controller.start()

        self.controller._configured = False
        self._thread, self._worker = make_worker_thread(self.controller, interval_ms=100)
        self._worker.data_ready.connect(self._on_data)
        self._worker.error.connect(self._on_error)
        self._worker.stopped.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

        self.live_checkbox.setChecked(True)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.scan_button.setEnabled(False)
        self.status_label.setText("Starting acquisition…")
        self.acquisition_changed.emit(True)

    def _stop(self) -> None:
        if self._worker is not None:
            QMetaObject.invokeMethod(self._worker, "stop", Qt.ConnectionType.QueuedConnection)
            if self._thread is not None:
                self._thread.wait()
        else:
            self._set_stopped()

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._set_stopped()

    def _set_stopped(self) -> None:
        self.live_checkbox.setChecked(False)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.scan_button.setEnabled(True)
        if not self.status_label.text().startswith("Error:"):
            self.status_label.setText("Stopped")
        self.acquisition_changed.emit(False)

    def _on_data(self, state: MeasurementState) -> None:
        counter = state.counter_data
        if counter is None or counter.shape[0] < 2:
            return
        t = counter[0]
        alice = counter[1] if counter.shape[0] > 1 else None
        bob = counter[2] if counter.shape[0] > 2 else None
        corr = None
        if state.corr_data:
            corr_t, corr_v = state.corr_data[0]
            corr = np.interp(t, corr_t, corr_v) if len(corr_t) > 1 else None
        self.plot_panel.set_traces(t, alice, bob, corr)
        self.status_label.setText(f"Acquiring… last counter row: {counter.shape}")

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Error: {message}")

    def _run_bell_scan(self) -> None:
        alice = [c.channel for c in _parse_channels(self.alice_edit.text())]
        bob = [c.channel for c in _parse_channels(self.bob_edit.text())]
        scan = BellScanController(self.controller.adapter, self.alice_stage, self.bob_stage, alice, bob)
        self._scan_thread, self._scan_worker = make_scan_thread(scan)
        self._scan_worker.cell_done.connect(self._on_scan_cell)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_thread.start()

        self.scan_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.status_label.setText("Running Bell scan…")

    def _on_scan_cell(self, row: int, col: int, value: float) -> None:
        self.bell_table.setItem(row, col, QTableWidgetItem(f"{value:.0f}"))

    def _on_scan_finished(self, matrix: np.ndarray, e: np.ndarray, s: np.ndarray) -> None:
        e_text = ", ".join(f"{v:.2f}" for v in e)
        s_text = ", ".join(f"{v:.2f}" for v in s)
        max_s = max(abs(v) for v in s)
        self.bell_e_label.setText(f"E: {e_text}")
        self.bell_s_label.setText(f"S: {s_text}  (max |S| = {max_s:.2f})")
        self.status_label.setText("Scan complete")
        self._finish_scan_thread()

    def _on_scan_error(self, message: str) -> None:
        self.status_label.setText(f"Scan error: {message}")
        self._finish_scan_thread()

    def _finish_scan_thread(self) -> None:
        if self._scan_thread is not None:
            self._scan_thread.quit()
            self._scan_thread.wait()
        self.scan_button.setEnabled(True)
        self.start_button.setEnabled(True)
