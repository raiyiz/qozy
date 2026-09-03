"""Orchestrates a MeasurementConfig + a MeasurementAdapter (real or
simulated) + Bell math, and hands back a MeasurementState.

Deliberately has no PyQt import. The GUI layer polls this from a QTimer or
QThread worker (see ``qozy.gui.worker``) and pushes the resulting state
into the VisPy plot panel; that separation is what makes this class
testable without a display.
"""

from __future__ import annotations

from qozy.core.bell_math import calc_e_s, coincidence_matrix_from_counts
from qozy.core.data_model import MeasurementConfig, MeasurementState
from qozy.hardware.base import MeasurementAdapter


class MeasurementController:
    def __init__(self, adapter: MeasurementAdapter, config: MeasurementConfig | None = None) -> None:
        self.adapter = adapter
        self.config = config or MeasurementConfig()
        self.state = MeasurementState()
        self._configured = False

    def configure(self) -> None:
        """Push the current config to the adapter."""
        alice = [c.channel for c in self.config.alice_channels]
        bob = [c.channel for c in self.config.bob_channels]

        self.adapter.setup_sm()
        for ch in self.config.alice_channels + self.config.bob_channels:
            self.adapter.setup_channel(ch.channel, ch.delay_ns)

        all_channels = self.config.all_channel_numbers()
        self.adapter.setup_counters(
            all_channels, self.config.counts_bin_width_ms, self.config.counts_time_frame_s
        )
        self.adapter.setup_countrates(all_channels)
        self.adapter.setup_coincidences(alice, bob, self.config.coincidence_window_ns)
        self.adapter.setup_correlations(
            alice,
            bob,
            self.config.correlation_bin_width_ns,
            self.config.correlation_time_frame_ns,
        )
        self._configured = True

    def start(self) -> None:
        if not self._configured:
            self.configure()
        self.adapter.start_sm()
        self.config.live_acquisition = True

    def stop(self) -> None:
        self.adapter.stop_sm()
        self.config.live_acquisition = False

    def poll(self) -> MeasurementState:
        """Pull the latest data from the adapter into ``self.state``."""
        self.state.counter_data = self.adapter.get_counter_data()
        self.state.corr_data = self.adapter.get_corr_data()
        self.state.countrate_data = self.adapter.get_countrate_data()
        return self.state

    def evaluate_bell(self, flat_coincidence_counts) -> None:
        """Compute E/S from a flat 16-value coincidence readout and stash
        the result on ``self.state``."""
        matrix = coincidence_matrix_from_counts(flat_coincidence_counts)
        e, s = calc_e_s(matrix)
        self.state.bell_e = e
        self.state.bell_s = s
