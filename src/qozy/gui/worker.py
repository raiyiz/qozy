"""Background acquisition worker for MeasurementController."""

from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from qozy.core.bell_acquisition import BellAcquisition
from qozy.core.controller import MeasurementController
from qozy.core.data_model import MeasurementState


class AcquisitionWorker(QObject):
    """Own the measurement lifecycle and optionally a live Bell scan.

    A Bell scan is layered onto this same acquisition loop rather than
    creating a second adapter owner. That keeps the count graph and Bell
    matrix fed by the exact same ``MeasurementState`` stream.
    """

    data_ready = pyqtSignal(object)
    bell_updated = pyqtSignal(object)
    error = pyqtSignal(str)
    started = pyqtSignal()
    stopped = pyqtSignal()
    bell_cell_updated = pyqtSignal(int, int, float)
    bell_cell_completed = pyqtSignal(int, int, float)
    bell_finished = pyqtSignal(object)

    def __init__(
        self,
        controller: MeasurementController,
        interval_ms: int = 100,
        bell_acquisition: BellAcquisition | None = None,
    ) -> None:
        super().__init__()
        self.controller = controller
        self.interval_s = interval_ms / 1000.0
        self.bell_acquisition = bell_acquisition
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
        bell_started = False
        try:
            self.controller.start()
            controller_started = True
            self.started.emit()

            bell_started = False
            while not self._stop_event.is_set():
                state: MeasurementState = self.controller.poll()
                self.data_ready.emit(state)

                if self.bell_acquisition is not None and state.total_counts_data is not None:
                    if not bell_started:
                        update = self.bell_acquisition.start(state.total_counts_data)
                        bell_started = True
                    else:
                        update = self.bell_acquisition.update(state.total_counts_data)
                    self.bell_updated.emit(update)
                    if update.done:
                        break

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
    controller: MeasurementController,
    interval_ms: int = 100,
    bell_acquisition: BellAcquisition | None = None,
) -> tuple[QThread, AcquisitionWorker]:
    """Create a worker + thread pair; caller owns the returned objects."""
    thread = QThread()
    worker = AcquisitionWorker(controller, interval_ms, bell_acquisition)
    worker.moveToThread(thread)
    thread.started.connect(worker.start)
    worker.stopped.connect(thread.quit)
    return thread, worker
