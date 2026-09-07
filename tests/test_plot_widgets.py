"""Unit tests for the two plotting widgets: PlotPanel (VisPy live traces)
and BellMatrixPlot (matplotlib Bell-scan heatmap)."""

from __future__ import annotations

import numpy as np
import pytest

from qozy.gui.bell_matrix_plot import BellMatrixPlot
from qozy.gui.plot_panel import PlotPanel

# --- PlotPanel --------------------------------------------------------------


def test_set_traces_calls_set_range_without_an_explicit_y_range(qapp) -> None:
    """Previously set_range() was only ever called when the caller passed
    an explicit y_range -- which CountsPage never does -- so the camera
    stayed at its initial view forever while the data scrolled off to the
    right, looking like the curves were stuck "at the beginning"."""
    panel = PlotPanel()
    calls: list[dict] = []
    panel.view.camera.set_range = lambda **kwargs: calls.append(kwargs)

    t = np.linspace(1000, 1010, 50)
    panel.set_traces(t, alice=np.full(50, 5.0), bob=np.full(50, 3.0))

    assert len(calls) == 1
    x_min, x_max = calls[0]["x"]
    assert x_min < t[0]
    assert x_max > t[-1]


def test_set_traces_x_range_tracks_the_current_data_window(qapp) -> None:
    """The whole point: as t advances, the view must re-center on the new
    window rather than staying anchored near the first call's range."""
    panel = PlotPanel()
    calls: list[dict] = []
    panel.view.camera.set_range = lambda **kwargs: calls.append(kwargs)

    panel.set_traces(np.linspace(0, 10, 20))
    panel.set_traces(np.linspace(500, 510, 20))

    first_x, second_x = calls[0]["x"], calls[1]["x"]
    assert first_x != second_x
    assert second_x[0] > first_x[1]  # the new window is well past the old one


def test_set_traces_handles_empty_t_without_error(qapp) -> None:
    panel = PlotPanel()
    panel.set_traces(np.array([]))  # must not raise


def test_set_traces_handles_a_single_flat_sample_without_a_zero_width_range(qapp) -> None:
    panel = PlotPanel()
    calls: list[dict] = []
    panel.view.camera.set_range = lambda **kwargs: calls.append(kwargs)

    panel.set_traces(np.array([5.0]), alice=np.array([3.0]))

    x_min, x_max = calls[0]["x"]
    y_min, y_max = calls[0]["y"]
    assert x_min < x_max
    assert y_min < y_max


def test_set_traces_respects_an_explicit_y_range(qapp) -> None:
    panel = PlotPanel()
    calls: list[dict] = []
    panel.view.camera.set_range = lambda **kwargs: calls.append(kwargs)

    panel.set_traces(np.linspace(0, 10, 5), y_range=(-1.0, 1.0))

    assert calls[0]["y"] == (-1.0, 1.0)


# --- BellMatrixPlot -----------------------------------------------------


def _matrix() -> np.ndarray:
    return np.arange(1, 17, dtype=float).reshape(4, 4)


def test_update_matrix_defaults_filled_to_everything(qapp) -> None:
    plot = BellMatrixPlot()
    plot.update_matrix(_matrix())  # must not raise without a filled mask
    assert plot._ax.get_title() == "Scanning…  16/16 settings measured"


def test_update_matrix_partial_fill_shows_progress_not_e_s(qapp) -> None:
    plot = BellMatrixPlot()
    filled = np.zeros((4, 4), dtype=bool)
    filled[0, 0] = True
    filled[1, 2] = True

    plot.update_matrix(_matrix(), filled=filled)

    assert plot._ax.get_title() == "Scanning…  2/16 settings measured"


def test_update_matrix_full_fill_with_e_s_shows_chsh_values(qapp) -> None:
    plot = BellMatrixPlot()
    filled = np.ones((4, 4), dtype=bool)
    e = np.array([0.1, -0.2, 0.3, -0.4])
    s = np.array([1.0, -1.0, 2.0, -2.0])

    plot.update_matrix(_matrix(), filled=filled, e=e, s=s)

    title = plot._ax.get_title()
    assert "E1=0.10" in title
    assert "S4=-2.00" in title
    assert "Scanning" not in title


def test_update_matrix_color_scale_ignores_unfilled_cells(qapp) -> None:
    """The color scale must reflect only what's been measured so far, not
    a fixed/assumed range -- an unfilled cell defaulting to zero must not
    silently widen (or narrow) the scale as if it were a real reading."""
    matrix = np.zeros((4, 4))
    matrix[0, 0] = 100.0
    matrix[1, 1] = 10_000.0  # not yet "measured" -- must not affect scaling
    filled = np.zeros((4, 4), dtype=bool)
    filled[0, 0] = True

    plot = BellMatrixPlot()
    plot.update_matrix(matrix, filled=filled)

    image = plot._ax.get_images()[0]
    _vmin, vmax = image.get_clim()
    assert vmax < 10_000.0


def test_clear_resets_to_a_placeholder(qapp) -> None:
    plot = BellMatrixPlot()
    plot.update_matrix(_matrix(), filled=np.ones((4, 4), dtype=bool))
    plot.clear()
    assert plot._ax.get_title() == ""
    assert not plot._ax.get_images()


@pytest.mark.parametrize(
    ("n_filled_rc", "expected_count"),
    [
        pytest.param([], 0, id="none"),
        pytest.param([(0, 0)], 1, id="one"),
        pytest.param([(r, c) for r in range(4) for c in range(4)], 16, id="all"),
    ],
)
def test_update_matrix_progress_count_matches_filled_mask(
    qapp, n_filled_rc: list[tuple[int, int]], expected_count: int
) -> None:
    filled = np.zeros((4, 4), dtype=bool)
    for r, c in n_filled_rc:
        filled[r, c] = True

    plot = BellMatrixPlot()
    plot.update_matrix(_matrix(), filled=filled)

    if expected_count < 16:
        assert plot._ax.get_title() == f"Scanning…  {expected_count}/16 settings measured"
