import numpy as np

from qozy.core.scan_controller import BellScanController, ScanConfig
from qozy.hardware.simulator import SimulatorAdapter, SimulatorStage


def make_scan(**kwargs) -> BellScanController:
    return BellScanController(
        SimulatorAdapter(seed=0),
        SimulatorStage(),
        SimulatorStage(),
        alice_channels=[1],
        bob_channels=[2],
        config=ScanConfig(integration_time_s=0.01),
        **kwargs,
    )


def test_run_produces_full_4x4_matrix() -> None:
    scan = make_scan()
    matrix = scan.run()
    assert matrix.shape == (4, 4)
    assert np.all(np.isfinite(matrix))
    assert np.all(matrix > 0)


def test_run_calls_on_cell_done_for_all_16_settings() -> None:
    scan = make_scan()
    seen = []
    scan.run(on_cell_done=lambda r, c, v: seen.append((r, c)))
    assert len(seen) == 16
    assert set(seen) == {(r, c) for r in range(4) for c in range(4)}


def test_stages_end_at_last_setting() -> None:
    scan = make_scan()
    scan.run()
    assert scan.alice_stage.get_angle() == scan.config.settings_deg[-1]
    assert scan.bob_stage.get_angle() == scan.config.settings_deg[-1]


def test_evaluate_matches_calc_e_s_on_the_scanned_matrix() -> None:
    from qozy.core.bell_math import calc_e_s

    scan = make_scan()
    scan.run()
    e, s = scan.evaluate()
    expected_e, expected_s = calc_e_s(scan.matrix)
    np.testing.assert_allclose(e, expected_e)
    np.testing.assert_allclose(s, expected_s)
