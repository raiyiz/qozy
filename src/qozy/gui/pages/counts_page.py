"""The Counts page: the first page actually wired to real logic instead of
placeholder metric cards. Replaces the standalone window from
``old_spdc_to_port/spdc/main.py`` — same live acquisition + channel config
idea, now embedded as one tab of the QOZY shell and driven by
MeasurementController instead of hand-rolled UI state.

Runs against SimulatorAdapter by default. Swapping in
``qozy.hardware.timetagger_adapter.TimeTaggerAdapter`` is a one-line change
in ``qozy.app`` once real hardware is available (see plan.md Phase 4).
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QMetaObject, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from qozy.core.controller import MeasurementController
from qozy.core.data_model import ChannelConfig, MeasurementConfig, MeasurementState
from qozy.gui.components import Card
from qozy.gui.plot_panel import PlotPanel
from qozy.gui.worker import make_worker_thread
from qozy.hardware.simulator import SimulatorAdapter


def _parse_channels(text: str) -> list[ChannelConfig]:
    channels = []
    for part in text.split(","):
        part = part.strip()
        if part:
            channels.append(ChannelConfig(channel=int(part)))
    return channels


class CountsPage(QWidget):
    def __init__(self, controller: MeasurementController | None = None) -> None:
        super().__init__()
        self.controller = controller or MeasurementController(
            SimulatorAdapter(), MeasurementConfig()
        )
        self._thread = None
        self._worker = None

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

    def _start(self) -> None:
        self.controller.config.alice_channels = _parse_channels(self.alice_edit.text())
        self.controller.config.bob_channels = _parse_channels(self.bob_edit.text())
        self.controller._configured = False
        self.controller.start()

        self._thread, self._worker = make_worker_thread(self.controller, interval_ms=100)
        self._worker.data_ready.connect(self._on_data)
        self._worker.error.connect(self._on_error)
        self._thread.start()

        self.live_checkbox.setChecked(True)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("Acquiring…")

    def _stop(self) -> None:
        if self._worker is not None:
            # self._worker lives on the background thread; a direct call
            # here would touch its QTimer from the wrong thread. Queue it
            # so it actually runs on the worker's own thread.
            QMetaObject.invokeMethod(
                self._worker, "stop", Qt.ConnectionType.QueuedConnection
            )
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait()
        self.controller.stop()

        self.live_checkbox.setChecked(False)
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Stopped")

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
        self._stop()
