import numpy as np

from qozy.hardware.simulator import SimulatorAdapter


def make_adapter() -> SimulatorAdapter:
    sim = SimulatorAdapter(seed=0)
    sim.connect()
    sim.setup_sm()
    sim.setup_channel(1, 0.0)
    sim.setup_counters([1, 2], counts_bin_width_ms=100.0, counts_time_frame_s=1.0)
    sim.setup_countrates([1, 2])
    sim.setup_coincidences([1], [2], coin_time_window_ns=2.0)
    sim.setup_correlations([1], [2, 3], corr_bin_width_ns=1.0, corr_time_frame_ns=100.0)
    return sim


def test_get_counter_data_shape() -> None:
    sim = make_adapter()
    data = sim.get_counter_data()
    # 1 index row + 2 channel rows
    assert data.shape[0] == 3
    assert np.all(np.isfinite(data))


def test_get_corr_data_matches_b_channel_count() -> None:
    sim = make_adapter()
    corrs = sim.get_corr_data()
    assert len(corrs) == 2  # b_channels = [2, 3]
    for corr in corrs:
        assert corr.shape[0] == 2
        assert np.all(np.isfinite(corr))


def test_get_countrate_data_matches_channel_count() -> None:
    sim = make_adapter()
    rates = sim.get_countrate_data()
    assert rates.shape == (2,)


def test_disconnect_does_not_raise() -> None:
    sim = make_adapter()
    sim.stop_sm()
    sim.disconnect()
