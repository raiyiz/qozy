"""Small process-wide hardware selection/connection manager.

The manager deliberately contains no Qt code. GUI workers call ``connect`` and
``disconnect`` from a background thread, while pages only consume the adapter
once the connection has succeeded.
"""

from __future__ import annotations

from typing import Literal

from qozy.hardware.base import MeasurementAdapter
from qozy.hardware.simulator import SimulatorAdapter
from qozy.hardware.timetagger_local import LocalTimeTagger
from qozy.hardware.timetagger_network import NetworkTimeTagger

BackendName = Literal["simulator", "timetagger-local", "timetagger-network"]


class HardwareManager:
    def __init__(self) -> None:
        self.backend: BackendName = "simulator"
        self.network_address = "localhost:41101"
        self.adapter: MeasurementAdapter = SimulatorAdapter()
        self.adapter.connect()
        self.connected = True

    def select(self, backend: BackendName, network_address: str = "") -> None:
        if self.connected:
            raise RuntimeError("Disconnect the current Time Tagger before changing backend")
        self.backend = backend
        if backend == "timetagger-network":
            self.network_address = network_address.strip()

    def connect(self) -> MeasurementAdapter:
        if self.connected:
            return self.adapter

        if self.backend == "simulator":
            adapter: MeasurementAdapter = SimulatorAdapter()
        elif self.backend == "timetagger-local":
            adapter = LocalTimeTagger()
        elif self.backend == "timetagger-network":
            adapter = NetworkTimeTagger(self.network_address)
        else:  # pragma: no cover - protected by BackendName
            raise ValueError(f"Unknown acquisition backend: {self.backend}")

        adapter.connect()
        self.adapter = adapter
        self.connected = True
        return adapter

    def disconnect(self) -> None:
        if not self.connected:
            return
        self.adapter.disconnect()
        self.connected = False
