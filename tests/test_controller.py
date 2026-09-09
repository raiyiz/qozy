"""Tests for qozy.core.controller.MeasurementController."""

from __future__ import annotations

import numpy as np
import pytest

from qozy.core.bell_math import calc_e_s, coincidence_matrix_from_counts
from qozy.core.controller import MeasurementController
from qozy.core.data_model import ChannelConfig, MeasurementConfig
from qozy.hardware.simulator import SimulatorAdapter


def make_config(
    alice_channels: list[int] | None = None,
    bob_channels: list[int] | None = None,
    **kwargs,
) -> MeasurementConfig:
    alice_channels = [1, 2] if alice_channels is None else alice_channels
    bob_channels = [3, 4] if bob_channels is None else bob_channels
    return MeasurementConfig(
        alice_channels=[ChannelConfig(channel=c) for c in alice_channels],
        bob_channels=[ChannelConfig(channel=c) for c in bob_channels],
        **kwargs,
    )


def test_start_configures_and_starts() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.start()
    assert controller.config.live_acquisition is True
    assert controller._configured is True


def test_start_does_not_reconfigure_if_already_configured() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.configure()
    calls = []
    controller.configure = lambda: calls.append(True)  # type: ignore[method-assign]
    controller.start()
    assert calls == []


def test_stop_clears_live_flag() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.start()
    controller.stop()
    assert controller.config.live_acquisition is False


def test_stop_without_start_does_not_raise() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.stop()
    assert controller.config.live_acquisition is False


def test_poll_populates_state() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.start()
    state = controller.poll()
    assert state.counter_data is not None
    assert state.corr_data is not None
    assert state.countrate_data is not None
    assert state.total_counts_data is not None


@pytest.mark.parametrize(
    ("alice_channels", "bob_channels", "expected_coincidence_labels"),
    [
        pytest.param([1], [2], ["coin 1×2"], id="single-single"),
        pytest.param(
            [1, 2],
            [3, 4],
            ["coin 1×3", "coin 1×4", "coin 2×3", "coin 2×4"],
            id="double-double",
        ),
        pytest.param(
            [1, 2, 5],
            [3],
            ["coin 1×3", "coin 2×3", "coin 5×3"],
            id="triple-single",
        ),
    ],
)
def test_configure_labels_singles_then_coincidence_channels(
    alice_channels: list[int], bob_channels: list[int], expected_coincidence_labels: list[str]
) -> None:
    """setup_countrates() must cover the coincidence (virtual) channels
    alongside the singles, so a live coincidence rate is recorded, not
    just the per-detector rates."""
    config = make_config(alice_channels, bob_channels)
    controller = MeasurementController(SimulatorAdapter(seed=0), config)
    controller.configure()
    state = controller.poll()

    n_singles = len(alice_channels) + len(bob_channels)
    n_coincidences = len(alice_channels) * len(bob_channels)
    assert len(state.countrate_labels) == n_singles + n_coincidences
    assert state.countrate_data.shape[0] == len(state.countrate_labels)
    assert state.total_counts_data.shape[0] == len(state.countrate_labels)

    singles_labels = [f"ch {c}" for c in (*alice_channels, *bob_channels)]
    assert state.countrate_labels == singles_labels + expected_coincidence_labels


@pytest.mark.parametrize(
    "delays_ns",
    [
        pytest.param([0.0, 0.0, 0.0, 0.0], id="no-delay"),
        pytest.param([1.5, -2.0, 0.0, 10.25], id="mixed-delays"),
    ],
)
def test_configure_pushes_per_channel_delay_to_the_adapter(delays_ns: list[float]) -> None:
    alice = [
        ChannelConfig(channel=1, delay_ns=delays_ns[0]),
        ChannelConfig(channel=2, delay_ns=delays_ns[1]),
    ]
    bob = [
        ChannelConfig(channel=3, delay_ns=delays_ns[2]),
        ChannelConfig(channel=4, delay_ns=delays_ns[3]),
    ]
    config = MeasurementConfig(alice_channels=alice, bob_channels=bob)
    adapter = SimulatorAdapter(seed=0)
    controller = MeasurementController(adapter, config)
    controller.configure()

    for channel, expected_delay in zip((1, 2, 3, 4), delays_ns, strict=True):
        assert adapter._channel_delay_ns[channel] == expected_delay


def test_evaluate_bell_sets_state() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    flat = np.arange(1, 17, dtype=float)
    controller.evaluate_bell(flat)
    assert controller.state.bell_e is not None
    assert controller.state.bell_s is not None


@pytest.mark.parametrize(
    "flat_counts",
    [
        pytest.param(np.arange(1, 17, dtype=float), id="ascending"),
        pytest.param(np.ones(16), id="uniform"),
        pytest.param(np.zeros(16), id="all-zero"),
    ],
)
def test_evaluate_bell_matches_calc_e_s_directly(flat_counts: np.ndarray) -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    controller.evaluate_bell(flat_counts)
    expected_e, expected_s = calc_e_s(coincidence_matrix_from_counts(flat_counts))
    np.testing.assert_allclose(controller.state.bell_e, expected_e)
    np.testing.assert_allclose(controller.state.bell_s, expected_s)


def test_evaluate_bell_propagates_wrong_sized_input_error() -> None:
    controller = MeasurementController(SimulatorAdapter(seed=0), make_config())
    with pytest.raises(ValueError, match="expected 16 values"):
        controller.evaluate_bell(np.arange(10, dtype=float))
