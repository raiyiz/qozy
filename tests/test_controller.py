import numpy as np

from qozy.core.controller import MeasurementController
from qozy.core.data_model import ChannelConfig, MeasurementConfig
from qozy.hardware.simulator import SimulatorAdapter


def make_config() -> MeasurementConfig:
    return MeasurementConfig(
        alice_channels=[ChannelConfig(channel=1), ChannelConfig(channel=2)],
        bob_channels=[ChannelConfig(channel=3), ChannelConfig(channel=4)],
    )


def test_start_configures_and_starts() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.start()
    assert controller.config.live_acquisition is True
    assert controller._configured is True


def test_poll_populates_state() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.start()
    state = controller.poll()
    assert state.counter_data is not None
    assert state.corr_data is not None
    assert state.countrate_data is not None
    assert state.total_counts_data is not None


def test_configure_extends_countrate_with_coincidence_channels() -> None:
    """setup_countrates() must cover the coincidence (virtual) channels
    alongside the singles, so a live coincidence rate is recorded, not
    just the per-detector rates."""
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.configure()
    state = controller.poll()

    # 2 Alice + 2 Bob singles, plus 2x2=4 coincidence combinations
    assert len(state.countrate_labels) == 4 + 4
    assert state.countrate_data.shape[0] == len(state.countrate_labels)
    assert state.total_counts_data.shape[0] == len(state.countrate_labels)
    coincidence_labels = [label for label in state.countrate_labels if label.startswith("coin ")]
    assert coincidence_labels == ["coin 1×3", "coin 1×4", "coin 2×3", "coin 2×4"]


def test_evaluate_bell_sets_state() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    flat = np.arange(1, 17, dtype=float)
    controller.evaluate_bell(flat)
    assert controller.state.bell_e is not None
    assert controller.state.bell_s is not None


def test_stop_clears_live_flag() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.start()
    controller.stop()
    assert controller.config.live_acquisition is False
