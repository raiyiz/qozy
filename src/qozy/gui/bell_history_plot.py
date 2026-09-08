"""A small line plot of max|S| across successive Bell-scan cycles.

Complements ``BellMatrixPlot`` (a snapshot of the current cycle) with a
view of how the result is trending over time — useful once "Loop
continuously (live)" is enabled on the Counts page and the scan keeps
re-measuring all 16 settings back to back, e.g. while tuning polarization
optics and watching whether |S| is climbing toward violation or drifting
away from it.

Fixed canvas size and fixed subplot margins, same reasoning as
``BellMatrixPlot``: the y-axis limit and the title both change on every
cycle (a growing "cycle N" count, a changing max|S| value), and letting
``tight_layout`` recompute margins from that changing text on every redraw
is what makes the page visibly twitch during a live-looping scan.
"""

from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QVBoxLayout, QWidget

#: |S| <= 2 is the classical (local hidden-variable) bound; |S| <= 2*sqrt(2)
#: is the Tsirelson bound, the maximum quantum mechanics itself allows.
CLASSICAL_BOUND = 2.0
TSIRELSON_BOUND = 2.0 * np.sqrt(2.0)

_CANVAS_SIZE_PX = (420, 200)


class BellHistoryPlot(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(4.2, 2.0), dpi=100)
        self.figure.subplots_adjust(left=0.13, right=0.97, bottom=0.22, top=0.82)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setFixedSize(*_CANVAS_SIZE_PX)
        layout.addWidget(self.canvas)
        self._ax = self.figure.add_subplot(111)
        self.clear()

    def clear(self) -> None:
        self._ax.clear()
        self._ax.set_axis_off()
        self._ax.text(
            0.5,
            0.5,
            "max |S| per cycle appears here in live mode",
            ha="center",
            va="center",
            fontsize=9,
            color="#8892a6",
            transform=self._ax.transAxes,
        )
        self.canvas.draw_idle()

    def update_history(self, max_s_values: list[float]) -> None:
        """Redraw with one point per completed cycle, most recent last."""
        if not max_s_values:
            self.clear()
            return

        self._ax.clear()
        self._ax.set_axis_on()
        cycles = np.arange(1, len(max_s_values) + 1)
        values = np.asarray(max_s_values, dtype=float)

        self._ax.axhline(CLASSICAL_BOUND, color="#8892a6", linestyle="--", linewidth=1)
        self._ax.axhline(TSIRELSON_BOUND, color="#8892a6", linestyle=":", linewidth=1)
        self._ax.plot(cycles, values, color="#d1495b", marker="o", markersize=3, linewidth=1.5)

        self._ax.set_xlabel("scan cycle", fontsize=9)
        self._ax.set_ylabel("max |S|", fontsize=9)
        y_top = max(TSIRELSON_BOUND, float(values.max())) + 0.2
        self._ax.set_ylim(0, y_top)
        # keep the x-axis on integer cycle numbers even for a handful of points
        self._ax.set_xlim(0.5, max(len(max_s_values), 1) + 0.5)
        self._ax.set_title(f"cycle {len(max_s_values)}: max |S| = {values[-1]:.2f}", fontsize=9)
        self.canvas.draw_idle()
