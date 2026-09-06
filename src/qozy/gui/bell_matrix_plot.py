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
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from qozy.core.bell_math import POLARIZATION_LABELS

_BOB_ANGLE_LABELS = ("22.5°", "67.5°", "112.5°", "157.5°")


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
        self.clear()

    def clear(self) -> None:
        """Reset to a placeholder — shown before the first scan of a
        session, and while a new scan is running so a stale matrix from a
        previous run isn't mistaken for the current one."""
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
        self.canvas.draw_idle()

    def update_matrix(self, matrix: np.ndarray, e: np.ndarray, s: np.ndarray) -> None:
        self._ax.clear()
        self._ax.set_axis_on()
        self._ax.imshow(matrix, cmap="coolwarm", aspect="auto")
        self._ax.set_xticks(range(matrix.shape[1]))
        self._ax.set_xticklabels(_BOB_ANGLE_LABELS[: matrix.shape[1]])
        self._ax.set_yticks(range(matrix.shape[0]))
        self._ax.set_yticklabels(POLARIZATION_LABELS[: matrix.shape[0]])
        self._ax.set_xlabel("Bob angle", fontsize=9)

        vmax = float(np.max(matrix)) if matrix.size else 0.0
        for row in range(matrix.shape[0]):
            for col in range(matrix.shape[1]):
                value = matrix[row, col]
                color = "white" if value > vmax * 0.55 else "black"
                self._ax.text(
                    col, row, f"{value:.0f}", ha="center", va="center", fontsize=9, color=color
                )

        e_text = "  ".join(f"E{i + 1}={v:.2f}" for i, v in enumerate(e))
        s_text = "  ".join(f"S{i + 1}={v:.2f}" for i, v in enumerate(s))
        self._ax.set_title(f"{e_text}\n{s_text}", fontsize=9)
        self.canvas.draw_idle()

    def save_svg(self, path: Path) -> None:
        self.figure.savefig(path, bbox_inches="tight")
