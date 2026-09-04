"""Background workers for potentially blocking hardware calls."""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from qozy.hardware.manager import HardwareManager, StageName


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


class StageWorker(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(
        self,
        manager: HardwareManager,
        stage: StageName,
        action: str,
        angle_deg: float | None = None,
    ) -> None:
        super().__init__()
        self.manager = manager
        self.stage = stage
        self.action = action
        self.angle_deg = angle_deg

    @pyqtSlot()
    def run(self) -> None:
        try:
            if self.action == "connect":
                self.result.emit(self.manager.connect_stage(self.stage))
            elif self.action == "disconnect":
                self.manager.disconnect_stage(self.stage)
                self.result.emit(None)
            elif self.action == "angle":
                self.result.emit(self.manager.stage_angle(self.stage))
            elif self.action == "move":
                if self.angle_deg is None:
                    raise ValueError("An angle is required for a stage move")
                self.result.emit(self.manager.move_stage(self.stage, self.angle_deg))
            elif self.action == "home":
                self.result.emit(self.manager.home_stage(self.stage))
            else:  # pragma: no cover - only constructed internally
                raise ValueError(f"Unknown stage action: {self.action}")
        except Exception as exc:  # noqa: BLE001 - hardware errors belong in the UI
            self.error.emit(str(exc))
