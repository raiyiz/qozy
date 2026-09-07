import numpy as np

from qozy.core.scan_controller import LiveBellScan, ScanConfig
from qozy.hardware.simulator import SimulatorAdapter, SimulatorStage


def test_live_bell_scan_updates_cells_from_shared_totals() -> None:
    adapter = SimulatorAdapter(seed=0)
    adapter.connect()
    adapter.setup_countrates([1, 2, 3, 4, 0, 1, 2, 3])
    scan = LiveBellScan(
        adapter,
        SimulatorStage(),
        SimulatorStage(),
        [1, 2],
        [3, 4],
        config=ScanConfig(settings_deg=(0.0, 1.0, 2.0, 3.0), integration_time_s=0.0),
    )

    scan.start(adapter.get_total_counts())
    completed = []
    for _ in range(16):
        row, col, value, done = scan.update(adapter.get_total_counts())
        completed.append((row, col, value, done))

    assert completed[-1][3] is True
    assert scan.done
    assert scan.matrix.shape == (4, 4)
    assert np.all(scan.matrix > 0)
