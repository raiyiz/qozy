import numpy as np

from signal_utils import generate_signal


def test_generate_signal_matches_expected_formula() -> None:
    x = np.array([0.0, 1.0, 2.0, 3.0], dtype=float)
    phase = 0.5
    amplitude = 1.2
    decay = 10.0

    got = generate_signal(x, phase, amplitude, decay)
    expected = amplitude * np.sin(x + phase) * np.exp(-x / decay)

    np.testing.assert_allclose(got, expected, rtol=1e-12, atol=1e-12)


def test_generate_signal_respects_amplitude_zero() -> None:
    x = np.linspace(0.0, 5.0, 25)
    got = generate_signal(x, phase=0.0, amplitude=0.0, decay=8.0)
    np.testing.assert_allclose(got, np.zeros_like(x))
