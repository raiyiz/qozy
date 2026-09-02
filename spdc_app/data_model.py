from dataclasses import dataclass, field


@dataclass
class MeasurementConfig:
    detector_angle: float = 22.5
    live_scan: bool = True
    count_timeframe: float = 5.0
    counts_binwidth: float = 0.1
    coincidence_time_window: float = 2.0
    corr_binwidth: float = 0.1
    corr_timeframe: float = 10.0
    matrix_integration_time: float = 1.0
    detector_channels: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5, 6, 7, 8])
    delays: dict[int, float] = field(default_factory=lambda: {i: 0.0 for i in range(1, 9)})


@dataclass
class MeasurementState:
    phase: float = 0.0
    alice_counts: list[float] = field(default_factory=list)
    bob_counts: list[float] = field(default_factory=list)
    coin_counts: list[float] = field(default_factory=list)
    corr_values: list[float] = field(default_factory=list)
    s_value: float = 0.0
