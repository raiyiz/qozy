"""Counts page and live acquisition UI."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qozy.core.app_config import AppConfig
from qozy.core.bell_math import POLARIZATION_LABELS, calc_e_s, e_readiness
from qozy.core.controller import MeasurementController
from qozy.core.data_model import (
    ChannelConfig,
    MeasurementConfig,
    MeasurementState,
    TimeTaggerSettings,
)
from qozy.core.export import save_measurement
from qozy.core.scan_controller import BellScanController
from qozy.gui.bell_history_plot import BellHistoryPlot
from qozy.gui.bell_matrix_plot import BellMatrixPlot
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
        self._last_scan_e: np.ndarray | None = None
        self._last_scan_s: np.ndarray | None = None
        self._scan_matrix = np.zeros((4, 4))
        self._scan_filled = np.zeros((4, 4), dtype=bool)
        self._live_matrix = np.zeros((4, 4))
        self._live_filled_mask = np.zeros((4, 4), dtype=bool)
        self._scan_integration_time_s = 1.0
        self._live_scan_running = False
        self._scan_cycle_count = 0
        self._s_history: list[float] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        root = QVBoxLayout(content)
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
        # The settings describe desired configuration, not a proof that the
        # current adapter instance has been configured. The acquisition worker
        # must configure its adapter on its own thread before polling.
        self.controller._configured = False
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
        # Fixed height for up to 3 wrapped lines: the live-loop status
        # text ("Live — cycle N complete (max |S| = X.XX), starting
        # next…") changes length every cycle and, without this, would
        # wrap onto a different number of lines depending on how many
        # digits happened to be in N or the S value -- shrinking or
        # growing this whole card's height, and with it the vertical
        # position of everything below it, several times a second.
        self.status_label.setFixedHeight(3 * self.status_label.fontMetrics().lineSpacing() + 4)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
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
        table_col.setContentsMargins(0, 0, 0, 0)
        table_col.setSpacing(4)

        label = QLabel("Coincidence matrix")
        label.setObjectName("SectionTitle")
        table_col.addWidget(label, 0, Qt.AlignmentFlag.AlignTop)

        self.bell_table = QTableWidget(4, 4)
        self.bell_table.setVerticalHeaderLabels(list(POLARIZATION_LABELS))
        self.bell_table.setHorizontalHeaderLabels(["22.5°", "67.5°", "112.5°", "157.5°"])
        self.bell_table.setFixedHeight(300)
        self.bell_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.bell_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Fixed column widths: accumulated live-loop counts grow to more
        # digits over time, and without this the column would keep
        # widening to fit them, reflowing everything beside it.
        self.bell_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for col in range(4):
            self.bell_table.setColumnWidth(col, 90)

        for r in range(4):
            for c in range(4):
                self.bell_table.setItem(r, c, QTableWidgetItem("—"))

        table_col.addWidget(self.bell_table, 0)

        self.bell_plot = BellMatrixPlot()
        table_col.addWidget(self.bell_plot)

        # Keep title + table + heatmap together at the top instead of the
        # heatmap drifting away from the table it illustrates — the stretch
        # belongs after everything in this column, not between two widgets
        # meant to be read together.
        table_col.addStretch(1)

        row.addLayout(table_col, 1)

        summary_col = QVBoxLayout()
        label2 = QLabel("Bell summary")
        label2.setObjectName("SectionTitle")
        summary_col.addWidget(label2)
        self.scan_button = QPushButton("Run Bell scan")
        self.scan_button.clicked.connect(self._run_bell_scan)
        summary_col.addWidget(self.scan_button)

        self.live_scan_checkbox = QCheckBox("Loop continuously (live)")
        self.live_scan_checkbox.setToolTip(
            "Keep re-running the 16-setting scan back to back after each "
            "cycle finishes, showing count rate (not raw counts) so the "
            "matrix stays comparable cycle to cycle. Uncheck to let the "
            "current cycle finish and stop looping."
        )
        summary_col.addWidget(self.live_scan_checkbox)

        self.bell_e_label = QLabel("E: —, —, —, —")
        self.bell_s_label = QLabel("S: —, —, —, —")
        self.bell_s_label.setObjectName("MetricValue")
        # Fixed minimum width sized for the longest realistic text (four
        # signed 2-decimal values plus the "(max |S| = X.XX)" suffix) so
        # going from placeholder dashes to real numbers doesn't change
        # this column's preferred width and shove the heatmap column
        # beside it back and forth.
        self.bell_e_label.setMinimumWidth(320)
        self.bell_s_label.setMinimumWidth(320)
        summary_col.addWidget(self.bell_e_label)
        summary_col.addWidget(self.bell_s_label)

        self.auto_save_checkbox = QCheckBox("Auto-save after scan")
        self.auto_save_checkbox.setChecked(self._initial.auto_save_scan)
        summary_col.addWidget(self.auto_save_checkbox)

        self.save_scan_button = QPushButton("Save scan")
        self.save_scan_button.setEnabled(False)
        self.save_scan_button.clicked.connect(self._save_scan_matrix)
        summary_col.addWidget(self.save_scan_button)

        self.bell_history_plot = BellHistoryPlot()
        summary_col.addWidget(self.bell_history_plot)

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
        self.controller._configured = False

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
        self._update_coincidence_labels(state)
        self.status_label.setText(f"Acquiring… last counter shape: {counter.shape}")

    def _update_coincidence_labels(self, state: MeasurementState) -> None:
        """Countrate/total-counts now cover the coincidence (virtual)
        channels alongside the singles (see ``MeasurementController.
        configure()``), so this is genuinely new recorded data, not just a
        different view of what Counts already showed."""
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
        coincidence_rate = float(np.sum(rate[coincidence_idx]))
        coincidence_total = float(np.sum(total[coincidence_idx]))
        self.coincidence_rate_label.setText(f"Coincidence rate: {coincidence_rate:,.0f} cps")
        self.total_coincidences_label.setText(f"Total coincidences: {coincidence_total:,.0f}")

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
            self._stop_live_scan()
            return
        try:
            self._prepare_controller_config()
        except (ValueError, TypeError) as exc:
            self.status_label.setText(f"Settings error: {exc}")
            self._stop_live_scan()
            return

        # A fresh start (as opposed to this being the next cycle of an
        # already-running live loop) resets the cycle count, history
        # graph, and -- for live mode -- the running accumulated matrix.
        # A loop continuation must not reset any of that, or every cycle
        # would look like the first one, and the whole point of
        # accumulating -- a stable, ever-growing total rather than a
        # fresh independent (and noisier) reading each time -- would be
        # lost. It also means the matrix/heatmap/labels are never reset
        # to a blank placeholder between cycles: only a fresh start does
        # that, so a live loop just keeps adding to what's already shown
        # instead of flashing empty and refilling every cycle.
        if not self._live_scan_running:
            self._scan_cycle_count = 0
            self._s_history = []
            self.bell_history_plot.clear()
            self._live_matrix = np.zeros((4, 4))
            self._live_filled_mask = np.zeros((4, 4), dtype=bool)
            for r in range(4):
                for c in range(4):
                    self.bell_table.setItem(r, c, QTableWidgetItem("—"))
            self.bell_plot.clear()
            self._render_bell_summary(np.zeros(4), np.zeros(4), np.zeros(4, dtype=bool))
        self._live_scan_running = True

        alice = [c.channel for c in self.controller.config.alice_channels]
        bob = [c.channel for c in self.controller.config.bob_channels]
        alice_stage, bob_stage = self._bell_scan_stages()
        self._scan_matrix = np.zeros((4, 4))
        self._scan_filled = np.zeros((4, 4), dtype=bool)
        scan = BellScanController(
            self.controller.adapter,
            alice_stage,
            bob_stage,
            alice,
            bob,
            coincidence_window_ns=self.controller.config.coincidence_window_ns,
        )
        self._scan_integration_time_s = scan.config.integration_time_s
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
        if self.live_scan_checkbox.isChecked():
            self.status_label.setText(
                f"Running Bell scan… (live, cycle {self._scan_cycle_count + 1})"
            )
        else:
            self.save_scan_button.setEnabled(False)
            self.status_label.setText("Running Bell scan…")
        self.acquisition_changed.emit(True)

    def _display_matrix(self) -> np.ndarray:
        """The matrix actually shown in the heatmap/table: this cycle's
        raw counts in single-shot mode (matches what gets saved to disk),
        or the running total accumulated across every cycle of the
        current live loop while looping -- which keeps growing, cycle
        after cycle, the way a longer-integrated measurement should,
        rather than resetting to a fresh independent (and noisier)
        reading every time. E/S are computed from whichever of these is
        displayed: a raw accumulated count isn't just a rescaling of a
        single cycle's numbers the way a rate would be, it's a genuinely
        larger and more statistically meaningful dataset."""
        if self.live_scan_checkbox.isChecked():
            return self._live_matrix
        return self._scan_matrix

    def _display_filled(self) -> np.ndarray:
        if self.live_scan_checkbox.isChecked():
            return self._live_filled_mask
        return self._scan_filled

    def _on_scan_cell(self, row: int, col: int, value: float) -> None:
        self._scan_matrix[row, col] = value
        self._scan_filled[row, col] = True
        if self.live_scan_checkbox.isChecked():
            # Add to the running total rather than replacing it -- see
            # _display_matrix's docstring for why, and _run_bell_scan's
            # comment for why this is also what keeps a live loop from
            # ever flashing back to a blank display between cycles.
            self._live_matrix[row, col] += value
            self._live_filled_mask[row, col] = True

        display_matrix = self._display_matrix()
        display_filled = self._display_filled()
        self.bell_table.setItem(row, col, QTableWidgetItem(f"{display_matrix[row, col]:.0f}"))
        # Live per-cell update, no blocking: this handler already runs on
        # the GUI thread via Qt's normal (automatically queued) cross-thread
        # signal delivery from ScanWorker's own QThread -- the scan itself
        # never waits on this call -- and draw_idle() defers the actual
        # repaint to Qt's idle processing rather than forcing a synchronous
        # redraw for each of the 16 settings.
        self.bell_plot.update_matrix(display_matrix, filled=display_filled)
        # E/S are calculated live too, from whatever's been recorded so
        # far -- not only once the scan finishes. e_readiness() keeps this
        # honest: an E value only shows once every cell its formula reads
        # has a real recorded count, not a zero standing in for "not
        # measured yet", and S never shows until every E does, since each
        # S combines all four.
        e, s = calc_e_s(display_matrix)
        self._render_bell_summary(e, s, e_readiness(display_filled))

    def _render_bell_summary(self, e: np.ndarray, s: np.ndarray, e_ready: np.ndarray) -> None:
        e_text = ", ".join(f"{v:.2f}" if ready else "—" for v, ready in zip(e, e_ready, strict=True))
        self.bell_e_label.setText(f"E: {e_text}")
        if e_ready.all():
            s_text = ", ".join(f"{v:.2f}" for v in s)
            max_s = max((abs(v) for v in s), default=0.0)
            self.bell_s_label.setText(f"S: {s_text}  (max |S| = {max_s:.2f})")
        else:
            self.bell_s_label.setText("S: —, —, —, —")

    def _on_scan_finished(self, matrix: np.ndarray, e: np.ndarray, s: np.ndarray) -> None:
        # In live mode, _on_scan_cell has already folded every one of this
        # cycle's 16 values into self._live_matrix as they arrived, so the
        # authoritative "final" values for this point in the loop are the
        # accumulated ones, not the worker's own per-cycle-only e/s
        # (computed from just this one cycle's matrix, in isolation).
        is_live = self.live_scan_checkbox.isChecked()
        display_matrix = self._display_matrix()
        display_e, display_s = (calc_e_s(display_matrix) if is_live else (e, s))
        self._last_scan_matrix = display_matrix
        self._last_scan_e = display_e
        self._last_scan_s = display_s
        self._render_bell_summary(display_e, display_s, np.ones(4, dtype=bool))
        self.bell_plot.update_matrix(display_matrix, e=display_e, s=display_s)
        self.save_scan_button.setEnabled(True)

        self._scan_cycle_count += 1
        max_s = max((abs(v) for v in display_s), default=0.0)
        self._s_history.append(max_s)
        del self._s_history[:-200]  # bound memory/plot width for a long-running loop
        self.bell_history_plot.update_history(self._s_history)

        if self.auto_save_checkbox.isChecked():
            self._save_scan_matrix(auto=True)

        if is_live:
            # Stay "busy": the loop continues immediately (from
            # _on_scan_thread_finished, once this cycle's QThread has
            # actually stopped), so Settings/Time Tagger/Polarization stay
            # frozen and the scan/start buttons stay disabled until the
            # loop is truly stopped, not just between individual cycles.
            self.status_label.setText(
                f"Live — cycle {self._scan_cycle_count} complete (max |S| = {max_s:.2f}), "
                "starting next…"
            )
        else:
            self._stop_live_scan()
            if not self.auto_save_checkbox.isChecked():
                self.status_label.setText("Scan complete")

    def _on_scan_error(self, message: str) -> None:
        self.status_label.setText(f"Scan error: {message}")
        self._stop_live_scan()

    def _stop_live_scan(self) -> None:
        self._live_scan_running = False

    def _on_scan_thread_finished(self) -> None:
        self._scan_thread = None
        self._scan_worker = None
        if self._live_scan_running and self.live_scan_checkbox.isChecked():
            # Only safe to start the next cycle now that this QThread has
            # actually finished (not merely asked to via .quit()) --
            # starting it any earlier (e.g. straight from _on_scan_finished)
            # is a race: self._scan_thread might still be the old, not-yet-
            # cleared thread object, which trips _run_bell_scan's own
            # reentrancy guard and silently stalls the whole loop.
            QTimer.singleShot(0, self._run_bell_scan)
            return
        # Covers both a normal stop and the case where the checkbox was
        # unchecked in the gap between this cycle's _on_scan_finished
        # (which already decided to continue) and the QThread actually
        # finishing -- _live_scan_running must end up False either way, or
        # the *next* "Run Bell scan" click would wrongly treat itself as a
        # loop continuation and skip resetting the cycle count/history.
        self._stop_live_scan()
        if self.status_label.text().endswith("starting next…"):
            # Caught in that exact gap: _on_scan_finished already wrote a
            # "starting next…" message on the assumption the loop would
            # continue, so it needs correcting now that it won't.
            self.status_label.setText(f"Live scan stopped after cycle {self._scan_cycle_count}")
        self.scan_button.setEnabled(self._hardware_connected)
        self.start_button.setEnabled(self._hardware_connected)
        self.acquisition_changed.emit(False)

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
