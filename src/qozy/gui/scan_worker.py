"""Runs a BellScanController on a background QThread, emitting per-cell
progress and a final result — same pattern as AcquisitionWorker
(qozy.gui.worker), but one-shot instead of a repeating QTimer.
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot

from qozy.core.scan_controller import BellScanController


class ScanWorker(QObject):
    cell_done = pyqtSignal(int, int, float)
    finished = pyqtSignal(object, object, object)  # matrix, e, s
    error = pyqtSignal(str)

    def __init__(self, scan: BellScanController) -> None:
        super().__init__()
        self.scan = scan

    @pyqtSlot()
    def run(self) -> None:
        try:
            matrix: np.ndarray = self.scan.run(
                on_cell_done=lambda r, c, v: self.cell_done.emit(r, c, v)
            )
            e, s = self.scan.evaluate()
        except Exception as exc:  # noqa: BLE001 - surface any scan/hardware failure to the UI
            self.error.emit(str(exc))
            return
        self.finished.emit(matrix, e, s)


def make_scan_thread(scan: BellScanController) -> tuple[QThread, ScanWorker]:
    thread = QThread()
    worker = ScanWorker(scan)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    return thread, worker
