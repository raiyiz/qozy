import numpy as np


def generate_signal(x: np.ndarray, phase: float, amplitude: float, decay: float) -> np.ndarray:
    return amplitude * np.sin(x + phase) * np.exp(-x / decay)
