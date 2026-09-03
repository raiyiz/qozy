import numpy as np
from vispy import scene
from vispy.app import use_app
from vispy.scene import visuals

use_app("pyqt5")


class VisPyPlotPanel:
    def __init__(self, parent_widget, title: str = ""):
        self.canvas = scene.SceneCanvas(
            keys="interactive",
            show=True,
            bgcolor="#08131a",
            size=(900, 210),
        )
        self.native = self.canvas.native
        parent_widget.layout().addWidget(self.native)

        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "panzoom"

        self.grid = visuals.GridLines(parent=self.view.scene, color=(0.25, 0.35, 0.5, 0.8))
        self.lines: dict[str, visuals.Line] = {}
        self.title = title
        if title:
            self.title_text = visuals.Text(
                title,
                color="white",
                font_size=12,
                parent=self.canvas.scene,
                pos=(16, 16),
            )

    def add_line(self, name: str, color, width: float = 2.0) -> visuals.Line:
        line = visuals.Line(parent=self.view.scene, color=color, width=width)
        self.lines[name] = line
        return line

    def set_data(self, name: str, x: np.ndarray, y: np.ndarray) -> None:
        if name not in self.lines:
            raise KeyError(f"No line named '{name}' in this plot panel")
        self.lines[name].set_data(np.column_stack((x, y)))

    def set_range(self, x_range: tuple[float, float] | None = None, y_range: tuple[float, float] | None = None) -> None:
        if x_range is None:
            x_range = (0.0, 1.0)
        if y_range is None:
            y_range = (0.0, 1.0)
        self.view.camera.set_range(x=x_range, y=y_range)

    def clear(self) -> None:
        for line in self.lines.values():
            line.set_data(np.column_stack((np.array([0.0, 1.0]), np.array([0.0, 0.0]))))
