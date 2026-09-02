import numpy as np


def generate_synthetic_channels(time_axis: np.ndarray, phase: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Generate a simple synthetic SPDC-like signal triplet for plotting and testing."""
    alice = 1000 + 500 * np.cos(np.deg2rad(time_axis * 1.5 - 22.5)) ** 2
    bob = 950 + 450 * np.cos(np.deg2rad(time_axis * 1.2 + 45.0)) ** 2
    coin = 110 + 90 * np.exp(-((time_axis - 45.0) / 16.0) ** 2) + 40 * np.sin(time_axis / 12.0 + phase)

    alice += 80 * np.sin(time_axis / 15.0 + phase)
    bob += 70 * np.cos(time_axis / 18.0 + phase * 0.7)
    return alice, bob, coin
