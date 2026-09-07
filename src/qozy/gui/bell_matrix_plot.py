"""Matplotlib heatmap of the live Bell coincidence matrix."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib import colormaps
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from qozy.core.bell_math import POLARIZATION_LABELS

_BOB_ANGLE_LABELS = ("22.5°", "67.5°", "112.5°", "157.5°")
_UNFILLED_COLOR = "#e4e7ee"


class BellMatrixPlot(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.figure = Figure(figsize=(4.2, 3.6), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setMinimumHeight(260)
        layout.addWidget(self.canvas)
        self._ax = self.figure.add_subplot(111)
        self._live_context: str | None = None
        self._active_cell: tuple[int, int] | None = None
        self._color_reference_total: float | None = None
        self.clear()

    def set_live_context(
        self,
        title: str | None,
        active_cell: tuple[int, int] | None,
    ) -> None:
        """Set optional live-acquisition title and active-cell highlight."""
        if active_cell is not None and not (
            0 <= active_cell[0] < 4 and 0 <= active_cell[1] < 4
        ):
            raise ValueError(f"invalid Bell matrix cell {active_cell}")
        self._live_context = title
        self._active_cell = active_cell

    def set_color_reference_total(self, total: float | None) -> None:
        """Use raw measured counts to determine heatmap intensity."""
        self._color_reference_total = None if total is None else max(float(total), 0.0)

    def clear(self) -> None:
        self._live_context = None
        self._active_cell = None
        self._color_reference_total = None
        self._ax.clear()
        self._ax.set_axis_off()
        self._ax.text(
            0.5,
            0.5,
            "Start acquisition to see the matrix",
            ha="center",
            va="center",
            fontsize=10,
            color="#8892a6",
            transform=self._ax.transAxes,
        )
        self.canvas.draw_idle()

    def update_matrix(
        self,
        matrix: np.ndarray,
        filled: np.ndarray | None = None,
        e: np.ndarray | None = None,
        s: np.ndarray | None = None,
        color_reference_total: float | None = None,
    ) -> None:
        """Redraw the matrix while keeping measurement state separate from display state."""
        values = np.asarray(matrix, dtype=float)
        if values.shape != (4, 4):
            raise ValueError(f"expected a 4x4 matrix, got {values.shape}")
        if filled is None:
            filled = np.ones(values.shape, dtype=bool)
        else:
            filled = np.asarray(filled, dtype=bool)
        if filled.shape != values.shape:
            raise ValueError(f"expected a 4x4 filled mask, got {filled.shape}")

        self._ax.clear()
        self._ax.set_axis_on()

        cmap = colormaps["coolwarm"].with_extremes(bad=_UNFILLED_COLOR)
        if color_reference_total is None:
            color_reference_total = self._color_reference_total
        if color_reference_total is None:
            color_reference_total = float(np.sum(values[filled]))
        total = max(float(color_reference_total), 0.0)
        color_values = np.zeros_like(values, dtype=float)
        if total > 0.0:
            color_values[filled] = values[filled] / total

        color_display = np.ma.masked_array(color_values, mask=~filled)
        self._ax.imshow(color_display, cmap=cmap, aspect="equal", vmin=0.0, vmax=1.0)
        self._ax.set_xticks(range(values.shape[1]))
        self._ax.set_xticklabels(_BOB_ANGLE_LABELS[: values.shape[1]])
        self._ax.set_yticks(range(values.shape[0]))
        self._ax.set_yticklabels(POLARIZATION_LABELS[: values.shape[0]])
        self._ax.set_xlabel("Bob angle", fontsize=9)

        for row in range(values.shape[0]):
            for col in range(values.shape[1]):
                if not filled[row, col]:
                    continue
                value = values[row, col]
                intensity = color_values[row, col]
                text_color = "white" if intensity > 0.5 else "black"
                self._ax.text(
                    col,
                    row,
                    f"{value:.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=text_color,
                )

        if self._active_cell is not None and filled[self._active_cell]:
            row, col = self._active_cell
            self._ax.add_patch(
                Rectangle(
                    (col - 0.5, row - 0.5),
                    1,
                    1,
                    fill=False,
                    linewidth=2,
                    edgecolor="#111827",
                )
            )

        if self._live_context is not None:
            title = self._live_context
        elif e is not None and s is not None:
            e_text = "  ".join(f"E{i + 1}={v:.2f}" for i, v in enumerate(e))
            s_text = "  ".join(f"S{i + 1}={v:.2f}" for i, v in enumerate(s))
            title = f"{e_text}\n{s_text}"
        else:
            title = f"Scanning…  {int(np.count_nonzero(filled))}/{filled.size} settings measured"
        self._ax.set_title(title, fontsize=9)
        self.canvas.draw_idle()

    def save_svg(self, path: Path) -> None:
        self.figure.savefig(path, bbox_inches="tight")
