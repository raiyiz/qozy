"""Drives an actual polarization-angle scan to build the 4x4 coincidence
matrix, instead of the single-poll stand-in ``SimulatorAdapter`` used to
expose as ``get_coincidence_matrix()``.

For each of the 4x4 (Alice angle, Bob angle) settings: move both stages,
integrate coincidences for a fixed time, record the total count. No Qt
here — ``qozy.gui`` drives this from its own worker thread the same way it
drives ``MeasurementController``, so the sequence itself stays testable
without a display.
"""

from __future__ import annotations

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
        """Run the full 16-setting scan and return the resulting 4x4 matrix.

        ``on_cell_done(row, col, count)`` is called after each cell, so the
        GUI can fill in the coincidence-matrix table live instead of
        waiting for the whole scan to finish.
        """
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
                        set_angle_context(a_angle, b_angle)  # simulator-only, see simulator.py

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
