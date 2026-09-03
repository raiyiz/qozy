import numpy as np

from spdc_app.bell_math import calc_e_s, coincidence_matrix_from_counts


def test_coincidence_matrix_from_counts_respects_shape() -> None:
    data = np.arange(16, dtype=float)
    matrix = coincidence_matrix_from_counts(data)
    assert matrix.shape == (4, 4)
    np.testing.assert_allclose(matrix, data.reshape(4, 4))


def test_calc_e_s_returns_expected_values() -> None:
    matrix = np.array(
        [
            [100, 20, 40, 10],
            [15, 90, 12, 35],
            [42, 8, 96, 18],
            [6, 25, 14, 110],
        ],
        dtype=float,
    )
    e, s = calc_e_s(matrix)
    assert e.shape == (4,)
    assert s.shape == (4,)
    assert np.all(np.isfinite(e))
    assert np.all(np.isfinite(s))
