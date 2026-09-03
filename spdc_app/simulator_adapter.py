from __future__ import annotations

import numpy as np

from .simulator import generate_synthetic_channels


class SimulatorAdapter:
    """A simulator-compatible adapter for the same interface as TimeTaggerAdapter."""

    def __init__(self):
        self.phase = 0.0
        self.sm = object()
        self._connected = True

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def setup_channel(self, channel: int, delay: float) -> None:
        return None

    def setup_sm(self) -> None:
        return None

    def setup_counters(self, channels, binwidth: float, timeframe: float) -> None:
        self.binwidth = binwidth
        self.timeframe = timeframe

    def setup_countrates(self, channels) -> None:
        self.channels = channels

    def setup_coincidences(self, a_channels, b_channels, coin_time_window: float):
        combos = []
        for a in a_channels:
            for b in b_channels:
                combos.append([a, b])
        return combos, [0, 1, 2, 3]

    def setup_correlations(self, a_channels, b_channels, corr_binwidth: float, corr_timeframe: float):
        self.corr_binwidth = corr_binwidth
        self.corr_timeframe = corr_timeframe

    def start_sm(self) -> None:
        return None

    def stop_sm(self) -> None:
        return None

    def get_counter_data(self):
        time_axis = np.linspace(0.0, self.timeframe, 800)
        alice, bob, coin = generate_synthetic_channels(time_axis, self.phase)
        data = np.vstack((time_axis, np.vstack((alice, bob, coin))))
        self.phase += 0.05
        return data

    def get_corr_data(self):
        values = np.linspace(0.0, 5.0, 16)
        idx = np.arange(values.size)
        return [np.vstack((idx, values))]

    def get_countrate_data(self):
        time_axis = np.linspace(0.0, self.timeframe, 800)
        alice, bob, coin = generate_synthetic_channels(time_axis, self.phase)
        return np.concatenate([alice[:10], bob[:10], coin[:10]])
