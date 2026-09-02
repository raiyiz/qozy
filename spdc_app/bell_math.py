import numpy as np


def calc_e_s(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute the Bell correlation coefficients and the S-values for a 4x4 matrix."""
    matrix = np.asarray(matrix, dtype=float)
    if matrix.shape != (4, 4):
        raise ValueError(f"Expected a 4x4 matrix, got shape {matrix.shape}")

    matrix[matrix == 0] = 1e-20

    e1 = ((matrix[0, 0] + matrix[1, 1]) - (matrix[0, 1] + matrix[1, 0])) / (
        (matrix[0, 0] + matrix[1, 1]) + (matrix[0, 1] + matrix[1, 0])
    )
    e2 = ((matrix[0, 2] + matrix[1, 3]) - (matrix[0, 3] + matrix[1, 2])) / (
        (matrix[0, 2] + matrix[1, 3]) + (matrix[0, 3] + matrix[1, 2])
    )
    e3 = ((matrix[2, 0] + matrix[3, 1]) - (matrix[2, 1] + matrix[3, 0])) / (
        (matrix[2, 0] + matrix[3, 1]) + (matrix[2, 1] + matrix[3, 0])
    )
    e4 = ((matrix[2, 2] + matrix[3, 3]) - (matrix[2, 3] + matrix[3, 2])) / (
        (matrix[2, 2] + matrix[3, 3]) + (matrix[2, 3] + matrix[3, 2])
    )

    e = np.round([e1, e2, e3, e4], 2)
    s = np.round(
        [
            -e1 + e2 + e3 + e4,
            e1 - e2 + e3 + e4,
            e1 + e2 - e3 + e4,
            e1 + e2 + e3 - e4,
        ],
        2,
    )
    return e, s


def coincidence_matrix_from_counts(counts: np.ndarray) -> np.ndarray:
    """Build a 4x4 coincidence matrix from a flat counts array."""
    counts = np.asarray(counts, dtype=float)
    if counts.size == 0:
        return np.zeros((4, 4), dtype=float)

    if counts.size < 16:
        padded = np.zeros(16, dtype=float)
        padded[: counts.size] = counts
        counts = padded

    matrix = counts.reshape(4, 4)
    return matrix
