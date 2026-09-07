"""Drives polarization-angle scans and the live Bell scan state machine."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from qozy.core.bell_math import BELL_ANGLES_DEG, calc_e_s
from qozy.hardware.base import MeasurementAdapter, PositionerAdapter


@dataclass
class ScanConfig:
    settings_deg: tuple[float, ...] = BELL_ANGLES_DEG
    integration_time_s: float = 0.5


class BellScanController:
    def __init__(
        self,
        coincidence_adapter: MeasurementAdapter,
        alice_stage: PositionerAdapter,
        bob_stage: PositionerAdapter,
        alice_channels: list[int],
        bob_channels: list[int],
        coincidence_window_ns: float = 2.0,
        config: ScanConfig | None = None,
    ) -> None:
        self.adapter = coincidence_adapter
        self.alice_stage = alice_stage
        self.bob_stage = bob_stage
        self.alice_channels = alice_channels
        self.bob_channels = bob_channels
        self.coincidence_window_ns = coincidence_window_ns
        self.config = config or ScanConfig()
        self.matrix = np.zeros((4, 4))

    def run(self, on_cell_done: Callable[[int, int, float], None] | None = None) -> np.ndarray:
        """Run the original blocking 16-setting scan."""
        _, coin_channels = self.adapter.setup_coincidences(
            self.alice_channels, self.bob_channels, self.coincidence_window_ns
        )
        self.adapter.setup_countrates(coin_channels)
        self.adapter.setup_sm()
        self.adapter.start_sm()

        set_angle_context = getattr(self.adapter, "set_angle_context", None)

        try:
            angles = self.config.settings_deg
            for i, a_angle in enumerate(angles):
                self.alice_stage.set_angle(a_angle)
                for j, b_angle in enumerate(angles):
                    self.bob_stage.set_angle(b_angle)
                    if set_angle_context is not None:
                        set_angle_context(a_angle, b_angle)

                    self.adapter.measure_for_sm(self.config.integration_time_s)
                    cell = float(np.sum(self.adapter.get_total_counts()))
                    self.matrix[i, j] = cell
                    if on_cell_done is not None:
                        on_cell_done(i, j, cell)
        finally:
            self.adapter.stop_sm()

        return self.matrix

    def evaluate(self) -> tuple[np.ndarray, np.ndarray]:
        """E/S from the matrix built by the last ``run()``."""
        return calc_e_s(self.matrix)


class LiveBellScan:
    """State machine layered on an already-running acquisition.

    The measurement controller remains the sole owner of the adapter. Each
    update consumes the controller's cumulative coincidence totals, so the
    current matrix cell can be refreshed on every acquisition poll without
    starting a second TimeTagger measurement stream.
    """

    def __init__(
        self,
        adapter: MeasurementAdapter,
        alice_stage: PositionerAdapter,
        bob_stage: PositionerAdapter,
        alice_channels: list[int],
        bob_channels: list[int],
        config: ScanConfig | None = None,
    ) -> None:
        self.adapter = adapter
        self.alice_stage = alice_stage
        self.bob_stage = bob_stage
        self.alice_channels = alice_channels
        self.bob_channels = bob_channels
        self.config = config or ScanConfig()
        self.matrix = np.zeros((4, 4))
        self.row = 0
        self.col = 0
        self._baseline = 0.0
        self._started_at = 0.0
        self._done = False
        self._set_angle_context = getattr(adapter, "set_angle_context", None)

    @property
    def done(self) -> bool:
        return self._done

    def start(self, total_counts: object) -> None:
        """Move to the first setting and establish a cumulative baseline."""
        self.row = 0
        self.col = 0
        self.matrix.fill(0.0)
        self._done = False
        self._baseline = self._coincidence_total(total_counts)
        self._move_to_current_cell()
        self._started_at = time.monotonic()

    def update(self, total_counts: object) -> tuple[int, int, float, bool]:
        """Update the current cell and advance when its integration expires.

        Returns ``(row, col, value, completed)``. ``completed`` is true only
        when the update finishes the entire 4x4 scan.
        """
        if self._done:
            return self.row, self.col, float(self.matrix[self.row, self.col]), True

        value = max(0.0, self._coincidence_total(total_counts) - self._baseline)
        self.matrix[self.row, self.col] = value
        if time.monotonic() - self._started_at < self.config.integration_time_s:
            return self.row, self.col, value, False

        completed_row, completed_col = self.row, self.col
        if self.col == len(self.config.settings_deg) - 1:
            if self.row == len(self.config.settings_deg) - 1:
                self._done = True
                return completed_row, completed_col, value, True
            self.row += 1
            self.col = 0
        else:
            self.col += 1

        self._move_to_current_cell()
        self._baseline = self._coincidence_total(total_counts)
        self._started_at = time.monotonic()
        return completed_row, completed_col, value, False

    def _move_to_current_cell(self) -> None:
        a_angle = self.config.settings_deg[self.row]
        b_angle = self.config.settings_deg[self.col]
        self.alice_stage.set_angle(a_angle)
        self.bob_stage.set_angle(b_angle)
        if self._set_angle_context is not None:
            self._set_angle_context(a_angle, b_angle)

    def _coincidence_total(self, total_counts: object) -> float:
        values = np.asarray(total_counts, dtype=float).reshape(-1)
        offset = len(self.alice_channels) + len(self.bob_channels)
        count = len(self.alice_channels) * len(self.bob_channels)
        if values.size < offset + count:
            raise ValueError(
                "Live Bell scan requires cumulative coincidence totals from the configured acquisition"
            )
        return float(np.sum(values[offset : offset + count]))
