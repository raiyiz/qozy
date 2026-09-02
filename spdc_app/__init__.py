"""SPDC application package."""

from .bell_math import calc_e_s, coincidence_matrix_from_counts
from .simulator import generate_synthetic_channels

__all__ = [
    "calc_e_s",
    "coincidence_matrix_from_counts",
    "generate_synthetic_channels",
]
