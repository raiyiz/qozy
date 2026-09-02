import sys

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .controller import SPDCController
from .data_model import MeasurementConfig
from .plot_panel import VisPyPlotPanel


class SPDCMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = MeasurementConfig()
        self.controller = SPDCController(self.config)

        self.setWindowTitle("SPDC Source Aligner")
        self.resize(1280, 760)

        central = QWidget(self)
        self.setCentralWidget(central)

        outer = QHBoxLayout(central)

        control_panel = QWidget(self)
        control_panel.setFixedWidth(280)
        control_layout = QVBoxLayout(control_panel)

        self.live_checkbox = QCheckBox("Live scan")
        self.live_checkbox.setChecked(True)
        self.live_checkbox.toggled.connect(self._set_live_scan)

        self.angle_slider = QSlider(Qt.Horizontal)
        self.angle_slider.setRange(0, 180)
        self.angle_slider.setValue(int(self.config.detector_angle))
        self.angle_slider.valueChanged.connect(self._on_angle_change)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Alice/Bob visibility", "Coincidence envelope", "Bell summary"])

        self.reset_button = QPushButton("Reset phase")
        self.reset_button.clicked.connect(self._reset_phase)

        self.measure_button = QPushButton("Measure once")
        self.measure_button.clicked.connect(self._measure_once)

        self.status_label = QLabel("Waiting for data...")
        self.status_label.setWordWrap(True)

        control_layout.addWidget(self.live_checkbox)
        control_layout.addWidget(QLabel("Detector angle (deg):"))
        control_layout.addWidget(self.angle_slider)
        control_layout.addWidget(QLabel("View mode:"))
        control_layout.addWidget(self.mode_combo)
        control_layout.addWidget(self.reset_button)
        control_layout.addWidget(self.measure_button)
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()

        outer.addWidget(control_panel)

        plot_container = QWidget(self)
        plot_container.setMinimumWidth(700)
        plot_layout = QVBoxLayout(plot_container)
        self.plot_panel = VisPyPlotPanel(plot_container)
        outer.addWidget(plot_container)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

    def _set_live_scan(self, checked: bool) -> None:
        self.config.live_scan = checked

    def _on_angle_change(self, value: int) -> None:
        self.config.detector_angle = float(value)

    def _reset_phase(self) -> None:
        self.controller.state.phase = 0.0

    def _measure_once(self) -> None:
        self.config.live_scan = False
        self.live_checkbox.setChecked(False)

    def _tick(self) -> None:
        phase = self.controller.state.phase
        self.controller.update_state(phase)

        time_axis = [idx / 10 for idx in range(len(self.controller.state.alice_counts))]
        t = __import__("numpy").array(time_axis, dtype=float)
        alice = __import__("numpy").array(self.controller.state.alice_counts, dtype=float)
        bob = __import__("numpy").array(self.controller.state.bob_counts, dtype=float)
        coin = __import__("numpy").array(self.controller.state.coin_counts, dtype=float)

        mode = self.mode_combo.currentText()
        if mode == "Coincidence envelope":
            self.plot_panel.update(t, coin * 0.3, coin * 0.2, coin)
        elif mode == "Bell summary":
            self.plot_panel.update(t, alice * 0.5, bob * 0.5, coin)
        else:
            self.plot_panel.update(t, alice, bob, coin)

        self.controller.state.phase += 0.03 if self.config.live_scan else 0.0
        self.status_label.setText(self.controller.summary_text())


def main() -> None:
    app = QApplication(sys.argv)
    window = SPDCMainWindow()
    window.show()
    sys.exit(app.exec_())
