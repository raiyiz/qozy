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


def test_poll_also_populates_bell_summary_when_adapter_supports_it() -> None:
    # SimulatorAdapter exposes get_coincidence_matrix() as a demo extra;
    # poll() should pick it up automatically.
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.start()
    state = controller.poll()
    assert state.coincidence_matrix is not None
    assert state.coincidence_matrix.shape == (4, 4)
    assert state.bell_e is not None
    assert state.bell_s is not None
    assert len(state.bell_s) == 4


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
