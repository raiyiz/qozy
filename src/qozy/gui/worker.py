"""Background acquisition worker for MeasurementController."""

from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from qozy.core.controller import MeasurementController
from qozy.core.data_model import MeasurementState


class AcquisitionWorker(QObject):
    """Own the complete measurement lifecycle on a background thread.

    The worker deliberately does not use a Qt timer. Its acquisition loop is
    synchronous inside the worker thread, while ``request_stop`` is safe to
    call directly from the GUI because it only sets a thread-safe Event.
    """

    data_ready = pyqtSignal(object)
    error = pyqtSignal(str)
    started = pyqtSignal()
    stopped = pyqtSignal()

    def __init__(self, controller: MeasurementController, interval_ms: int = 100) -> None:
        super().__init__()
        self.controller = controller
        self.interval_s = interval_ms / 1000.0
        self._stop_event = threading.Event()
        self._started = False

    def request_stop(self) -> None:
        """Request stop from any thread without relying on Qt event dispatch."""
        self._stop_event.set()

    @pyqtSlot()
    def start(self) -> None:
        """Run the controller lifecycle entirely on the worker thread."""
        if self._started:
            return
        self._started = True
        controller_started = False
        try:
            self.controller.start()
            controller_started = True
            self.started.emit()

            while not self._stop_event.is_set():
                state: MeasurementState = self.controller.poll()
                self.data_ready.emit(state)
                self._stop_event.wait(self.interval_s)
        except Exception as exc:  # noqa: BLE001 - hardware errors belong in the UI
            self.error.emit(str(exc))
        finally:
            try:
                if controller_started:
                    self.controller.stop()
            except Exception as exc:  # noqa: BLE001 - report hardware stop failures
                self.error.emit(str(exc))
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
