"""Swabian Instruments TimeTagger adapter.

The adapter is intentionally agnostic about where the Time Tagger comes from:
``address=None`` creates a local USB Time Tagger, while a server address uses
Network Time Tagger. Both expose the same SDK measurement API, so the rest of
QOZY does not need to care about the transport.

The vendor SDK is imported lazily in ``connect()`` because it is an optional
hardware dependency and is not needed for simulator-only development/CI.
"""

from __future__ import annotations

import numpy as np

from qozy.core.data_model import TimeTaggerChannelSettings, TimeTaggerSettings


class TimeTaggerAdapter:
    def __init__(self, address: str | None = None) -> None:
        self.address = address
        self.tagger = None
        self.sm = None
        self.sm_tagger = None
        self.counter = None
        self.countrate = None
        self.coin = None
        self.corrs: list = []
        self._connected = False
        self._channel_delay_ns: dict[int, float] = {}
        self._channel_trigger_v: dict[int, float] = {}
        self._last_counts_bin_width_ms = 100.0
        self._last_counts_time_frame_s = 5.0
        self._last_alice_channels: list[int] = [1, 2]
        self._last_bob_channels: list[int] = [3, 4]
        self._last_coincidence_window_ns = 2.0
        self._last_correlation_bin_width_ns = 1.0
        self._last_correlation_time_frame_ns = 1000.0
        self._TimeTagger = None

    def connect(self) -> None:
        try:
            from Swabian import TimeTagger
        except ImportError as exc:
            raise RuntimeError(
                "TimeTagger Python SDK is not installed in this environment. "
                "Install the Swabian Instruments TimeTagger package, or switch "
                "the backend to Simulator."
            ) from exc

        self._TimeTagger = TimeTagger
        if self.address:
            # Current Network Time Tagger accepts a list of server addresses;
            # keeping this as a one-element list leaves room for multi-server
            # support later without changing the adapter interface.
            self.tagger = TimeTagger.createTimeTaggerNetwork([self.address])
        else:
            self.tagger = TimeTagger.createTimeTagger()
        self._connected = True

    def disconnect(self) -> None:
        if self.tagger is not None:
            self._TimeTagger.freeTimeTagger(self.tagger)
        self.tagger = None
        self._connected = False
        self.sm = None
        self.sm_tagger = None

    def is_connected(self) -> bool:
        return self._connected and self.tagger is not None

    def get_device_info(self) -> str:
        if not self.is_connected():
            return "Disconnected"
        # Serial/model helpers vary by SDK versions; keep this robust.
        return "TimeTagger connected"

    def setup_sm(self) -> None:
        self.sm = self._TimeTagger.SynchronizedMeasurements(self.tagger)
        self.sm_tagger = self.sm.getTagger()

    def setup_channel(
        self, channel: int, delay: float, trigger_level_v: float = 0.1
    ) -> None:
        """``delay`` is in ns."""
        self.tagger.setTriggerLevel(channel, trigger_level_v)
        self.tagger.setInputDelay(channel, delay * 1e3)
        self._channel_delay_ns[channel] = delay
        self._channel_trigger_v[channel] = trigger_level_v

    def setup_counters(
        self, channel_list: list[int], counts_bin_width_ms: float, counts_time_frame_s: float
    ) -> None:
        counts_bin_number = np.ceil(counts_time_frame_s * 1e3 / counts_bin_width_ms)
        self.counter = self._TimeTagger.Counter(
            self.sm_tagger, channel_list, counts_bin_width_ms * 1e9, counts_bin_number
        )
        self._last_counts_bin_width_ms = counts_bin_width_ms
        self._last_counts_time_frame_s = counts_time_frame_s

    def setup_countrates(self, channels: list[int]) -> None:
        self.countrate = self._TimeTagger.Countrate(self.sm_tagger, channels)

    def setup_coincidences(
        self, a_channels: list[int], b_channels: list[int], coin_time_window_ns: float
    ) -> tuple[list[list[int]], list[int]]:
        coin_channel_combinations = [[a, b] for a in a_channels for b in b_channels]
        self.coin = self._TimeTagger.Coincidences(
            self.sm_tagger, coin_channel_combinations, coin_time_window_ns * 1e3
        )
        coin_channel_list = list(self.coin.getChannels())
        self._last_alice_channels = list(a_channels)
        self._last_bob_channels = list(b_channels)
        self._last_coincidence_window_ns = coin_time_window_ns
        return coin_channel_combinations, coin_channel_list

    def setup_correlations(
        self,
        a_channels: list[int],
        b_channels: list[int],
        corr_bin_width_ns: float,
        corr_time_frame_ns: float,
    ) -> None:
        corr_bin_number = np.ceil(corr_time_frame_ns / corr_bin_width_ns)
        self.corrs = [
            self._TimeTagger.Correlation(
                self.sm_tagger, a_channels[0], b, corr_bin_width_ns * 1e3, corr_bin_number
            )
            for b in b_channels
        ]
        self._last_alice_channels = list(a_channels)
        self._last_bob_channels = list(b_channels)
        self._last_correlation_bin_width_ns = corr_bin_width_ns
        self._last_correlation_time_frame_ns = corr_time_frame_ns

    def start_sm(self) -> None:
        self.sm.start()

    def stop_sm(self) -> None:
        self.sm.stop()

    def measure_for_sm(self, time_frame_s: float) -> None:
        self.sm.startFor(time_frame_s * 1e12, clear=True)
        self.sm.waitUntilFinished()

    def get_counter_data(self) -> np.ndarray:
        new_values = np.array(self.counter.getData())
        new_index = np.array(self.counter.getIndex())
        return np.vstack((new_index, new_values))

    def get_corr_data(self) -> list[np.ndarray]:
        new_datas = []
        for corr in self.corrs:
            new_values = np.array(corr.getData())
            new_index = np.array(corr.getIndex())
            new_datas.append(np.vstack((new_index, new_values)))
            corr.clear()
        return new_datas

    def get_countrate_data(self) -> np.ndarray:
        new_data = np.array(self.countrate.getData())
        self.countrate.clear()
        return new_data

    def get_total_counts(self) -> np.ndarray:
        return np.array(self.countrate.getCountsTotal())

    def read_current_settings(self) -> TimeTaggerSettings:
        if not self.is_connected():
            raise RuntimeError("TimeTagger is not connected")

        channel_settings: list[TimeTaggerChannelSettings] = []
        for channel in range(1, 9):
            delay_ns = self._channel_delay_ns.get(channel, 0.0)
            trigger_v = self._channel_trigger_v.get(channel, 0.1)

            if hasattr(self.tagger, "getInputDelay"):
                raw_delay_ps = float(self.tagger.getInputDelay(channel))
                delay_ns = raw_delay_ps / 1e3
            if hasattr(self.tagger, "getTriggerLevel"):
                trigger_v = float(self.tagger.getTriggerLevel(channel))

            channel_settings.append(
                TimeTaggerChannelSettings(
                    channel=channel,
                    enabled=True,
                    delay_ns=delay_ns,
                    trigger_level_v=trigger_v,
                )
            )

        return TimeTaggerSettings(
            backend_mode="hardware",
            channel_settings=channel_settings,
            alice_channels=list(self._last_alice_channels),
            bob_channels=list(self._last_bob_channels),
            counts_bin_width_ms=self._last_counts_bin_width_ms,
            counts_time_frame_s=self._last_counts_time_frame_s,
            coincidence_window_ns=self._last_coincidence_window_ns,
            correlation_bin_width_ns=self._last_correlation_bin_width_ns,
            correlation_time_frame_ns=self._last_correlation_time_frame_ns,
        )
