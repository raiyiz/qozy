"""Background acquisition worker for MeasurementController."""

from __future__ import annotations

from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot

from qozy.core.controller import MeasurementController
from qozy.core.data_model import MeasurementState


class AcquisitionWorker(QObject):
    """Own the complete measurement lifecycle on a background thread.

    No MeasurementAdapter call is made from the GUI thread. The worker emits
    data/error/state signals back to the page and stops itself after a
    requested stop or hardware error.
    """

    data_ready = pyqtSignal(object)
    error = pyqtSignal(str)
    started = pyqtSignal()
    stopped = pyqtSignal()

    def __init__(self, controller: MeasurementController, interval_ms: int = 100) -> None:
        super().__init__()
        self.controller = controller
        self.interval_ms = interval_ms
        self._running = False
        self._timer: QTimer | None = None

    @pyqtSlot()
    def start(self) -> None:
        """Start the controller and polling timer on the worker thread."""
        if self._running:
            return
        try:
            self.controller.start()
            self._timer = QTimer(self)
            self._timer.setInterval(self.interval_ms)
            self._timer.timeout.connect(self._poll)
            self._timer.start()
            self._running = True
            self.started.emit()
        except Exception as exc:  # noqa: BLE001 - hardware errors belong in the UI
            self.error.emit(str(exc))
            self._finish()

    @pyqtSlot()
    def stop(self) -> None:
        """Stop acquisition on the worker thread."""
        self._finish()

    @pyqtSlot()
    def _poll(self) -> None:
        if not self._running:
            return
        try:
            state: MeasurementState = self.controller.poll()
        except Exception as exc:  # noqa: BLE001 - hardware errors belong in the UI
            self.error.emit(str(exc))
            self._finish()
            return
        self.data_ready.emit(state)

    def _finish(self) -> None:
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.stop()
            timer.deleteLater()

        was_running = self._running
        self._running = False
        try:
            if was_running:
                self.controller.stop()
        except Exception as exc:  # noqa: BLE001 - report hardware stop failures
            self.error.emit(str(exc))
        finally:
            self.stopped.emit()


def make_worker_thread(
    controller: MeasurementController, interval_ms: int = 100
) -> tuple[QThread, AcquisitionWorker]:
    """Create a worker + thread pair; caller owns the returned objects."""
    thread = QThread()
    worker = AcquisitionWorker(controller, interval_ms)
    worker.moveToThread(thread)
    thread.started.connect(worker.start)
    worker.stopped.connect(thread.quit)
    return thread, worker
