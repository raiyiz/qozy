"""Counts page and live Bell acquisition UI."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qozy.core.app_config import AppConfig
from qozy.core.bell_acquisition import (
    BellAcquisitionMode,
    BellAcquisitionOptions,
    BellChannelMap,
    BellMatrixAccumulator,
    SequentialBellAcquisition,
    SimultaneousBellAcquisition,
)
from qozy.core.bell_math import POLARIZATION_LABELS
from qozy.core.controller import MeasurementController
from qozy.core.data_model import (
    ChannelConfig,
    MeasurementConfig,
    MeasurementState,
    TimeTaggerSettings,
)
from qozy.core.export import save_measurement
from qozy.gui.bell_matrix_plot import BellMatrixPlot
from qozy.gui.components import Card
from qozy.gui.plot_panel import PlotPanel
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
        self._bell_acquisition = None
        self._bell_accumulator = BellMatrixAccumulator()
        self._last_scan_matrix: np.ndarray | None = None
        self._last_scan_e: np.ndarray | None = None
        self._last_scan_s: np.ndarray | None = None
        self._export_dir = self._initial.export_dir

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
        delay_map = settings.channel_delay_map()
        self.controller.config.alice_channels = [
            ChannelConfig(channel=ch, delay_ns=delay_map.get(ch, 0.0))
            for ch in settings.alice_channels
        ]
        self.controller.config.bob_channels = [
            ChannelConfig(channel=ch, delay_ns=delay_map.get(ch, 0.0))
            for ch in settings.bob_channels
        ]
        self.controller.config.counts_bin_width_ms = settings.counts_bin_width_ms
        self.controller.config.counts_time_frame_s = settings.counts_time_frame_s
        self.controller.config.coincidence_window_ns = settings.coincidence_window_ns
        self.controller.config.correlation_bin_width_ns = settings.correlation_bin_width_ns
        self.controller.config.correlation_time_frame_ns = settings.correlation_time_frame_ns
        self.controller._configured = False
        self.alice_edit.setText(", ".join(map(str, settings.alice_channels)))
        self.bob_edit.setText(", ".join(map(str, settings.bob_channels)))

    def set_hardware_connected(self, connected: bool) -> None:
        self._hardware_connected = connected
        idle = self._worker is None
        self.start_button.setEnabled(connected and idle)
        self.sequential_button.setEnabled(connected and idle)
        self.simultaneous_button.setEnabled(connected and idle)
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

        self.start_button = QPushButton("Start counts")
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
        self.coincidence_rate_label = QLabel("Coincidence rate: —")
        self.total_coincidences_label = QLabel("Total coincidences: —")
        self.coincidence_rate_label.setProperty("role", "muted")
        self.total_coincidences_label.setProperty("role", "muted")
        form.addRow("", self.coincidence_rate_label)
        form.addRow("", self.total_coincidences_label)
        return card

    def _build_bell_section(self) -> QWidget:
        card = Card()
        row = QHBoxLayout(card)
        row.setContentsMargins(20, 16, 20, 16)
        row.setSpacing(16)

        table_col = QVBoxLayout()
        label = QLabel("Coincidence matrix")
        label.setObjectName("SectionTitle")
        table_col.addWidget(label, 0, Qt.AlignmentFlag.AlignTop)
        self.bell_table = QTableWidget(4, 4)
        self.bell_table.setVerticalHeaderLabels(list(POLARIZATION_LABELS))
        self.bell_table.setHorizontalHeaderLabels(["22.5°", "67.5°", "112.5°", "157.5°"])
        self.bell_table.setFixedHeight(300)
        self.bell_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.bell_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._clear_bell_table()
        table_col.addWidget(self.bell_table, 0)
        self.bell_plot = BellMatrixPlot()
        table_col.addWidget(self.bell_plot)
        table_col.addStretch(1)
        row.addLayout(table_col, 1)

        summary_col = QVBoxLayout()
        label2 = QLabel("Bell acquisition")
        label2.setObjectName("SectionTitle")
        summary_col.addWidget(label2)
        self.sequential_radio = QRadioButton("Sequential scan")
        self.sequential_radio.setChecked(True)
        self.simultaneous_radio = QRadioButton("Simultaneous channels")
        summary_col.addWidget(self.sequential_radio)
        summary_col.addWidget(self.simultaneous_radio)
        self.sequential_button = QPushButton("Run sequential Bell scan")
        self.sequential_button.clicked.connect(self._run_sequential_bell)
        summary_col.addWidget(self.sequential_button)
        self.simultaneous_button = QPushButton("Start simultaneous Bell acquisition")
        self.simultaneous_button.clicked.connect(self._run_simultaneous_bell)
        summary_col.addWidget(self.simultaneous_button)
        self.normalize_bell_checkbox = QCheckBox("Normalize matrix display")
        self.normalize_bell_checkbox.setChecked(True)
        self.normalize_bell_checkbox.toggled.connect(self._render_bell)
        summary_col.addWidget(self.normalize_bell_checkbox)
        self.bell_e_label = QLabel("E: —, —, —, —")
        self.bell_s_label = QLabel("S: —, —, —, —")
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
        alice = [ChannelConfig(channel=int(v)) for v in self.alice_edit.text().split(",") if v.strip()]
        bob = [ChannelConfig(channel=int(v)) for v in self.bob_edit.text().split(",") if v.strip()]
        if not alice or not bob:
            raise ValueError("At least one Alice channel and one Bob channel are required")
        self.controller.config.alice_channels = alice
        self.controller.config.bob_channels = bob
        self.controller._configured = False

    def _start_worker(self, bell_acquisition=None, status: str = "Starting acquisition…") -> None:
        self._bell_acquisition = bell_acquisition
        self._bell_accumulator.reset()
        self._clear_bell_table()
        self._thread, self._worker = make_worker_thread(
            self.controller, interval_ms=100, bell_acquisition=bell_acquisition
        )
        self._worker.data_ready.connect(self._on_data)
        self._worker.bell_updated.connect(self._on_bell_updated)
        self._worker.error.connect(self._on_error)
        self._worker.started.connect(self._on_started)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()
        self.start_button.setEnabled(False)
        self.sequential_button.setEnabled(False)
        self.simultaneous_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.save_scan_button.setEnabled(False)
        self.status_label.setText(status)
        self.acquisition_changed.emit(True)

    def _start(self) -> None:
        if self._worker is not None:
            return
        try:
            self._prepare_controller_config()
        except (ValueError, TypeError) as exc:
            self.status_label.setText(f"Settings error: {exc}")
            return
        self._start_worker(status="Starting counts acquisition…")

    def _run_sequential_bell(self) -> None:
        if self._worker is not None:
            return
        if self.hardware is not None and not (
            self.hardware.stage_connected["alice"] and self.hardware.stage_connected["bob"]
        ):
            self.status_label.setText("Error: connect both polarization stages before a sequential Bell scan")
            return
        try:
            self._prepare_controller_config()
        except (ValueError, TypeError) as exc:
            self.status_label.setText(f"Settings error: {exc}")
            return
        alice = [c.channel for c in self.controller.config.alice_channels]
        bob = [c.channel for c in self.controller.config.bob_channels]
        alice_stage, bob_stage = self._bell_scan_stages()
        acquisition = SequentialBellAcquisition(
            self.controller.adapter,
            alice_stage,
            bob_stage,
            alice,
            bob,
            BellAcquisitionOptions(
                mode=BellAcquisitionMode.SEQUENTIAL,
                integration_time_s=0.5,
            ),
        )
        self._start_worker(acquisition, "Bell acquisition · Sequential")

    def _run_simultaneous_bell(self) -> None:
        if self._worker is not None:
            return
        try:
            self._prepare_controller_config()
        except (ValueError, TypeError) as exc:
            self.status_label.setText(f"Settings error: {exc}")
            return
        coincidence_count = len(self.controller.config.alice_channels) * len(self.controller.config.bob_channels)
        if coincidence_count == 0:
            self.status_label.setText("Error: no coincidence channels are configured")
            return
        offset = len(self.controller.config.alice_channels) + len(self.controller.config.bob_channels)
        acquisition = SimultaneousBellAcquisition(
            BellChannelMap.row_major(min(16, coincidence_count)),
            coincidence_offset=offset,
        )
        self._start_worker(acquisition, "Bell acquisition · Simultaneous channels")

    def _bell_scan_stages(self) -> tuple[PositionerAdapter, PositionerAdapter]:
        if self.hardware is not None:
            return self.hardware.stages["alice"], self.hardware.stages["bob"]
        assert self._fallback_alice_stage is not None
        assert self._fallback_bob_stage is not None
        return self._fallback_alice_stage, self._fallback_bob_stage

    def _on_started(self) -> None:
        if self._bell_acquisition is None:
            self.status_label.setText("Acquiring counts…")

    def _stop(self) -> None:
        if self._worker is not None:
            self.status_label.setText("Stopping…")
            self._worker.request_stop()
        else:
            self._set_stopped()

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        if self._bell_acquisition is not None:
            matrix = self._bell_accumulator.matrix.copy()
            if matrix.any():
                self._last_scan_matrix = matrix
                self._last_scan_e = self._bell_accumulator.e_values()
                self._last_scan_s = self._bell_accumulator.s_values()
                self.save_scan_button.setEnabled(True)
        self._bell_acquisition = None
        self._set_stopped()

    def _set_stopped(self) -> None:
        self.start_button.setEnabled(self._hardware_connected)
        self.sequential_button.setEnabled(self._hardware_connected)
        self.simultaneous_button.setEnabled(self._hardware_connected)
        self.stop_button.setEnabled(False)
        if not self.status_label.text().startswith("Error:") and not self.status_label.text().startswith("Scan complete"):
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
        self._update_coincidence_labels(state)
        if self._bell_acquisition is None:
            self.status_label.setText(f"Acquiring… last counter shape: {counter.shape}")

    def _update_coincidence_labels(self, state: MeasurementState) -> None:
        labels = state.countrate_labels
        rate = state.countrate_data
        total = state.total_counts_data
        if not labels or rate is None or total is None:
            return
        coincidence_idx = [i for i, label in enumerate(labels) if label.startswith("coin ")]
        if not coincidence_idx:
            return
        rate = np.asarray(rate)
        total = np.asarray(total)
        self.coincidence_rate_label.setText(
            f"Coincidence rate: {float(np.sum(rate[coincidence_idx])):,.0f} cps"
        )
        self.total_coincidences_label.setText(
            f"Total coincidences: {float(np.sum(total[coincidence_idx])):,.0f}"
        )

    def _on_bell_updated(self, update) -> None:
        self._bell_accumulator.update_matrix(update.matrix, update.filled)
        self._render_bell()
        if update.row is not None and update.col is not None and self._bell_acquisition is not None:
            if isinstance(self._bell_acquisition, SequentialBellAcquisition):
                elapsed = max(0.0, __import__("time").monotonic() - self._bell_acquisition._started_at)
                progress = self._bell_acquisition.completed_cells + 1
                self.status_label.setText(
                    f"Bell acquisition · Sequential · Alice {POLARIZATION_LABELS[update.row]} · "
                    f"Bob {POLARIZATION_LABELS[update.col]} · cell {progress}/16 · "
                    f"{min(elapsed, self._bell_acquisition.options.integration_time_s):.1f}/"
                    f"{self._bell_acquisition.options.integration_time_s:.1f} s"
                )
        if update.done:
            self.status_label.setText("Scan complete")

    def _render_bell(self, *_args) -> None:
        if not self._bell_accumulator.filled.any():
            self._clear_bell_table()
            self.bell_plot.clear()
            self.bell_e_label.setText("E: —, —, —, —")
            self.bell_s_label.setText("S: —, —, —, —")
            return
        matrix = self._bell_accumulator.normalized_matrix() if self.normalize_bell_checkbox.isChecked() else self._bell_accumulator.matrix.copy()
        for row in range(4):
            for col in range(4):
                if self._bell_accumulator.filled[row, col]:
                    self.bell_table.setItem(row, col, QTableWidgetItem(f"{matrix[row, col]:.2f}" if self.normalize_bell_checkbox.isChecked() else f"{matrix[row, col]:.0f}"))
                else:
                    self.bell_table.setItem(row, col, QTableWidgetItem("—"))
        self.bell_plot.update_matrix(matrix, filled=self._bell_accumulator.filled)
        e = self._bell_accumulator.e_values()
        s = self._bell_accumulator.s_values()
        ready = self._bell_accumulator.e_readiness()
        e_text = ", ".join(f"{v:.2f}" if ok else "—" for v, ok in zip(e, ready, strict=True))
        self.bell_e_label.setText(f"E: {e_text}")
        self.bell_s_label.setText(
            "S: " + (", ".join(f"{v:.2f}" for v in s) if ready.all() else "—, —, —, —")
        )

    def _clear_bell_table(self) -> None:
        for row in range(4):
            for col in range(4):
                self.bell_table.setItem(row, col, QTableWidgetItem("—"))

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Error: {message}")

    def _save_scan_matrix(self, auto: bool = False) -> None:
        if self._last_scan_matrix is None:
            return
        try:
            path = save_measurement(
                self._last_scan_matrix,
                base_dir=Path(self._export_dir).expanduser(),
            )
            svg_note = ""
            if self._last_scan_e is not None and self._last_scan_s is not None:
                svg_path = path.with_name(f"{path.stem}_quick_analysis.svg")
                self.bell_plot.save_svg(svg_path)
                svg_note = " (+ quick-analysis SVG)"
        except (OSError, RuntimeError) as exc:
            prefix = "Scan complete — auto-save failed" if auto else "Save failed"
            self.status_label.setText(f"{prefix}: {exc}")
            return
        prefix = "Scan complete — saved to" if auto else "Saved to"
        self.status_label.setText(f"{prefix} {path}{svg_note}")
