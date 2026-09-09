"""Unit tests for the two plotting widgets: PlotPanel (VisPy live traces)
and BellMatrixPlot (matplotlib Bell-scan heatmap)."""

from __future__ import annotations

import numpy as np
import pytest

from qozy.gui.bell_history_plot import CLASSICAL_BOUND, TSIRELSON_BOUND, BellHistoryPlot
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


# --- BellHistoryPlot ---------------------------------------------------


def test_history_plot_starts_with_a_placeholder(qapp) -> None:
    plot = BellHistoryPlot()
    assert not plot._ax.lines
    assert plot._ax.get_title() == ""


def test_history_plot_update_with_empty_history_stays_a_placeholder(qapp) -> None:
    plot = BellHistoryPlot()
    plot.update_history([])
    assert not plot._ax.lines


def test_history_plot_draws_one_point_per_cycle(qapp) -> None:
    plot = BellHistoryPlot()
    plot.update_history([1.5, 1.8, 2.3])
    x_data, y_data = plot._ax.lines[-1].get_data()  # last line added is the data, not a bound
    np.testing.assert_array_equal(x_data, [1, 2, 3])
    np.testing.assert_allclose(y_data, [1.5, 1.8, 2.3])


def test_history_plot_title_reports_latest_cycle_and_value(qapp) -> None:
    plot = BellHistoryPlot()
    plot.update_history([1.5, 1.8, 2.3])
    assert plot._ax.get_title() == "cycle 3: max |S| = 2.30"


def test_history_plot_y_axis_always_shows_the_tsirelson_bound(qapp) -> None:
    """Even a low/early S value shouldn't hide the theoretical maximum --
    it's the reference point the graph exists to show progress toward."""
    plot = BellHistoryPlot()
    plot.update_history([0.1])
    _bottom, top = plot._ax.get_ylim()
    assert top > TSIRELSON_BOUND


def test_history_plot_reference_lines_at_classical_and_tsirelson_bounds(qapp) -> None:
    plot = BellHistoryPlot()
    plot.update_history([2.5])
    reference_y_values = {line.get_ydata()[0] for line in plot._ax.lines[:-1]}  # exclude data line
    assert CLASSICAL_BOUND in reference_y_values
    assert TSIRELSON_BOUND in reference_y_values


def test_history_plot_clear_resets_after_having_data(qapp) -> None:
    plot = BellHistoryPlot()
    plot.update_history([1.0, 2.0])
    plot.clear()
    assert not plot._ax.lines
    assert plot._ax.get_title() == ""


def test_bell_matrix_plot_canvas_size_is_fixed_across_updates(qapp) -> None:
    plot = BellMatrixPlot()
    size_before = (plot.canvas.width(), plot.canvas.height())
    plot.update_matrix(np.arange(1, 17, dtype=float).reshape(4, 4))
    plot.update_matrix(
        np.arange(1, 17, dtype=float).reshape(4, 4), e=np.zeros(4), s=np.zeros(4)
    )
    plot.clear()
    size_after = (plot.canvas.width(), plot.canvas.height())
    assert size_before == size_after


def test_history_plot_canvas_size_is_fixed_across_updates(qapp) -> None:
    plot = BellHistoryPlot()
    size_before = (plot.canvas.width(), plot.canvas.height())
    plot.update_history([1.5])
    plot.update_history([1.5, 1.9, 2.6, 2.1])
    size_after = (plot.canvas.width(), plot.canvas.height())
    assert size_before == size_after


def test_bell_matrix_plot_does_not_clear_axes_after_the_first_update(qapp) -> None:
    """The whole point of the incremental-update optimization: ax.clear()
    (which forces matplotlib to destroy and rebuild every artist) must
    only happen once, not on every one of up to 16 per-cycle calls."""
    plot = BellMatrixPlot()
    matrix = np.arange(1, 17, dtype=float).reshape(4, 4)
    plot.update_matrix(matrix)  # first call: builds the artists

    calls = []
    original_clear = plot._ax.clear
    plot._ax.clear = lambda: (calls.append(1), original_clear())[1]
    for _ in range(5):
        plot.update_matrix(matrix)
    assert calls == []


def test_history_plot_does_not_clear_axes_after_the_first_update(qapp) -> None:
    plot = BellHistoryPlot()
    plot.update_history([1.0])  # first call: builds the artists

    calls = []
    original_clear = plot._ax.clear
    plot._ax.clear = lambda: (calls.append(1), original_clear())[1]
    for i in range(2, 7):
        plot.update_history(list(range(1, i)))
    assert calls == []
