"""The interface both the real TimeTagger adapter and the simulator
implement, so the controller and GUI never need to know which one is
plugged in.

Mirrors the method set of the original ``timetaggerlive.timetagger_device``
class, just formalized as a ``Protocol`` so it can be type-checked and so a
new backend only needs to satisfy this shape.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class MeasurementAdapter(Protocol):
    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def setup_sm(self) -> None: ...

    def setup_channel(
        self, channel: int, delay: float, trigger_level_v: float = 0.1
    ) -> None: ...

    def setup_counters(
        self, channel_list: list[int], counts_bin_width_ms: float, counts_time_frame_s: float
    ) -> None: ...

    def setup_countrates(self, channels: list[int]) -> None: ...

    def setup_coincidences(
        self, a_channels: list[int], b_channels: list[int], coin_time_window_ns: float
    ) -> tuple[list[list[int]], list[int]]: ...

    def setup_correlations(
        self,
        a_channels: list[int],
        b_channels: list[int],
        corr_bin_width_ns: float,
        corr_time_frame_ns: float,
    ) -> None: ...

    def start_sm(self) -> None: ...

    def stop_sm(self) -> None: ...

    def measure_for_sm(self, time_frame_s: float) -> None: ...

    def get_counter_data(self) -> np.ndarray: ...

    def get_corr_data(self) -> list[np.ndarray]: ...

    def get_countrate_data(self) -> np.ndarray: ...

    def get_total_counts(self) -> np.ndarray: ...


@runtime_checkable
class PositionerAdapter(Protocol):
    """Shared shape for anything that moves a polarization setting —
    Thorlabs Elliptec rotators (real) or an in-memory stand-in (simulator).
    """

    def connect(self) -> None: ...

    def disconnect(self) -> None: ...

    def home(self) -> None: ...

    def get_angle(self) -> float: ...

    def set_angle(self, angle_deg: float) -> float: ...
