"""Polls a MeasurementController on a background QThread and emits the
results, so the main window's paint/event loop never blocks on hardware
(or simulator) I/O.

This mirrors plan.md's "Qt worker threads for live acquisition" step: the
worker only touches the controller/adapter; the main window only touches
the emitted signal, never the adapter directly.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

from qozy.core.controller import MeasurementController
from qozy.core.data_model import MeasurementState


class AcquisitionWorker(QObject):
    data_ready = pyqtSignal(object)  # emits MeasurementState
    error = pyqtSignal(str)

    def __init__(self, controller: MeasurementController, interval_ms: int = 100) -> None:
        super().__init__()
        self.controller = controller
        self.interval_ms = interval_ms
        self._timer: QTimer | None = None

    @pyqtSlot()
    def start(self) -> None:
        """Must run on this worker's own thread — the QTimer it creates is
        bound to whatever thread calls this. Only ever invoke via the
        ``thread.started`` signal (see ``make_worker_thread``), never
        directly from the GUI thread."""
        self._timer = QTimer()
        self._timer.timeout.connect(self._poll)
        self._timer.start(self.interval_ms)

    @pyqtSlot()
    def stop(self) -> None:
        """Same rule as ``start``: call this via a queued cross-thread
        signal/slot connection (or QMetaObject.invokeMethod), never
        directly — see ``CountsPage._stop``."""
        if self._timer is not None:
            self._timer.stop()

    def _poll(self) -> None:
        try:
            state: MeasurementState = self.controller.poll()
        except Exception as exc:  # surface adapter errors instead of crashing the thread
            self.error.emit(str(exc))
            return
        self.data_ready.emit(state)


def make_worker_thread(
    controller: MeasurementController, interval_ms: int = 100
) -> tuple[QThread, AcquisitionWorker]:
    """Create a worker + thread pair; caller owns starting/stopping both."""
    thread = QThread()
    worker = AcquisitionWorker(controller, interval_ms)
    worker.moveToThread(thread)
    thread.started.connect(worker.start)
    return thread, worker
