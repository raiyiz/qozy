"""VisPy canvas embedded in a QWidget, replacing the old
pyqtgraph/matplotlib plotting from ``old_spdc_to_port/spdc/main.py``.

Kept intentionally dumb: it only knows how to draw line data it's handed.
Anything about *what* to plot (which mode, which channels) lives in
``CountsPage`` / the controller.
"""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QVBoxLayout, QWidget
from vispy import scene
from vispy.app import use_app
from vispy.scene import visuals

use_app("pyqt6")


class PlotPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.canvas = scene.SceneCanvas(keys="interactive", show=True, bgcolor="#0b1117")
        self.canvas.native.setMinimumHeight(420)
        self.canvas.native.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self.canvas.native)

        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "panzoom"
        self.grid = visuals.GridLines(parent=self.view.scene, color=(0.30, 0.38, 0.52, 0.8))

        self.alice_line = visuals.Line(parent=self.view.scene, color=(0.93, 0.32, 0.30, 1.0), width=2.5)
        self.bob_line = visuals.Line(parent=self.view.scene, color=(0.26, 0.72, 0.98, 1.0), width=2.5)
        self.corr_line = visuals.Line(parent=self.view.scene, color=(0.74, 0.82, 0.26, 1.0), width=2.0)

    def set_traces(
        self,
        t: np.ndarray,
        alice: np.ndarray | None = None,
        bob: np.ndarray | None = None,
        corr: np.ndarray | None = None,
        y_range: tuple[float, float] | None = None,
    ) -> None:
        zeros = np.zeros_like(t)
        self.alice_line.set_data(np.column_stack((t, alice if alice is not None else zeros)))
        self.bob_line.set_data(np.column_stack((t, bob if bob is not None else zeros)))
        self.corr_line.set_data(np.column_stack((t, corr if corr is not None else zeros)))

        if y_range is not None:
            self.view.camera.set_range(x=(float(t[0]), float(t[-1])), y=y_range)
