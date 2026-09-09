"""Matplotlib heatmap of the Bell-scan coincidence matrix, with E/S values
annotated directly on the plot.

A lighter, modern take on ``old_spdc_to_port/spdc/bellvalue.py``'s ``plot()``
function, which colored a 4x4 slice of a full angle sweep the same way and
printed E1-E4/S1-S4 next to it. This widget skips the full 4x16 visibility
curve that function also drew — this app's ``BellScanController`` only ever
takes the four discrete Bell-angle settings, not a continuous sweep — and
keeps to the part that maps directly onto data this app actually has: the
4x4 matrix itself.

The existing ``QTableWidget`` next to this widget (see ``CountsPage``) still
shows exact numeric values; this is for reading CHSH violation strength at
a glance, not for precise numbers.

Updated live, one cell at a time, as ``BellScanController.run()`` reports
each completed setting from its own background ``QThread`` (see
``gui/scan_worker.py``) — this widget itself never touches a thread; it's
just handed already-computed values through a normal (automatically
queued, cross-thread-safe) Qt signal/slot, same as the numeric table next
to it. ``canvas.draw_idle()`` defers the actual repaint to Qt's own idle
processing instead of forcing an immediate synchronous redraw, which is
what keeps sixteen rapid per-cell updates during a scan from stuttering
the GUI.

The canvas has a fixed pixel size and fixed subplot margins (set once,
never recomputed per draw) rather than matplotlib's ``tight_layout``,
which recalculates margins from the current tick/title text on every
single redraw. During a live scan the title alternates between a short
"Scanning… N/16" line and a two-line E/S block of varying digit widths,
and ``tight_layout`` would shift the axes within the canvas — and, worse,
change the canvas's own size hint — on every one of those redraws,
which is what shows up as the whole page twitching several times a
second. A fixed size and fixed margins mean only the pixels that actually
changed are ever different between two redraws.

``update_matrix()`` also updates artists **in place** (``image.set_data()``,
``text.set_text()``/``set_color()``/``set_visible()``) after the first
call, instead of calling ``ax.clear()`` and rebuilding the whole plot
(image, ticks, axis labels, sixteen text objects) from scratch every
time. ``ax.clear()`` — not the actual pixel rasterization — turned out to
be the dominant cost of a redraw: roughly 13 ms of pure Python/matplotlib
object-creation overhead per call, measured directly, on top of whatever
the Agg backend then needs for the real render. At 16 cells a cycle that
adds up to noticeable, avoidable GUI-thread work during a live scan;
avoiding ``ax.clear()`` cut it to isolated ``set_*()`` calls on
already-existing artists, which is what the rest of this docstring assumed
before that optimization was added — the *first* call after construction
or ``clear()`` still builds everything once, since there's nothing to
mutate yet.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from qozy.core.bell_math import POLARIZATION_LABELS

_BOB_ANGLE_LABELS = ("22.5°", "67.5°", "112.5°", "157.5°")
_UNFILLED_COLOR = "#e4e7ee"
_CANVAS_SIZE_PX = (420, 360)


class BellMatrixPlot(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(4.2, 3.6), dpi=100)
        # Fixed margins, set once: room at the top for a two-line title
        # (the E/S block) even when the current title is only one line
        # (the "Scanning…" progress text) or none (the placeholder), so
        # switching between them never changes where the axes sit.
        self.figure.subplots_adjust(left=0.14, right=0.97, bottom=0.14, top=0.78)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setFixedSize(*_CANVAS_SIZE_PX)
        layout.addWidget(self.canvas)
        self._ax = self.figure.add_subplot(111)
        self._image = None
        self._cell_texts: list[list] = []
        self.clear()

    def clear(self) -> None:
        """Reset to a placeholder — shown before the first scan of a
        session. Not called between cycles of a live/looping scan, so a
        completed matrix keeps being shown (and refined in place) rather
        than flashing to this placeholder and back every cycle."""
        self._ax.clear()
        self._ax.set_axis_off()
        self._ax.text(
            0.5,
            0.5,
            "Run a Bell scan to see the matrix",
            ha="center",
            va="center",
            fontsize=10,
            color="#8892a6",
            transform=self._ax.transAxes,
        )
        # Forces the next update_matrix() to rebuild everything once,
        # rather than trying to mutate artists ax.clear() just destroyed.
        self._image = None
        self._cell_texts = []
        self.canvas.draw_idle()

    def update_matrix(
        self,
        matrix: np.ndarray,
        filled: np.ndarray | None = None,
        e: np.ndarray | None = None,
        s: np.ndarray | None = None,
    ) -> None:
        """Redraw with ``matrix``. ``filled`` marks which cells actually
        have a measurement yet (defaults to "all of them", i.e. a
        completed scan) — cells not yet filled are drawn in a neutral
        color rather than as if they were a real zero-count reading, and
        excluded from the color-scale normalization below.

        ``e``/``s`` are optional: a scan in progress has neither yet, so
        the title shows a "measured so far" count instead of CHSH values
        until both are supplied on the final, completed-scan call.
        """
        if filled is None:
            filled = np.ones(matrix.shape, dtype=bool)

        cmap = colormaps["coolwarm"].with_extremes(bad=_UNFILLED_COLOR)
        display = np.ma.masked_array(matrix, mask=~filled)

        # The color scale reflects only what's actually been measured so
        # far, not a range fixed up front — it recalibrates as each new
        # cell comes in during a live scan, rather than (mis)representing
        # unmeasured cells as if they were known low values.
        measured = matrix[filled]
        if measured.size:
            vmin, vmax = float(measured.min()), float(measured.max())
            if vmin == vmax:
                vmin, vmax = vmin - 1.0, vmax + 1.0
        else:
            vmin, vmax = 0.0, 1.0

        if self._image is None:
            # First call since construction or clear(): nothing to mutate
            # yet, so build the image/ticks/text artists once. Every
            # subsequent call reuses these instead of destroying and
            # recreating them (see the module docstring for why that
            # matters for a live scan calling this up to 16 times a cycle).
            self._ax.clear()
            self._ax.set_axis_on()
            self._image = self._ax.imshow(display, cmap=cmap, aspect="auto", vmin=vmin, vmax=vmax)
            self._ax.set_xticks(range(matrix.shape[1]))
            self._ax.set_xticklabels(_BOB_ANGLE_LABELS[: matrix.shape[1]])
            self._ax.set_yticks(range(matrix.shape[0]))
            self._ax.set_yticklabels(POLARIZATION_LABELS[: matrix.shape[0]])
            self._ax.set_xlabel("Bob angle", fontsize=9)
            self._cell_texts = [
                [
                    self._ax.text(col, row, "", ha="center", va="center", fontsize=9)
                    for col in range(matrix.shape[1])
                ]
                for row in range(matrix.shape[0])
            ]
        else:
            self._image.set_data(display)
            self._image.set_clim(vmin, vmax)

        mid = (vmin + vmax) / 2.0
        for row in range(matrix.shape[0]):
            for col in range(matrix.shape[1]):
                text = self._cell_texts[row][col]
                if filled[row, col]:
                    value = matrix[row, col]
                    text.set_text(f"{value:.0f}")
                    text.set_color("white" if value > mid else "black")
                    text.set_visible(True)
                else:
                    text.set_visible(False)

        if e is not None and s is not None:
            e_text = "  ".join(f"E{i + 1}={v:.2f}" for i, v in enumerate(e))
            s_text = "  ".join(f"S{i + 1}={v:.2f}" for i, v in enumerate(s))
            title = f"{e_text}\n{s_text}"
        else:
            title = f"Scanning…  {int(np.count_nonzero(filled))}/{filled.size} settings measured"
        self._ax.set_title(title, fontsize=9)
        self.canvas.draw_idle()

    def save_svg(self, path: Path) -> None:
        self.figure.savefig(path, bbox_inches="tight")
