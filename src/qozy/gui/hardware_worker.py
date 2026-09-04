"""Background worker for potentially blocking hardware connection calls."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from qozy.hardware.manager import HardwareManager


class HardwareWorker(QObject):
    connected = pyqtSignal(object)
    disconnected = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, manager: HardwareManager, action: str) -> None:
        super().__init__()
        self.manager = manager
        self.action = action

    @pyqtSlot()
    def run(self) -> None:
        try:
            if self.action == "connect":
                self.connected.emit(self.manager.connect())
            elif self.action == "disconnect":
                self.manager.disconnect()
                self.disconnected.emit()
            else:  # pragma: no cover - only constructed internally
                raise ValueError(f"Unknown hardware action: {self.action}")
        except Exception as exc:  # noqa: BLE001 - hardware errors belong in the UI
            self.error.emit(str(exc))
