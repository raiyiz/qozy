"""Counts page and live acquisition UI."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PyQt6.QtCore import pyqtSignal
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

from qozy.core.app_config import AppConfig
from qozy.core.bell_math import POLARIZATION_LABELS
from qozy.core.controller import MeasurementController
from qozy.core.data_model import (
    ChannelConfig,
    MeasurementConfig,
    MeasurementState,
    TimeTaggerSettings,
)
from qozy.core.export import save_measurement
from qozy.core.scan_controller import BellScanController
from qozy.gui.components import Card
from qozy.gui.plot_panel import PlotPanel
from qozy.gui.scan_worker import make_scan_thread
from qozy.gui.worker import make_worker_thread
from qozy.hardware.base import MeasurementAdapter, PositionerAdapter
from qozy.hardware.manager import HardwareManager
from qozy.hardware.simulator import SimulatorStage


class CountsPage(QWidget):
    acquisition_changed = pyqtSignal(bool)

    def __init__(
        self,
        hardware: HardwareManager | None = None,
        controller: MeasurementController | None = None,
        initial: AppConfig | None = None,
    ) -> None:
        super().__init__()
        self.hardware = hardware
        self._initial = initial or AppConfig()
        if controller is not None:
            self.controller = controller
        elif hardware is not None:
            self.controller = MeasurementController(hardware.adapter, MeasurementConfig())
        else:
            raise ValueError("CountsPage requires a HardwareManager or MeasurementController")

        self._hardware_connected = hardware is None or hardware.connected
        self._fallback_alice_stage = SimulatorStage() if hardware is None else None
        self._fallback_bob_stage = SimulatorStage() if hardware is None else None
        self._thread = None
        self._worker = None
        self._scan_thread = None
        self._scan_worker = None
        self._export_dir = self._initial.export_dir
        self._last_scan_matrix: np.ndarray | None = None

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
        self.set_timetagger_settings(
            hardware.timetagger_settings if hardware is not None else TimeTaggerSettings()
        )
        self.set_hardware_connected(self._hardware_connected)

    def export_config(self, config: AppConfig) -> None:
        config.auto_save_scan = self.auto_save_checkbox.isChecked()

    def set_export_dir(self, path: str) -> None:
        self._export_dir = path.strip() or self._export_dir

    def set_adapter(self, adapter: MeasurementAdapter) -> None:
        if self._worker is not None:
            raise RuntimeError("Cannot replace the adapter during live acquisition")
        self.controller = MeasurementController(adapter, self.controller.config)
        self._prepare_controller_config()
        self.set_hardware_connected(True)
        self.status_label.setText("Backend connected; ready")

    def set_timetagger_settings(self, settings: TimeTaggerSettings) -> None:
        self.controller.adapter = (
            self.hardware.adapter if self.hardware is not None else self.controller.adapter
        )
        self.controller.config.alice_channels = [
            ChannelConfig(channel=ch) for ch in settings.alice_channels
        ]
        self.controller.config.bob_channels = [
            ChannelConfig(
                channel=ch,
                delay_ns=settings.channel_delay_map().get(ch, 0.0),
            )
            for ch in settings.bob_channels
        ]
        for item, channel_list in (
            (self.controller.config.alice_channels, settings.alice_channels),
            (self.controller.config.bob_channels, settings.bob_channels),
        ):
            for cfg, ch in zip(item, channel_list):
                cfg.delay_ns = settings.channel_delay_map().get(ch, 0.0)
        self.controller.config.counts_bin_width_ms = settings.counts_bin_width_ms
        self.controller.config.counts_time_frame_s = settings.counts_time_frame_s
        self.controller.config.coincidence_window_ns = settings.coincidence_window_ns
        self.controller.config.correlation_bin_width_ns = settings.correlation_bin_width_ns
        self.controller.config.correlation_time_frame_ns = settings.correlation_time_frame_ns
        self.controller._configured = True
        self.alice_edit.setText(", ".join(map(str, settings.alice_channels)))
        self.bob_edit.setText(", ".join(map(str, settings.bob_channels)))

    def set_hardware_connected(self, connected: bool) -> None:
        self._hardware_connected = connected
        idle = self._worker is None and self._scan_thread is None
        self.start_button.setEnabled(connected and idle)
        self.scan_button.setEnabled(connected and idle)
        if not connected and idle:
            self.status_label.setText("No acquisition backend connected")

    def _build_controls(self) -> QWidget:
        card = Card()
        card.setFixedWidth(280)
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)

        self.alice_edit = QLineEdit()
        self.alice_edit.setReadOnly(True)
        self.bob_edit = QLineEdit()
        self.bob_edit.setReadOnly(True)
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

        self.auto_save_checkbox = QCheckBox("Auto-save after scan")
        self.auto_save_checkbox.setChecked(self._initial.auto_save_scan)
        summary_col.addWidget(self.auto_save_checkbox)

        self.save_scan_button = QPushButton("Save scan")
        self.save_scan_button.setEnabled(False)
        self.save_scan_button.clicked.connect(self._save_scan_matrix)
        summary_col.addWidget(self.save_scan_button)
        summary_col.addStretch()
        row.addLayout(summary_col, 1)
        return card

    def _prepare_controller_config(self) -> None:
        if self.hardware is not None:
            settings = self.hardware.timetagger_settings
            errors = settings.validate()
            if errors:
                raise ValueError(" | ".join(errors))
            self.set_timetagger_settings(settings)
            return
        alice = [
            ChannelConfig(channel=int(v)) for v in self.alice_edit.text().split(",") if v.strip()
        ]
        bob = [ChannelConfig(channel=int(v)) for v in self.bob_edit.text().split(",") if v.strip()]
        if not alice or not bob:
            raise ValueError("At least one Alice channel and one Bob channel are required")
        self.controller.config.alice_channels = alice
        self.controller.config.bob_channels = bob

    def _start(self) -> None:
        if self._thread is not None or self._scan_thread is not None:
            return
        try:
            self._prepare_controller_config()
        except (ValueError, TypeError) as exc:
            self.status_label.setText(f"Settings error: {exc}")
            return

        self._thread, self._worker = make_worker_thread(self.controller, interval_ms=100)
        self._worker.data_ready.connect(self._on_data)
        self._worker.error.connect(self._on_error)
        self._worker.started.connect(self._on_started)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

        self.live_checkbox.setChecked(True)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.scan_button.setEnabled(False)
        self.status_label.setText("Starting acquisition…")
        self.acquisition_changed.emit(True)

    def _on_started(self) -> None:
        self.status_label.setText("Acquiring…")

    def _stop(self) -> None:
        if self._worker is not None:
            self.status_label.setText("Stopping…")
            self._worker.request_stop()
        else:
            self._set_stopped()

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._set_stopped()

    def _set_stopped(self) -> None:
        self.live_checkbox.setChecked(False)
        self.start_button.setEnabled(self._hardware_connected and self._scan_thread is None)
        self.stop_button.setEnabled(False)
        self.scan_button.setEnabled(self._hardware_connected and self._scan_thread is None)
        if not self.status_label.text().startswith("Error:"):
            self.status_label.setText("Stopped")
        self.acquisition_changed.emit(False)

    def _on_data(self, state: MeasurementState) -> None:
        counter = state.counter_data
        if counter is None or counter.shape[0] < 2:
            return
        t = counter[0]
        alice = counter[1]
        bob = counter[2] if counter.shape[0] > 2 else None
        corr = None
        if state.corr_data:
            corr_t, corr_v = state.corr_data[0]
            corr = np.interp(t, corr_t, corr_v) if len(corr_t) > 1 else None
        self.plot_panel.set_traces(t, alice, bob, corr)
        self.status_label.setText(f"Acquiring… last counter shape: {counter.shape}")

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Error: {message}")

    def _bell_scan_stages(self) -> tuple[PositionerAdapter, PositionerAdapter]:
        if self.hardware is not None:
            return self.hardware.stages["alice"], self.hardware.stages["bob"]
        assert self._fallback_alice_stage is not None
        assert self._fallback_bob_stage is not None
        return self._fallback_alice_stage, self._fallback_bob_stage

    def _run_bell_scan(self) -> None:
        if self._scan_thread is not None or self._worker is not None:
            return
        if self.hardware is not None and not (
            self.hardware.stage_connected["alice"] and self.hardware.stage_connected["bob"]
        ):
            self.status_label.setText(
                "Error: connect both polarization stages on the Polarization page before running a Bell scan"
            )
            return
        try:
            self._prepare_controller_config()
        except (ValueError, TypeError) as exc:
            self.status_label.setText(f"Settings error: {exc}")
            return

        alice = [c.channel for c in self.controller.config.alice_channels]
        bob = [c.channel for c in self.controller.config.bob_channels]
        alice_stage, bob_stage = self._bell_scan_stages()
        scan = BellScanController(
            self.controller.adapter,
            alice_stage,
            bob_stage,
            alice,
            bob,
            coincidence_window_ns=self.controller.config.coincidence_window_ns,
        )
        self._scan_thread, self._scan_worker = make_scan_thread(scan)
        self._scan_worker.cell_done.connect(self._on_scan_cell)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.error.connect(self._on_scan_error)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_worker.error.connect(self._scan_thread.quit)
        self._scan_thread.finished.connect(self._on_scan_thread_finished)
        self._scan_thread.start()

        self.scan_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.save_scan_button.setEnabled(False)
        self.status_label.setText("Running Bell scan…")
        self.acquisition_changed.emit(True)

    def _on_scan_cell(self, row: int, col: int, value: float) -> None:
        self.bell_table.setItem(row, col, QTableWidgetItem(f"{value:.0f}"))

    def _on_scan_finished(self, matrix: np.ndarray, e: np.ndarray, s: np.ndarray) -> None:
        self._last_scan_matrix = matrix
        e_text = ", ".join(f"{v:.2f}" for v in e)
        s_text = ", ".join(f"{v:.2f}" for v in s)
        max_s = max((abs(v) for v in s), default=0.0)
        self.bell_e_label.setText(f"E: {e_text}")
        self.bell_s_label.setText(f"S: {s_text}  (max |S| = {max_s:.2f})")
        if self.auto_save_checkbox.isChecked():
            self._save_scan_matrix(auto=True)
        else:
            self.status_label.setText("Scan complete")

    def _on_scan_error(self, message: str) -> None:
        self.status_label.setText(f"Scan error: {message}")

    def _on_scan_thread_finished(self) -> None:
        self._scan_thread = None
        self._scan_worker = None
        self.scan_button.setEnabled(self._hardware_connected)
        self.start_button.setEnabled(self._hardware_connected)
        self.save_scan_button.setEnabled(self._last_scan_matrix is not None)
        self.acquisition_changed.emit(False)

    def _save_scan_matrix(self, auto: bool = False) -> None:
        if self._last_scan_matrix is None:
            return
        try:
            path = save_measurement(
                self._last_scan_matrix,
                base_dir=Path(self._export_dir).expanduser(),
            )
        except (OSError, RuntimeError) as exc:
            prefix = "Scan complete — auto-save failed" if auto else "Save failed"
            self.status_label.setText(f"{prefix}: {exc}")
            return
        prefix = "Scan complete — saved to" if auto else "Saved to"
        self.status_label.setText(f"{prefix} {path}")
