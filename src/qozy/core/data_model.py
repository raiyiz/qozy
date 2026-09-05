"""Configuration and live-state objects shared by the controller, hardware,
and GUI layers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChannelConfig:
    """A single detector channel and its input delay."""

    channel: int
    delay_ns: float = 0.0


@dataclass
class MeasurementConfig:
    """Everything needed to configure a measurement controller."""

    alice_channels: list[ChannelConfig] = field(default_factory=list)
    bob_channels: list[ChannelConfig] = field(default_factory=list)
    counts_bin_width_ms: float = 100.0
    counts_time_frame_s: float = 5.0
    coincidence_window_ns: float = 2.0
    correlation_bin_width_ns: float = 1.0
    correlation_time_frame_ns: float = 1000.0
    live_acquisition: bool = False

    def all_channel_numbers(self) -> list[int]:
        return [c.channel for c in (*self.alice_channels, *self.bob_channels)]


@dataclass
class MeasurementState:
    counter_data: object | None = None
    corr_data: object | None = None
    countrate_data: object | None = None
    coincidence_matrix: object | None = None
    bell_e: object | None = None
    bell_s: object | None = None


@dataclass
class TimeTaggerChannelSettings:
    """Configurable per-channel Time Tagger settings."""

    channel: int
    enabled: bool = True
    delay_ns: float = 0.0
    trigger_level_v: float = 0.1


@dataclass
class TimeTaggerSettings:
    """All device/measurement settings owned by TimeTaggerSettingsPage."""

    backend_mode: str = "simulator"
    channel_settings: list[TimeTaggerChannelSettings] = field(
        default_factory=lambda: [TimeTaggerChannelSettings(channel=i) for i in range(1, 9)]
    )
    alice_channels: list[int] = field(default_factory=lambda: [1, 2])
    bob_channels: list[int] = field(default_factory=lambda: [3, 4])
    counts_bin_width_ms: float = 100.0
    counts_time_frame_s: float = 5.0
    coincidence_window_ns: float = 2.0
    correlation_bin_width_ns: float = 1.0
    correlation_time_frame_ns: float = 1000.0
    measure_time_frame_s: float = 1.0

    def enabled_channels(self) -> list[int]:
        return [s.channel for s in self.channel_settings if s.enabled]

    def channel_delay_map(self) -> dict[int, float]:
        return {s.channel: s.delay_ns for s in self.channel_settings if s.enabled}

    def channel_trigger_map(self) -> dict[int, float]:
        return {s.channel: s.trigger_level_v for s in self.channel_settings if s.enabled}

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.backend_mode not in {"simulator", "hardware"}:
            errors.append("Backend mode must be either 'simulator' or 'hardware'.")
        if not self.alice_channels:
            errors.append("At least one Alice channel is required.")
        if not self.bob_channels:
            errors.append("At least one Bob channel is required.")
        overlap = sorted(set(self.alice_channels) & set(self.bob_channels))
        if overlap:
            errors.append(f"Alice/Bob channels must be distinct. Overlap: {overlap}.")
        if self.counts_bin_width_ms <= 0:
            errors.append("Counts bin width must be > 0.")
        if self.counts_time_frame_s <= 0:
            errors.append("Counts time frame must be > 0.")
        if self.coincidence_window_ns <= 0:
            errors.append("Coincidence window must be > 0.")
        if self.correlation_bin_width_ns <= 0:
            errors.append("Correlation bin width must be > 0.")
        if self.correlation_time_frame_ns <= 0:
            errors.append("Correlation time frame must be > 0.")
        if self.correlation_time_frame_ns < self.correlation_bin_width_ns:
            errors.append("Correlation time frame must be >= correlation bin width.")
        if self.measure_time_frame_s <= 0:
            errors.append("Measure time frame must be > 0.")
        seen: set[int] = set()
        for channel in self.channel_settings:
            if channel.channel <= 0:
                errors.append(f"Channel {channel.channel} must be > 0.")
            if channel.channel in seen:
                errors.append(f"Channel {channel.channel} appears more than once in channel settings.")
            seen.add(channel.channel)
            if channel.delay_ns < 0:
                errors.append(f"Channel {channel.channel} delay must be >= 0.")
            if channel.trigger_level_v <= 0:
                errors.append(f"Channel {channel.channel} trigger level must be > 0.")
        enabled = set(self.enabled_channels())
        missing = sorted((set(self.alice_channels) | set(self.bob_channels)) - enabled)
        if missing:
            errors.append(f"Acquisition channels must be enabled: {missing}.")
        return errors
