# Quiet Signal Viewer

## Oskar Sund and the Quiet Equation

Oskar Sund was a physicist who listened carefully—to instruments, to colleagues, and especially to the silences between measurements.

One winter evening, his laboratory’s old detector began recording a faint, repeating signal. Everyone assumed it was noise. Oskar stayed after the others had gone, wrapped in a wool coat, and plotted the readings by hand.

The pattern was delicate but exact. He built a small model, tested it against the data, and found that the signal matched the rhythm of a distant storm passing through the upper atmosphere. The detector had heard what no one had thought to ask it about.

When Oskar presented his result, the room fell quiet. Then a student raised her hand and asked, “How did you find it?”

Oskar smiled. “I stopped trying to make the universe speak loudly.”

From then on, his students learned that physics was not only the search for grand answers. It was also the patience to notice a whisper—and the courage to follow it.

## VisPy GUI starter

Save the following as `app.py`:

```python
import numpy as np
from vispy import app, scene
from vispy.scene import visuals


class SignalViewer:
	def __init__(self):
		self.canvas = scene.SceneCanvas(
			keys="interactive", show=True, title="Quiet Signal Viewer",
			bgcolor="#10151c", size=(900, 600)
		)
		self.view = self.canvas.central_widget.add_view()
		self.view.camera = "panzoom"
		self.x = np.linspace(0, 20, 2000)
		self.phase = 0.0
		self.line = visuals.Line(parent=self.view.scene, color="#65d9ff", width=2)
		self.status = visuals.Text("Amplitude: 1.0", color="white", font_size=12,
										   parent=self.canvas.scene, pos=(15, 15))
		self.timer = app.Timer(interval=1 / 30, connect=self.update, start=True)
		self.canvas.events.key_press.connect(self.on_key)
		self.redraw()

	def redraw(self):
		y = np.sin(self.x + self.phase) * np.exp(-self.x / 35)
		self.line.set_data(np.column_stack((self.x, y)))
		self.view.camera.set_range(x=(0, 20), y=(-1.2, 1.2))

	def update(self, event):
		self.phase += 0.08
		self.redraw()

	def on_key(self, event):
		if event.key == "Space":
			self.timer.running = not self.timer.running
			self.status.text = "Paused" if not self.timer.running else "Running"
		elif event.key == "R":
			self.phase = 0
			self.redraw()
		elif event.key == "Escape":
			self.canvas.close()


if __name__ == "__main__":
	SignalViewer()
	app.run()
```

Install and run with `pip install vispy numpy` followed by `python app.py`. Press `Space` to pause or resume, `R` to reset, and `Esc` to exit.

## Basic GitLab CI

Save as `.gitlab-ci.yml`:

```yaml
image: python:3.12-slim

stages: [test]

test:
  stage: test
  before_script:
	- python -m pip install --upgrade pip
	- pip install numpy vispy pytest
  script:
	- python -m compileall -q app.py
	- pytest -q
```
