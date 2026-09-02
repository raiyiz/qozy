import numpy as np
from vispy import scene
from vispy.app import use_app
from vispy.scene import visuals

use_app("pyqt5")


class VisPyPlotPanel:
    def __init__(self, parent_widget):
        self.canvas = scene.SceneCanvas(
            keys="interactive",
            show=True,
            bgcolor="#08131a",
            size=(900, 600),
        )
        self.native = self.canvas.native
        parent_widget.layout().addWidget(self.native)

        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "panzoom"

        self.grid = visuals.GridLines(parent=self.view.scene, color=(0.25, 0.35, 0.5, 0.8))
        self.alice_line = visuals.Line(parent=self.view.scene, color=(0.93, 0.30, 0.30, 1.0), width=2.5)
        self.bob_line = visuals.Line(parent=self.view.scene, color=(0.25, 0.74, 0.98, 1.0), width=2.5)
        self.coin_line = visuals.Line(parent=self.view.scene, color=(0.78, 0.82, 0.24, 1.0), width=2.0)

    def update(self, t: np.ndarray, alice: np.ndarray, bob: np.ndarray, coin: np.ndarray) -> None:
        self.alice_line.set_data(np.column_stack((t, alice)))
        self.bob_line.set_data(np.column_stack((t, bob)))
        self.coin_line.set_data(np.column_stack((t, coin)))
        self.view.camera.set_range(x=(float(t.min()), float(t.max())), y=(0.0, max(float(alice.max()), float(bob.max()), float(coin.max())) * 1.2))

    def clear(self) -> None:
        self.alice_line.set_data(np.column_stack((np.array([0.0, 1.0]), np.array([0.0, 0.0]))))
        self.bob_line.set_data(np.column_stack((np.array([0.0, 1.0]), np.array([0.0, 0.0]))))
        self.coin_line.set_data(np.column_stack((np.array([0.0, 1.0]), np.array([0.0, 0.0]))))
