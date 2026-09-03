"""Synthetic stand-in for TimeTaggerAdapter.

Implements the same ``MeasurementAdapter`` shape so the GUI and controller
can run (and be tested) with no hardware attached. The waveform shapes are
adapted from the demo generator in ``old_spdc_to_port/spdc/main.py``
(``generate_spdc_data``), just restructured to match the real adapter's
return shapes (index row + per-channel value rows) instead of returning
Alice/Bob arrays directly.
"""

from __future__ import annotations

import numpy as np


class SimulatorAdapter:
    def __init__(self, seed: int | None = None) -> None:
        self._rng = np.random.default_rng(seed)
        self._phase = 0.0
        self._connected = False

        self._counter_channels: list[int] = []
        self._counts_bin_width_ms = 100.0
        self._counts_bin_number = 50

        self._countrate_channels: list[int] = []

        self._corr_b_channels: list[int] = []
        self._corr_bin_width_ns = 1.0
        self._corr_bin_number = 1000

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def setup_sm(self) -> None:
        pass

    def setup_channel(self, channel: int, delay: float) -> None:
        pass

    def setup_counters(
        self, channel_list: list[int], counts_bin_width_ms: float, counts_time_frame_s: float
    ) -> None:
        self._counter_channels = list(channel_list)
        self._counts_bin_width_ms = counts_bin_width_ms
        self._counts_bin_number = int(np.ceil(counts_time_frame_s * 1e3 / counts_bin_width_ms))

    def setup_countrates(self, channels: list[int]) -> None:
        self._countrate_channels = list(channels)

    def setup_coincidences(
        self, a_channels: list[int], b_channels: list[int], coin_time_window_ns: float
    ) -> tuple[list[list[int]], list[int]]:
        combos = [[a, b] for a in a_channels for b in b_channels]
        return combos, list(range(len(combos)))

    def setup_correlations(
        self,
        a_channels: list[int],
        b_channels: list[int],
        corr_bin_width_ns: float,
        corr_time_frame_ns: float,
    ) -> None:
        self._corr_b_channels = list(b_channels)
        self._corr_bin_width_ns = corr_bin_width_ns
        self._corr_bin_number = int(np.ceil(corr_time_frame_ns / corr_bin_width_ns))

    def start_sm(self) -> None:
        pass

    def stop_sm(self) -> None:
        pass

    def measure_for_sm(self, time_frame_s: float) -> None:
        self._phase += 0.05

    def get_counter_data(self) -> np.ndarray:
        self._phase += 0.03
        n_bins = max(self._counter_channels and self._counts_bin_number, 1)
        index = np.arange(n_bins) * self._counts_bin_width_ms
        rows = [index]
        for i, _ch in enumerate(self._counter_channels):
            base = 1000 + 200 * i
            values = base + 150 * np.sin(index / 400.0 + self._phase + i)
            values += self._rng.normal(0, 15, size=n_bins)
            rows.append(np.clip(values, 0, None))
        return np.vstack(rows) if rows[1:] else index.reshape(1, -1)

    def get_corr_data(self) -> list[np.ndarray]:
        self._phase += 0.02
        n_bins = max(self._corr_bin_number, 1)
        index = (np.arange(n_bins) - n_bins / 2) * self._corr_bin_width_ns
        results = []
        for i, _b in enumerate(self._corr_b_channels):
            envelope = 200 * np.exp(-((index) / (30 + 5 * i)) ** 2)
            envelope += self._rng.normal(0, 8, size=n_bins)
            results.append(np.vstack((index, np.clip(envelope, 0, None))))
        return results

    def get_countrate_data(self) -> np.ndarray:
        n = max(len(self._countrate_channels), 1)
        base = 1000 + 100 * np.arange(n)
        return base + self._rng.normal(0, 30, size=n)

    def get_total_counts(self) -> np.ndarray:
        n = max(len(self._countrate_channels), 1)
        return (1000 + 100 * np.arange(n)) * 100
