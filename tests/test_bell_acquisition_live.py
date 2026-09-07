"""Tests for the shared live Bell acquisition strategies."""

from __future__ import annotations

import numpy as np

from qozy.core.bell_acquisition import (
    BellAcquisitionMode,
    BellAcquisitionOptions,
    BellChannelMap,
    BellMatrixAccumulator,
    SimultaneousBellAcquisition,
)


def test_options_expose_explicit_acquisition_modes() -> None:
    assert BellAcquisitionOptions().mode is BellAcquisitionMode.SEQUENTIAL
    assert BellAcquisitionOptions(mode=BellAcquisitionMode.SIMULTANEOUS).mode is BellAcquisitionMode.SIMULTANEOUS


def test_accumulator_keeps_raw_counts_separate_from_normalized_display() -> None:
    accumulator = BellMatrixAccumulator()
    accumulator.update_cell(0, 0, 25)
    accumulator.update_cell(1, 1, 50)

    np.testing.assert_allclose(accumulator.normalized_matrix()[0, 0], 0.5)
    np.testing.assert_allclose(accumulator.normalized_matrix()[1, 1], 1.0)
    assert accumulator.matrix[0, 0] == 25
    assert accumulator.matrix[1, 1] == 50


def test_partial_matrix_only_marks_measured_cells() -> None:
    accumulator = BellMatrixAccumulator()
    accumulator.update_cell(0, 0, 10)
    accumulator.update_cell(0, 1, 20)

    assert accumulator.filled[0, 0]
    assert accumulator.filled[0, 1]
    assert not accumulator.filled[1, 0]
    assert not accumulator.e_readiness().any()


def test_row_major_channel_map_can_represent_partial_parallel_hardware() -> None:
    mapping = BellChannelMap.row_major(6)
    assert mapping.coincidence_indices[(0, 0)] == 0
    assert mapping.coincidence_indices[(1, 1)] == 5
    assert len(mapping.cells) == 6


def test_simultaneous_acquisition_updates_all_mapped_cells_each_poll() -> None:
    acquisition = SimultaneousBellAcquisition(BellChannelMap.row_major(16), coincidence_offset=2)
    first = np.arange(18, dtype=float)
    second = first + np.arange(18, dtype=float) + 1

    update = acquisition.start(first)
    assert not update.done
    np.testing.assert_array_equal(acquisition.matrix.matrix, first[2:].reshape(4, 4))

    acquisition.update(second)
    np.testing.assert_array_equal(acquisition.matrix.matrix, second[2:].reshape(4, 4))
    assert acquisition.matrix.filled.all()


def test_simultaneous_acquisition_preserves_unmapped_cells() -> None:
    acquisition = SimultaneousBellAcquisition(BellChannelMap.row_major(4), coincidence_offset=1)
    acquisition.start(np.array([0, 10, 20, 30, 40], dtype=float))

    assert acquisition.matrix.filled[:1, :].all()
    assert not acquisition.matrix.filled[1:, :].any()
