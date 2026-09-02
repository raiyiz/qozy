import numpy as np
from vispy import app, scene
from vispy.scene import visuals

from signal_utils import generate_signal


class SignalViewer:
    def __init__(self) -> None:
        self.canvas = scene.SceneCanvas(
            keys="interactive",
            show=True,
            title="Quiet Signal Viewer",
            bgcolor="#0f1720",
            size=(1000, 650),
        )
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "panzoom"

        self.x = np.linspace(0.0, 20.0, 2000)
        self.phase = 0.0
        self.amplitude = 1.0
        self.speed = 0.08
        self.decay = 35.0
        self.grid_visible = True

        self.grid = visuals.GridLines(parent=self.view.scene, color=(0.22, 0.27, 0.35, 0.35))
        self.line = visuals.Line(parent=self.view.scene, color="#68d7ff", width=2.2)
        self.status = visuals.Text(
            "",
            color="white",
            font_size=12,
            parent=self.canvas.scene,
            pos=(16, 14),
        )
        self.hints = visuals.Text(
            "Space: pause/resume | Up/Down: amplitude | Left/Right: speed | G: grid | R: reset | Esc: quit",
            color="#b8c6db",
            font_size=11,
            parent=self.canvas.scene,
            pos=(16, 36),
        )

        self.timer = app.Timer(interval=1 / 30, connect=self.update, start=True)
        self.canvas.events.key_press.connect(self.on_key)
        self.canvas.events.resize.connect(self.on_resize)
        self.redraw()

    def redraw(self) -> None:
        y = generate_signal(self.x, self.phase, self.amplitude, self.decay)
        self.line.set_data(np.column_stack((self.x, y)))
        self.view.camera.set_range(x=(0.0, 20.0), y=(-2.2, 2.2))
        self.grid.visible = self.grid_visible
        state = "Running" if self.timer.running else "Paused"
        self.status.text = (
            f"{state} | amp={self.amplitude:.2f} | speed={self.speed:.2f} | "
            f"phase={self.phase:.2f} | grid={'on' if self.grid_visible else 'off'}"
        )

    def update(self, _event) -> None:
        self.phase += self.speed
        self.redraw()

    def on_resize(self, _event) -> None:
        self.hints.pos = (16, self.canvas.size[1] - 20)

    def on_key(self, event) -> None:
        if event.key == "Space":
            self.timer.running = not self.timer.running
        elif event.key == "R":
            self.phase = 0.0
            self.amplitude = 1.0
            self.speed = 0.08
            self.grid_visible = True
            self.timer.running = True
        elif event.key == "Up":
            self.amplitude = min(2.0, self.amplitude + 0.1)
        elif event.key == "Down":
            self.amplitude = max(0.1, self.amplitude - 0.1)
        elif event.key == "Right":
            self.speed = min(0.3, self.speed + 0.01)
        elif event.key == "Left":
            self.speed = max(0.01, self.speed - 0.01)
        elif event.key == "G":
            self.grid_visible = not self.grid_visible
        elif event.key == "Escape":
            self.canvas.close()
            return
        else:
            return
        self.redraw()


if __name__ == "__main__":
    SignalViewer()
    app.run()
