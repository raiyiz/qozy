"""Tests for shared Bell acquisition state."""

from __future__ import annotations

import numpy as np
import pytest

from qozy.core.bell_acquisition import (
    BellAcquisitionMode,
    BellAcquisitionOptions,
    BellChannelMap,
    BellMatrixAccumulator,
    SequentialBellAcquisition,
    SimultaneousBellAcquisition,
)


def test_default_bell_acquisition_options_are_sequential() -> None:
    options = BellAcquisitionOptions()
    assert options.mode is BellAcquisitionMode.SEQUENTIAL
    assert options.integration_time_s == 0.5


def test_accumulator_updates_one_cell_and_marks_it_filled() -> None:
    accumulator = BellMatrixAccumulator()
    accumulator.update_cell(1, 2, 42.5)

    assert accumulator.matrix[1, 2] == 42.5
    assert accumulator.filled[1, 2]
    assert accumulator.e_readiness().tolist() == [False, False, False, False]


def test_accumulator_reset_clears_counts_and_filled_mask() -> None:
    accumulator = BellMatrixAccumulator()
    accumulator.update_cell(0, 0, 10)
    accumulator.reset()

    np.testing.assert_array_equal(accumulator.matrix, np.zeros((4, 4)))
    assert not accumulator.filled.any()


def test_accumulator_normalization_is_display_only() -> None:
    accumulator = BellMatrixAccumulator()
    accumulator.update_cell(0, 0, 25)
    accumulator.update_cell(1, 1, 50)

    normalized = accumulator.normalized_matrix()

    np.testing.assert_allclose(normalized[0, 0], 0.5)
    np.testing.assert_allclose(normalized[1, 1], 1.0)
    assert accumulator.matrix[0, 0] == 25
    assert accumulator.matrix[1, 1] == 50


def test_accumulator_normalization_ignores_unmeasured_placeholder_values() -> None:
    accumulator = BellMatrixAccumulator()
    accumulator.matrix[3, 3] = 1000
    accumulator.update_cell(0, 0, 10)

    normalized = accumulator.normalized_matrix()

    assert normalized[0, 0] == 1.0
    assert normalized[3, 3] == 100.0


def test_accumulator_update_matrix_can_keep_partial_mask() -> None:
    accumulator = BellMatrixAccumulator()
    matrix = np.arange(16, dtype=float).reshape(4, 4)
    filled = np.zeros((4, 4), dtype=bool)
    filled[0, 0] = True

    accumulator.update_matrix(matrix, filled)

    np.testing.assert_array_equal(accumulator.matrix, matrix)
    np.testing.assert_array_equal(accumulator.filled, filled)
    assert accumulator.e_readiness().tolist() == [False, False, False, False]


def test_channel_map_row_major_supports_partial_mapping() -> None:
    mapping = BellChannelMap.row_major(6)

    assert mapping.coincidence_indices[(0, 0)] == 0
    assert mapping.coincidence_indices[(1, 1)] == 5
    assert len(mapping.cells) == 6


@pytest.mark.parametrize("count", [-1, 17])
def test_channel_map_row_major_rejects_invalid_count(count: int) -> None:
    with pytest.raises(ValueError, match="between 0 and 16"):
        BellChannelMap.row_major(count)


def test_channel_map_rejects_invalid_cell() -> None:
    with pytest.raises(ValueError, match="invalid Bell matrix cell"):
        BellChannelMap({(4, 0): 0})


def test_simultaneous_acquisition_updates_all_mapped_cells() -> None:
    mapping = BellChannelMap.row_major(16)
    acquisition = SimultaneousBellAcquisition(mapping, coincidence_offset=2)
    totals = np.arange(18, dtype=float)

    acquisition.start(totals)

    expected = np.arange(16, dtype=float).reshape(4, 4) + 2
    np.testing.assert_array_equal(acquisition.matrix.matrix, expected)
    assert acquisition.matrix.filled.all()
    assert not acquisition.done


def test_simultaneous_acquisition_updates_again_from_cumulative_totals() -> None:
    mapping = BellChannelMap.row_major(2)
    acquisition = SimultaneousBellAcquisition(mapping, coincidence_offset=1)
    acquisition.start(np.array([0, 10, 20], dtype=float))
    acquisition.update(np.array([0, 15, 25], dtype=float))

    assert acquisition.matrix.matrix[0, 0] == 15
    assert acquisition.matrix.matrix[0, 1] == 25


def test_simultaneous_acquisition_rejects_missing_configured_channel() -> None:
    mapping = BellChannelMap.row_major(2)
    acquisition = SimultaneousBellAcquisition(mapping, coincidence_offset=1)

    with pytest.raises(ValueError, match="requires all configured coincidence channels"):
        acquisition.start(np.array([0, 10], dtype=float))


class _FakeStage:
    def __init__(self) -> None:
        self.angles: list[float] = []

    def set_angle(self, angle: float) -> None:
        self.angles.append(angle)


class _FakeAdapter:
    def __init__(self) -> None:
        self.total_counts = np.zeros(18, dtype=float)
        self.contexts: list[tuple[float, float]] = []

    def get_total_counts(self) -> np.ndarray:
        return self.total_counts.copy()

    def set_angle_context(self, alice: float, bob: float) -> None:
        self.contexts.append((alice, bob))


def test_sequential_acquisition_starts_at_first_setting_and_updates_live(monkeypatch) -> None:
    import qozy.core.bell_acquisition as bell_acquisition

    clock = iter([10.0, 10.1, 10.2])
    monkeypatch.setattr(bell_acquisition.time, "monotonic", lambda: next(clock))

    adapter = _FakeAdapter()
    alice = _FakeStage()
    bob = _FakeStage()
    acquisition = SequentialBellAcquisition(
        adapter,
        alice,
        bob,
        [0],
        [1],
        integration_time_s=1.0,
    )

    acquisition.start(np.zeros(18))
    assert alice.angles == [22.5]
    assert bob.angles == [22.5]

    adapter.total_counts[2:] = 7
    row, col, value, done = acquisition.update(adapter.total_counts)

    assert (row, col) == (0, 0)
    assert value == 112.0
    assert not done
    assert acquisition.matrix.filled[0, 0]
    assert acquisition.state.completed_cells == 0
