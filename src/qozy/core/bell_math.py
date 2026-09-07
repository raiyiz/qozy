"""Bell-inequality math.

Ported from ``old_spdc_to_port/spdc/bellvalue.py``. The plotting/table code
that used to live alongside ``calc_e_s`` has been split out (see
``qozy.gui`` for anything that touches matplotlib/Qt) so this module stays a
pure numpy function that is trivial to unit test.
"""

from __future__ import annotations

import numpy as np

# Order the four polarization settings are expected in a flat 16-value
# coincidence readout, before being reshaped into a 4x4 matrix.
POLARIZATION_LABELS = ("V", "H", "D", "A")

# Bob detector angles (degrees) used to build the 4x4 coincidence matrix
# for a standard CHSH-style Bell measurement.
BELL_ANGLES_DEG = (22.5, 67.5, 112.5, 157.5)


# Which 2x2 block of the coincidence matrix each E value is computed from
# (see calc_e_s below) -- shared with e_readiness so a live/partial
# computation stays honest about what's actually been measured yet.
_E_BLOCKS = (
    (slice(0, 2), slice(0, 2)),
    (slice(0, 2), slice(2, 4)),
    (slice(2, 4), slice(0, 2)),
    (slice(2, 4), slice(2, 4)),
)


def coincidence_matrix_from_counts(data: np.ndarray) -> np.ndarray:
    """Reshape a flat 16-value coincidence readout into a 4x4 matrix.

    ``data`` is expected in row-major order: four rows (one per Alice/Bob
    polarization combination axis), four columns each.
    """
    data = np.asarray(data, dtype=float)
    if data.size != 16:
        raise ValueError(f"expected 16 values, got {data.size}")
    return data.reshape(4, 4)


def calc_e_s(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute the four CHSH correlation values E and the four Bell sums S.

    ``matrix`` is a 4x4 coincidence-count matrix. Zero counts are treated as
    a tiny epsilon to avoid division by zero, matching the original
    behavior. The input matrix is never mutated.
    """
    m = np.asarray(matrix, dtype=float).copy()
    m[m == 0] = 1e-20

    e1 = ((m[0][0] + m[1][1]) - (m[0][1] + m[1][0])) / ((m[0][0] + m[1][1]) + (m[0][1] + m[1][0]))
    e2 = ((m[0][2] + m[1][3]) - (m[0][3] + m[1][2])) / ((m[0][2] + m[1][3]) + (m[0][3] + m[1][2]))
    e3 = ((m[2][0] + m[3][1]) - (m[2][1] + m[3][0])) / ((m[2][0] + m[3][1]) + (m[2][1] + m[3][0]))
    e4 = ((m[2][2] + m[3][3]) - (m[2][3] + m[3][2])) / ((m[2][2] + m[3][3]) + (m[2][3] + m[3][2]))

    e = np.round([e1, e2, e3, e4], 2)
    s = np.round(
        [-e1 + e2 + e3 + e4, e1 - e2 + e3 + e4, e1 + e2 - e3 + e4, e1 + e2 + e3 - e4],
        2,
    )
    return e, s


def e_readiness(filled: np.ndarray) -> np.ndarray:
    """Which of the four E values calc_e_s would return are actually
    backed by real measurements yet, given ``filled`` — a 4x4 boolean mask
    of which coincidence-matrix cells have a real recorded count (as
    opposed to a live scan's not-yet-measured placeholder).

    Lets a live/partial computation stay honest: E_i only counts as ready
    once every cell in its 2x2 block (see ``_E_BLOCKS``, matching
    ``calc_e_s``'s own indexing) has been measured, rather than treating
    an unmeasured cell as if it were a genuine zero-count reading. None of
    the four S values are derivable until all four E values are — each S
    combines all of them — so ``s_ready = bool(e_readiness(filled).all())``
    is the corresponding check for S.
    """
    filled = np.asarray(filled, dtype=bool)
    return np.array([bool(filled[rows, cols].all()) for rows, cols in _E_BLOCKS])
