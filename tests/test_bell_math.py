"""Tests for qozy.core.bell_math: coincidence_matrix_from_counts and calc_e_s."""

from __future__ import annotations

import numpy as np
import pytest

from qozy.core.bell_math import (
    BELL_ANGLES_DEG,
    POLARIZATION_LABELS,
    calc_e_s,
    coincidence_matrix_from_counts,
)


def test_polarization_labels_are_the_four_bell_settings() -> None:
    assert POLARIZATION_LABELS == ("V", "H", "D", "A")


def test_bell_angles_are_the_four_chsh_degrees() -> None:
    assert BELL_ANGLES_DEG == (22.5, 67.5, 112.5, 157.5)


# --- coincidence_matrix_from_counts ---------------------------------------


def test_coincidence_matrix_from_counts_reshapes_row_major() -> None:
    data = np.arange(16, dtype=float)
    matrix = coincidence_matrix_from_counts(data)
    assert matrix.shape == (4, 4)
    np.testing.assert_allclose(matrix, data.reshape(4, 4))


def test_coincidence_matrix_from_counts_accepts_a_plain_list() -> None:
    matrix = coincidence_matrix_from_counts(list(range(16)))
    assert matrix.shape == (4, 4)
    assert matrix.dtype == float


def test_coincidence_matrix_from_counts_does_not_mutate_input() -> None:
    data = np.arange(16, dtype=float)
    original = data.copy()
    coincidence_matrix_from_counts(data)
    np.testing.assert_array_equal(data, original)


@pytest.mark.parametrize(
    "size",
    [
        pytest.param(0, id="empty"),
        pytest.param(1, id="one-value"),
        pytest.param(4, id="four-values"),
        pytest.param(15, id="one-short"),
        pytest.param(17, id="one-over"),
        pytest.param(32, id="double"),
    ],
)
def test_coincidence_matrix_from_counts_rejects_wrong_size(size: int) -> None:
    with pytest.raises(ValueError, match="expected 16 values"):
        coincidence_matrix_from_counts(np.arange(size))


# --- calc_e_s: known-matrix cases ------------------------------------------
#
# Chosen to cover a physically meaningful spread of Bell scenarios rather
# than arbitrary numbers: flat/symmetric counts that must cancel to exactly
# zero, a maximally-correlated case, and the PR-box (the theoretical
# maximum-violation case, |S|=4, above what any real quantum experiment can
# reach — a useful bound to pin down in a test).

_UNIFORM = np.ones((4, 4))
_ASCENDING = np.arange(1, 17, dtype=float).reshape(4, 4)
_QKD_LIKE = np.array(
    [
        [0, 0.5, 0.25, 0.25],
        [0.5, 0, 0.25, 0.25],
        [0.25, 0.25, 0, 0.5],
        [0.25, 0.25, 0.5, 0],
    ]
)
_PR_BOX = np.array(
    [
        [0, 1, 0, 1],
        [1, 0, 1, 0],
        [1, 0, 0, 1],
        [0, 1, 1, 0],
    ]
)
_NOISY_COUNTS = np.array(
    [
        [100, 20, 40, 10],
        [15, 90, 12, 35],
        [42, 8, 96, 18],
        [6, 25, 14, 110],
    ]
)


@pytest.mark.parametrize(
    ("matrix", "expected_e", "expected_s"),
    [
        pytest.param(_UNIFORM, [0, 0, 0, 0], [0, 0, 0, 0], id="uniform-counts-cancel-to-zero"),
        pytest.param(_ASCENDING, [0, 0, 0, 0], [0, 0, 0, 0], id="ascending-counts-cancel-to-zero"),
        pytest.param(_QKD_LIKE, [-1, 0, 0, -1], [0, -2, -2, 0], id="qkd-like-anti-correlated"),
        pytest.param(_PR_BOX, [-1, -1, 1, -1], [0, 0, -4, 0], id="pr-box-maximum-violation"),
    ],
)
def test_calc_e_s_known_matrices(
    matrix: np.ndarray, expected_e: list[float], expected_s: list[float]
) -> None:
    e, s = calc_e_s(matrix)
    np.testing.assert_allclose(e, expected_e)
    np.testing.assert_allclose(s, expected_s)


def test_calc_e_s_returns_finite_correctly_shaped_arrays() -> None:
    e, s = calc_e_s(_NOISY_COUNTS)
    assert e.shape == (4,)
    assert s.shape == (4,)
    assert np.all(np.isfinite(e))
    assert np.all(np.isfinite(s))


def test_calc_e_s_correlation_values_stay_within_plus_minus_one() -> None:
    """Each E is a normalized difference of counts, so no input can push it
    outside [-1, 1] regardless of scale or imbalance."""
    e, _s = calc_e_s(_NOISY_COUNTS)
    assert np.all(np.abs(e) <= 1.0)


@pytest.mark.parametrize(
    "scale",
    [
        pytest.param(0.001, id="tiny"),
        pytest.param(1, id="unscaled"),
        pytest.param(7, id="small-multiple"),
        pytest.param(1000, id="large-multiple"),
    ],
)
def test_calc_e_s_is_invariant_to_overall_count_scale(scale: float) -> None:
    """E/S are ratios of counts, so multiplying every count by the same
    positive factor (e.g. a longer integration time) must not change the
    result."""
    e_base, s_base = calc_e_s(_NOISY_COUNTS)
    e_scaled, s_scaled = calc_e_s(_NOISY_COUNTS * scale)
    np.testing.assert_allclose(e_scaled, e_base)
    np.testing.assert_allclose(s_scaled, s_base)


def test_calc_e_s_rounds_to_two_decimal_places() -> None:
    matrix = np.array(
        [
            [1, 3, 5, 7],
            [2, 4, 6, 8],
            [9, 11, 13, 15],
            [10, 12, 14, 16],
        ],
        dtype=float,
    )
    e, s = calc_e_s(matrix)
    np.testing.assert_allclose(e, np.round(e, 2))
    np.testing.assert_allclose(s, np.round(s, 2))


def test_calc_e_s_does_not_mutate_input() -> None:
    matrix = _NOISY_COUNTS.copy()
    original = matrix.copy()
    calc_e_s(matrix)
    np.testing.assert_array_equal(matrix, original)


@pytest.mark.parametrize(
    "matrix",
    [
        pytest.param(np.zeros((4, 4)), id="all-zero"),
        pytest.param(
            np.array(
                [
                    [0, 5, 3, 2],
                    [4, 0, 1, 6],
                    [2, 3, 0, 5],
                    [1, 4, 6, 0],
                ],
                dtype=float,
            ),
            id="zero-diagonal-only",
        ),
    ],
)
def test_calc_e_s_handles_zero_counts_without_error(matrix: np.ndarray) -> None:
    e, s = calc_e_s(matrix)
    assert np.all(np.isfinite(e))
    assert np.all(np.isfinite(s))


@pytest.mark.parametrize(
    "shape",
    [
        pytest.param((3, 4), id="too-few-rows"),
        pytest.param((4, 3), id="too-few-columns"),
        pytest.param((16,), id="flat-not-reshaped"),
    ],
)
def test_calc_e_s_rejects_matrices_too_small_for_4x4_indexing(shape: tuple[int, ...]) -> None:
    with pytest.raises(IndexError):
        calc_e_s(np.zeros(shape))
