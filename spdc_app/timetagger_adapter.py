from __future__ import annotations

import numpy as np

try:
    import TimeTagger
except ImportError:  # fallback in environments without the hardware package
    TimeTagger = None


class TimeTaggerAdapter:
    """Thin adapter around the Swabian TimeTagger API."""

    def __init__(self):
        self.tagger = None
        self.sm = None
        self.counter = None
        self.countrate = None
        self.corrs = []
        self._connected = False

    def connect(self) -> bool:
        if TimeTagger is None:
            raise RuntimeError("TimeTagger package is not installed")
        self.tagger = TimeTagger.createTimeTagger()
        self._connected = True
        return True

    def disconnect(self) -> None:
        if self.tagger is not None and TimeTagger is not None:
            TimeTagger.freeTimeTagger(self.tagger)
        self.tagger = None
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected and self.tagger is not None

    def setup_channel(self, channel: int, delay: float) -> None:
        if not self.is_connected():
            raise RuntimeError("TimeTagger is not connected")
        self.tagger.setTriggerLevel(channel, 0.1)
        self.tagger.setInputDelay(channel, delay * 1e3)

    def setup_sm(self) -> None:
        if not self.is_connected():
            raise RuntimeError("TimeTagger is not connected")
        self.sm = TimeTagger.SynchronizedMeasurements(self.tagger)
        self.sm_tagger = self.sm.getTagger()

    def setup_counters(self, channels, binwidth: float, timeframe: float) -> None:
        if not self.is_connected():
            raise RuntimeError("TimeTagger is not connected")
        bin_count = int(np.ceil(timeframe * 1e3 / binwidth))
        self.counter = TimeTagger.Counter(self.sm_tagger, channels, binwidth * 1e9, bin_count)

    def setup_countrates(self, channels) -> None:
        if not self.is_connected():
            raise RuntimeError("TimeTagger is not connected")
        self.countrate = TimeTagger.Countrate(self.sm_tagger, channels)

    def setup_coincidences(self, a_channels, b_channels, coin_time_window: float):
        if not self.is_connected():
            raise RuntimeError("TimeTagger is not connected")
        combos = []
        for a in a_channels:
            for b in b_channels:
                combos.append([a, b])
        self.coin = TimeTagger.Coincidences(self.sm_tagger, combos, coin_time_window * 1e3)
        return combos, list(self.coin.getChannels())

    def setup_correlations(self, a_channels, b_channels, corr_binwidth: float, corr_timeframe: float):
        if not self.is_connected():
            raise RuntimeError("TimeTagger is not connected")
        corr_count = int(np.ceil(corr_timeframe / corr_binwidth))
        corr_list = []
        for b in b_channels:
            corr_list.append(TimeTagger.Correlation(self.sm_tagger, a_channels[0], b, corr_binwidth * 1e3, corr_count))
        self.corrs = corr_list

    def start_sm(self) -> None:
        if self.sm is not None:
            self.sm.start()

    def stop_sm(self) -> None:
        if self.sm is not None:
            self.sm.stop()

    def get_counter_data(self):
        if self.counter is None:
            return np.zeros((2, 1))
        new_values = np.array(self.counter.getData())
        new_index = np.array(self.counter.getIndex())
        return np.vstack((new_index, new_values))

    def get_corr_data(self):
        if not self.corrs:
            return [np.vstack((np.array([0.0]), np.array([0.0])))]
        packets = []
        for corr in self.corrs:
            new_values = np.array(corr.getData())
            new_index = np.array(corr.getIndex())
            packets.append(np.vstack((new_index, new_values)))
            corr.clear()
        return packets

    def get_countrate_data(self):
        if self.countrate is None:
            return np.zeros(1)
        new_data = np.array(self.countrate.getData())
        self.countrate.clear()
        return new_data
