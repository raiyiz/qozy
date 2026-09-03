import sys
from pathlib import Path

import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)
from vispy import scene
from vispy.app import use_app
from vispy.scene import visuals

use_app("pyqt5")

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def generate_spdc_data(angle_deg: float, phase: float, t: np.ndarray):
    angle_rad = np.deg2rad(angle_deg)
    alice = 1100 + 450 * np.cos(np.deg2rad(t * 0.75 - angle_deg)) ** 2
    bob = 980 + 410 * np.cos(np.deg2rad(t * 0.9 + 45.0 - angle_deg)) ** 2
    alice += 120 * np.sin(2.0 * np.pi * 0.03 * t + phase)
    bob += 90 * np.cos(2.0 * np.pi * 0.04 * t + phase * 0.7)
    corr = 240 + 180 * np.exp(-(((t - 50.0) / 18.0) ** 2)) + 35 * np.sin(phase + t / 12.0)
    return alice, bob, corr


class SPDCVisPyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SPDC Source Aligner (PyQt + VisPy)")
        self.resize(1200, 760)

        self.angle_deg = 22.5
        self.phase = 0.0
        self.live_scan = True

        self._build_ui()
        self._update_plot()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_plot)
        self.timer.start(35)

    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)

        controls_panel = QWidget(self)
        controls_panel.setFixedWidth(280)
        controls_layout = QVBoxLayout(controls_panel)

        self.live_checkbox = QCheckBox("Live scan")
        self.live_checkbox.setChecked(True)
        self.live_checkbox.toggled.connect(self._toggle_live_scan)

        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(0, 180)
        self.angle_slider.setValue(int(self.angle_deg))
        self.angle_slider.valueChanged.connect(self._angle_changed)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(
            ["Alice / Bob visibility", "Coincidence envelope", "Bell-style summary"]
        )
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)

        self.reset_button = QPushButton("Reset phase")
        self.reset_button.clicked.connect(self._reset_phase)

        self.measure_button = QPushButton("Measure once")
        self.measure_button.clicked.connect(self._measure_once)

        self.status_label = QLabel("Phase: 0.00 | Angle: 22.5°")
        self.status_label.setWordWrap(True)

        controls_layout.addWidget(self.live_checkbox)
        controls_layout.addWidget(QLabel("Detector angle (deg):"))
        controls_layout.addWidget(self.angle_slider)
        controls_layout.addWidget(QLabel("Display mode:"))
        controls_layout.addWidget(self.mode_combo)
        controls_layout.addWidget(self.reset_button)
        controls_layout.addWidget(self.measure_button)
        controls_layout.addWidget(self.status_label)
        controls_layout.addStretch()

        root_layout.addWidget(controls_panel)

        plot_area = QWidget(self)
        plot_layout = QVBoxLayout(plot_area)

        self.canvas = scene.SceneCanvas(
            keys="interactive",
            show=True,
            bgcolor="#0b1117",
            size=(850, 600),
        )
        self.canvas.native.setMinimumHeight(520)
        self.canvas.native.setFocusPolicy(Qt.StrongFocus)
        plot_layout.addWidget(self.canvas.native)

        self.view = self.canvas.central_widget.add_view()
        self.view.camera = "panzoom"
        self.grid = visuals.GridLines(
            parent=self.view.scene, color=(0.30, 0.38, 0.52, 0.8)
        )
        self.alice_line = visuals.Line(
            parent=self.view.scene, color=(0.928, 0.32, 0.30, 1.0), width=2.5
        )
        self.bob_line = visuals.Line(
            parent=self.view.scene, color=(0.26, 0.72, 0.98, 1.0), width=2.5
        )
        self.corr_line = visuals.Line(
            parent=self.view.scene, color=(0.74, 0.82, 0.26, 1.0), width=2.0
        )

        root_layout.addWidget(plot_area)

    def _toggle_live_scan(self, checked: bool):
        self.live_scan = checked

    def _angle_changed(self, value: int):
        self.angle_deg = float(value)
        self._update_plot()

    def _mode_changed(self, index: int):
        self._update_plot()

    def _reset_phase(self):
        self.phase = 0.0
        self._update_plot()

    def _measure_once(self):
        self.live_scan = False
        self.live_checkbox.setChecked(False)
        self._update_plot()

    def _update_plot(self):
        t = np.linspace(0.0, 100.0, 800)
        alice, bob, corr = generate_spdc_data(self.angle_deg, self.phase, t)

        mode = self.mode_combo.currentText()
        if mode == "Alice / Bob visibility":
            self.alice_line.set_data(np.column_stack((t, alice)))
            self.bob_line.set_data(np.column_stack((t, bob)))
            self.corr_line.set_data(np.column_stack((t, np.zeros_like(t))))
            self.view.camera.set_range(x=(0, 100), y=(600, 1700))
        elif mode == "Coincidence envelope":
            self.alice_line.set_data(np.column_stack((t, np.zeros_like(t))))
            self.bob_line.set_data(np.column_stack((t, np.zeros_like(t))))
            self.corr_line.set_data(np.column_stack((t, corr)))
            self.view.camera.set_range(x=(0, 100), y=(0, 500))
        else:
            bell = 0.5 * alice + 0.5 * bob
            self.alice_line.set_data(np.column_stack((t, bell)))
            self.bob_line.set_data(np.column_stack((t, bob)))
            self.corr_line.set_data(np.column_stack((t, corr * 0.5)))
            self.view.camera.set_range(x=(0, 100), y=(0, 2000))

        self.phase += 0.03 if self.live_scan else 0.0
        self.status_label.setText(
            f"Phase: {self.phase:.2f} | Angle: {self.angle_deg:.1f}°"
        )


def main():
    app = QApplication(sys.argv)
    window = SPDCVisPyWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
