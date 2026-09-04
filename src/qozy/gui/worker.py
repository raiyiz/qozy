"""Run measurement lifecycle and polling on a background QThread."""

from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

from qozy.core.controller import MeasurementController
from qozy.core.data_model import MeasurementState


class AcquisitionWorker(QObject):
    """Own every potentially blocking MeasurementAdapter call.

    The GUI thread only starts/stops the QThread and consumes signals. In
    particular, ``controller.start()`` and ``controller.stop()`` are also run
    here; otherwise a future hardware backend could still block the GUI during
    start/stop even though polling was threaded.
    """

    data_ready = pyqtSignal(object)
    error = pyqtSignal(str)
    stopped = pyqtSignal()

    def __init__(self, controller: MeasurementController, interval_ms: int = 100) -> None:
        super().__init__()
        self.controller = controller
        self.interval_ms = interval_ms
        self._timer: QTimer | None = None

    @pyqtSlot()
    def start(self) -> None:
        try:
            self.controller.start()
            self._timer = QTimer(self)
            self._timer.timeout.connect(self._poll)
            self._timer.start(self.interval_ms)
        except Exception as exc:  # noqa: BLE001 - hardware errors belong in the UI
            self.error.emit(str(exc))
            self.stopped.emit()

    @pyqtSlot()
    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        try:
            self.controller.stop()
        except Exception as exc:  # noqa: BLE001 - report hardware stop failures
            self.error.emit(str(exc))
        finally:
            self.stopped.emit()

    @pyqtSlot()
    def _poll(self) -> None:
        try:
            state: MeasurementState = self.controller.poll()
        except Exception as exc:  # noqa: BLE001 - hardware failures belong in the UI
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
