"""Process-wide hardware selection/connection manager."""

from __future__ import annotations

from typing import Literal

from qozy.core.data_model import TimeTaggerSettings
from qozy.hardware.base import MeasurementAdapter, PositionerAdapter
from qozy.hardware.elliptec_adapter import ElliptecAdapter
from qozy.hardware.simulator import SimulatorAdapter, SimulatorStage
from qozy.hardware.timetagger_local import LocalTimeTagger
from qozy.hardware.timetagger_network import NetworkTimeTagger

BackendName = Literal["simulator", "timetagger-local", "timetagger-network"]
StageBackendName = Literal["simulator", "elliptec"]
StageName = Literal["alice", "bob"]


class HardwareManager:
    def __init__(self) -> None:
        self.backend: BackendName = "simulator"
        self.network_address = "localhost:41101"
        self.adapter: MeasurementAdapter = SimulatorAdapter()
        self.adapter.connect()
        self.connected = True
        self.timetagger_settings = TimeTaggerSettings()

        self.stage_backends: dict[StageName, StageBackendName] = {
            "alice": "simulator",
            "bob": "simulator",
        }
        self.stage_ports: dict[StageName, str] = {"alice": "", "bob": ""}
        self.stage_addresses: dict[StageName, str] = {"alice": "0", "bob": "1"}
        self.stages: dict[StageName, PositionerAdapter] = {
            "alice": SimulatorStage(),
            "bob": SimulatorStage(),
        }
        self.stage_connected: dict[StageName, bool] = {"alice": True, "bob": True}
        self.stages["alice"].connect()
        self.stages["bob"].connect()

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
        else:  # pragma: no cover
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

    def configure_timetagger(self, settings: TimeTaggerSettings) -> None:
        """Apply all Time Tagger input and measurement settings to the backend."""
        if not self.connected:
            raise RuntimeError("Connect a Time Tagger backend before applying settings")
        errors = settings.validate()
        if errors:
            raise ValueError(" | ".join(errors))

        self.adapter.setup_sm()
        for channel in settings.channel_settings:
            if channel.enabled:
                self.adapter.setup_channel(
                    channel.channel, channel.delay_ns, channel.trigger_level_v
                )

        channels = settings.enabled_channels()
        self.adapter.setup_counters(
            channels, settings.counts_bin_width_ms, settings.counts_time_frame_s
        )
        self.adapter.setup_countrates(channels)
        self.adapter.setup_coincidences(
            settings.alice_channels,
            settings.bob_channels,
            settings.coincidence_window_ns,
        )
        self.adapter.setup_correlations(
            settings.alice_channels,
            settings.bob_channels,
            settings.correlation_bin_width_ns,
            settings.correlation_time_frame_ns,
        )
        self.timetagger_settings = settings

    def read_timetagger_settings(self) -> TimeTaggerSettings:
        """Read the backend's current values when adapter readback is supported."""
        if not self.connected:
            raise RuntimeError("Time Tagger is disconnected")
        reader = getattr(self.adapter, "read_current_settings", None)
        if reader is None:
            return self.timetagger_settings
        settings = reader()
        self.timetagger_settings = settings
        return settings

    def select_stage(
        self,
        stage: StageName,
        backend: StageBackendName,
        port: str = "",
        address: str = "0",
    ) -> None:
        if self.stage_connected[stage]:
            raise RuntimeError(
                f"Disconnect the {stage.title()} polarization stage before changing backend"
            )
        self.stage_backends[stage] = backend
        self.stage_ports[stage] = port.strip()
        self.stage_addresses[stage] = address.strip() or "0"

    def connect_stage(self, stage: StageName) -> PositionerAdapter:
        if self.stage_connected[stage]:
            return self.stages[stage]

        if self.stage_backends[stage] == "simulator":
            adapter: PositionerAdapter = SimulatorStage()
        elif self.stage_backends[stage] == "elliptec":
            port = self.stage_ports[stage]
            if not port:
                raise ValueError(
                    f"A serial port is required for the {stage.title()} polarization stage"
                )
            adapter = ElliptecAdapter(port=port, address=self.stage_addresses[stage])
        else:  # pragma: no cover
            raise ValueError(f"Unknown polarization stage backend: {self.stage_backends[stage]}")

        adapter.connect()
        self.stages[stage] = adapter
        self.stage_connected[stage] = True
        return adapter

    def disconnect_stage(self, stage: StageName) -> None:
        if not self.stage_connected[stage]:
            return
        self.stages[stage].disconnect()
        self.stage_connected[stage] = False

    def stage_angle(self, stage: StageName) -> float:
        if not self.stage_connected[stage]:
            raise RuntimeError(f"{stage.title()} polarization stage is disconnected")
        return self.stages[stage].get_angle()

    def move_stage(self, stage: StageName, angle_deg: float) -> float:
        if not self.stage_connected[stage]:
            raise RuntimeError(f"{stage.title()} polarization stage is disconnected")
        return self.stages[stage].set_angle(angle_deg)

    def home_stage(self, stage: StageName) -> float:
        if not self.stage_connected[stage]:
            raise RuntimeError(f"{stage.title()} polarization stage is disconnected")
        self.stages[stage].home()
        return self.stages[stage].get_angle()
