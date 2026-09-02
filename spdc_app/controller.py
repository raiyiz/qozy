from __future__ import annotations

import numpy as np

from .bell_math import calc_e_s, coincidence_matrix_from_counts
from .data_model import MeasurementConfig, MeasurementState
from .simulator import generate_synthetic_channels


class SPDCController:
    def __init__(self, config: MeasurementConfig | None = None):
        self.config = config or MeasurementConfig()
        self.state = MeasurementState()

    def update_state(self, phase: float) -> None:
        time_axis = np.linspace(0.0, self.config.count_timeframe, 800)
        alice, bob, coin = generate_synthetic_channels(time_axis, phase)

        self.state.phase = phase
        self.state.alice_counts = list(alice)
        self.state.bob_counts = list(bob)
        self.state.coin_counts = list(coin)

        matrix = coincidence_matrix_from_counts(np.array([*alice[:4], *bob[:4], *coin[:4], *alice[4:8]])[:16])
        e_values, s_values = calc_e_s(matrix)
        self.state.s_value = float(s_values[0])
        self.state.corr_values = list(e_values)

    def summary_text(self) -> str:
        return (
            f"phase={self.state.phase:.2f} | "
            f"S={self.state.s_value:.2f} | "
            f"angle={self.config.detector_angle:.1f}°"
        )
