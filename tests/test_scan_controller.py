"""Tests for qozy.core.scan_controller.BellScanController."""

from __future__ import annotations

import numpy as np
import pytest

from qozy.core.bell_math import calc_e_s
from qozy.core.scan_controller import BellScanController, ScanConfig
from qozy.hardware.simulator import SimulatorAdapter, SimulatorStage


def make_scan(
    *,
    alice_channels: list[int] | None = None,
    bob_channels: list[int] | None = None,
    config: ScanConfig | None = None,
    seed: int = 0,
    **kwargs,
) -> BellScanController:
    return BellScanController(
        SimulatorAdapter(seed=seed),
        SimulatorStage(),
        SimulatorStage(),
        alice_channels=alice_channels if alice_channels is not None else [1],
        bob_channels=bob_channels if bob_channels is not None else [2],
        config=config or ScanConfig(integration_time_s=0.01),
        **kwargs,
    )


def test_run_produces_full_4x4_matrix() -> None:
    scan = make_scan()
    matrix = scan.run()
    assert matrix.shape == (4, 4)
    assert np.all(np.isfinite(matrix))
    assert np.all(matrix > 0)


def test_run_without_a_callback_still_completes() -> None:
    """on_cell_done is optional -- must not be required."""
    scan = make_scan()
    matrix = scan.run()
    assert matrix.shape == (4, 4)


def test_run_calls_on_cell_done_for_all_16_settings() -> None:
    scan = make_scan()
    seen = []
    scan.run(on_cell_done=lambda r, c, v: seen.append((r, c)))
    assert len(seen) == 16
    assert set(seen) == {(r, c) for r in range(4) for c in range(4)}


def test_on_cell_done_values_match_the_final_matrix() -> None:
    scan = make_scan()
    seen: dict[tuple[int, int], float] = {}
    matrix = scan.run(on_cell_done=lambda r, c, v: seen.__setitem__((r, c), v))
    assert len(seen) == 16
    for (row, col), value in seen.items():
        assert value == matrix[row, col]


@pytest.mark.parametrize(
    ("alice_channels", "bob_channels"),
    [
        pytest.param([1], [2], id="single-single"),
        pytest.param([1, 2], [3, 4], id="double-double"),
        pytest.param([1, 2, 5], [3], id="triple-single"),
    ],
)
def test_run_registers_one_countrate_channel_per_combination(
    alice_channels: list[int], bob_channels: list[int]
) -> None:
    scan = make_scan(alice_channels=alice_channels, bob_channels=bob_channels)
    scan.run()
    assert len(scan.adapter._countrate_channels) == len(alice_channels) * len(bob_channels)


@pytest.mark.parametrize("seed", [0, 1, 42])
def test_run_is_reproducible_for_a_given_seed(seed: int) -> None:
    """Same seed -> same simulated matrix, so a flaky-looking scan test
    would point at a real bug, not just simulator noise."""
    matrix_a = make_scan(seed=seed).run()
    matrix_b = make_scan(seed=seed).run()
    np.testing.assert_array_equal(matrix_a, matrix_b)


@pytest.mark.parametrize(
    "settings_deg",
    [
        pytest.param((22.5, 67.5, 112.5, 157.5), id="default-bell-angles"),
        pytest.param((0.0, 45.0, 90.0, 135.0), id="custom-angles"),
        pytest.param((157.5, 112.5, 67.5, 22.5), id="reversed-order"),
    ],
)
def test_stages_end_at_last_setting(settings_deg: tuple[float, ...]) -> None:
    scan = make_scan(config=ScanConfig(settings_deg=settings_deg, integration_time_s=0.01))
    scan.run()
    assert scan.alice_stage.get_angle() == settings_deg[-1]
    assert scan.bob_stage.get_angle() == settings_deg[-1]


def test_stages_visit_every_setting_in_the_expected_pattern() -> None:
    """Alice steps once per outer setting; Bob cycles through all four
    settings once per Alice setting -- worth pinning down explicitly, not
    just checking where the stages end up."""
    scan = make_scan()
    settings = scan.config.settings_deg
    alice_angles_seen: list[float] = []
    bob_angles_seen: list[float] = []
    original_alice_set = scan.alice_stage.set_angle
    original_bob_set = scan.bob_stage.set_angle

    def spy_alice(angle: float) -> float:
        alice_angles_seen.append(angle)
        return original_alice_set(angle)

    def spy_bob(angle: float) -> float:
        bob_angles_seen.append(angle)
        return original_bob_set(angle)

    scan.alice_stage.set_angle = spy_alice
    scan.bob_stage.set_angle = spy_bob
    scan.run()

    assert alice_angles_seen == list(settings)
    assert bob_angles_seen == list(settings) * len(settings)


@pytest.mark.parametrize("integration_time_s", [0.0, 0.001, 0.01, 1.0])
def test_run_completes_for_a_range_of_integration_times(integration_time_s: float) -> None:
    """The simulator doesn't actually block for integration_time_s, but a
    real adapter would -- this guards against the value being used in a
    way that breaks for edge cases like zero."""
    scan = make_scan(config=ScanConfig(integration_time_s=integration_time_s))
    matrix = scan.run()
    assert np.all(np.isfinite(matrix))


def test_stop_sm_is_called_even_if_a_measurement_raises() -> None:
    """finally: self.adapter.stop_sm() must run even on failure, so a
    failed scan doesn't leave the acquisition state machine running."""
    scan = make_scan()

    def boom(_time_frame_s: float) -> None:
        raise RuntimeError("simulated hardware fault")

    scan.adapter.measure_for_sm = boom
    stopped = []
    scan.adapter.stop_sm = lambda: stopped.append(True)

    with pytest.raises(RuntimeError, match="simulated hardware fault"):
        scan.run()

    assert stopped == [True]


def test_evaluate_matches_calc_e_s_on_the_scanned_matrix() -> None:
    scan = make_scan()
    scan.run()
    e, s = scan.evaluate()
    expected_e, expected_s = calc_e_s(scan.matrix)
    np.testing.assert_allclose(e, expected_e)
    np.testing.assert_allclose(s, expected_s)


def test_evaluate_before_run_uses_the_zero_initial_matrix() -> None:
    scan = make_scan()
    e, s = scan.evaluate()
    expected_e, expected_s = calc_e_s(np.zeros((4, 4)))
    np.testing.assert_allclose(e, expected_e)
    np.testing.assert_allclose(s, expected_s)
