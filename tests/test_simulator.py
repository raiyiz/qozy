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


def test_total_counts_accumulate_while_running() -> None:
    sim = make_adapter()
    sim.start_sm()
    first = sim.get_total_counts()
    second = sim.get_total_counts()
    assert first.shape == (2,)
    assert np.all(second >= first)
    assert np.any(second > first)


def test_total_counts_have_16_live_coincidence_channels() -> None:
    sim = SimulatorAdapter(seed=0)
    sim.connect()
    sim.setup_sm()
    alice = [1, 2, 3, 4]
    bob = [5, 6, 7, 8]
    sim.setup_counters(alice + bob, counts_bin_width_ms=100.0, counts_time_frame_s=1.0)
    sim.setup_coincidences(alice, bob, coin_time_window_ns=2.0)
    sim.setup_countrates(alice + bob + list(range(16)))
    sim.start_sm()
    first = sim.get_total_counts()
    second = sim.get_total_counts()
    assert first.shape == (24,)
    assert np.all(second[8:] >= first[8:])
    assert np.any(second[8:] > first[8:])


def test_disconnect_does_not_raise() -> None:
    sim = make_adapter()
    sim.stop_sm()
    sim.disconnect()
