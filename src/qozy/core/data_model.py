"""Configuration and live-state objects shared by the controller, the
hardware/simulator adapters, and the GUI.

Keeping these as plain dataclasses (no PyQt, no numpy required beyond
arrays already computed elsewhere) means the controller and adapters can be
exercised in tests without a display.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChannelConfig:
    """A single detector channel and its input delay."""

    channel: int
    delay_ns: float = 0.0


@dataclass
class MeasurementConfig:
    """Everything needed to (re)configure an acquisition.

    Units match the original ``timetaggerlive.py`` conventions:
    - ``counts_bin_width_ms`` / ``counts_time_frame_s`` for the Counter
    - ``coincidence_window_ns`` for Coincidences
    - ``correlation_bin_width_ns`` / ``correlation_time_frame_ns`` for Correlation
    """

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
    """Latest data pulled from the adapter, ready for plotting/summary."""

    counter_data: object | None = None
    corr_data: object | None = None
    countrate_data: object | None = None
    bell_e: object | None = None
    bell_s: object | None = None
