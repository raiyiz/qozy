import sys
from pathlib import Path

import numpy as np
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSlider,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

try:
    from .controller import SPDCController
    from .data_model import MeasurementConfig
    from .plot_panel import VisPyPlotPanel
    from .simulator_adapter import SimulatorAdapter
    from .timetagger_adapter import TimeTaggerAdapter
except ImportError:  # allow direct script execution in the repo without package import
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from spdc_app.controller import SPDCController
    from spdc_app.data_model import MeasurementConfig
    from spdc_app.plot_panel import VisPyPlotPanel
    from spdc_app.simulator_adapter import SimulatorAdapter
    from spdc_app.timetagger_adapter import TimeTaggerAdapter


class SPDCMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = MeasurementConfig()
        self.controller = SPDCController(self.config)
        self.adapter = SimulatorAdapter()
        self.is_hardware_connected = False

        self.setWindowTitle("SPDC Source Aligner Tool")
        self.resize(1600, 1100)

        central = QWidget(self)
        self.setCentralWidget(central)

        outer = QHBoxLayout(central)

        control_panel = QWidget(self)
        control_panel.setFixedWidth(320)
        control_layout = QVBoxLayout(control_panel)

        frame = QFrame(self)
        frame.setFrameShape(QFrame.StyledPanel)
        frame_layout = QGridLayout(frame)

        self.PushButtonTTConnect = QPushButton("Connect TimeTagger")
        self.PushButtonTTDisconnect = QPushButton("Disconnect")
        self.PushButtonTTApply = QPushButton("Apply settings")
        self.PushButtonMeasureMatrix = QPushButton("Save matrix")
        self.PushButtonMeasureCounts = QPushButton("Save counts")
        self.PushButtonMeasureBellQuad = QPushButton("Bell quad")
        self.PushButtonMeasureCorrStep = QPushButton("Corr step")
        self.PushButtonMeasureCorrQuad = QPushButton("Corr quad")

        frame_layout.addWidget(self.PushButtonTTConnect, 0, 0, 1, 2)
        frame_layout.addWidget(self.PushButtonTTDisconnect, 1, 0, 1, 2)
        frame_layout.addWidget(self.PushButtonTTApply, 2, 0, 1, 2)
        frame_layout.addWidget(self.PushButtonMeasureMatrix, 3, 0, 1, 2)
        frame_layout.addWidget(self.PushButtonMeasureCounts, 4, 0, 1, 2)
        frame_layout.addWidget(self.PushButtonMeasureBellQuad, 5, 0, 1, 2)
        frame_layout.addWidget(self.PushButtonMeasureCorrStep, 6, 0, 1, 2)
        frame_layout.addWidget(self.PushButtonMeasureCorrQuad, 7, 0, 1, 2)

        control_layout.addWidget(frame)

        self.RadioButtonLiveData = QCheckBox("Live data")
        self.RadioButtonLiveData.setChecked(True)
        self.RadioButtonLiveData.toggled.connect(self._set_live_scan)
        control_layout.addWidget(self.RadioButtonLiveData)

        self.channel_labels = ["AV", "AH", "AD", "AA", "BV", "BH", "BD", "BA"]
        for idx, label in enumerate(self.channel_labels, start=1):
            row = QWidget(self)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            radio = QRadioButton(f"{label} ON")
            radio.setChecked(True)
            setattr(self, f"RadioButton{label}On", radio)
            delay = QLineEdit("0.0")
            delay.setFixedWidth(70)
            setattr(self, f"LineEdit{label}Delay", delay)
            row_layout.addWidget(radio)
            row_layout.addWidget(QLabel("delay:"))
            row_layout.addWidget(delay)
            control_layout.addWidget(row)

        self.LineEditADelay = QLineEdit("0.0")
        self.LineEditBDelay = QLineEdit("0.0")
        self.LineEditCountsBinwidth = QLineEdit("0.1")
        self.LineEditCountsTimeFrame = QLineEdit("5.0")
        self.LineEditCoinTimeWindow = QLineEdit("2.0")
        self.LineEditCorrBinwidth = QLineEdit("0.1")
        self.LineEditCorrTimeFrame = QLineEdit("10.0")
        self.LineEditMatrixIntTime = QLineEdit("1.0")
        self.LineEditMeasureTime = QLineEdit("5.0")

        settings = QFrame(self)
        settings.setFrameShape(QFrame.StyledPanel)
        settings_layout = QGridLayout(settings)
        settings_layout.addWidget(QLabel("A delay:"), 0, 0)
        settings_layout.addWidget(self.LineEditADelay, 0, 1)
        settings_layout.addWidget(QLabel("B delay:"), 1, 0)
        settings_layout.addWidget(self.LineEditBDelay, 1, 1)
        settings_layout.addWidget(QLabel("Counts binwidth:"), 2, 0)
        settings_layout.addWidget(self.LineEditCountsBinwidth, 2, 1)
        settings_layout.addWidget(QLabel("Counts timeframe:"), 3, 0)
        settings_layout.addWidget(self.LineEditCountsTimeFrame, 3, 1)
        settings_layout.addWidget(QLabel("Coin window:"), 4, 0)
        settings_layout.addWidget(self.LineEditCoinTimeWindow, 4, 1)
        settings_layout.addWidget(QLabel("Corr binwidth:"), 5, 0)
        settings_layout.addWidget(self.LineEditCorrBinwidth, 5, 1)
        settings_layout.addWidget(QLabel("Corr timeframe:"), 6, 0)
        settings_layout.addWidget(self.LineEditCorrTimeFrame, 6, 1)
        settings_layout.addWidget(QLabel("Matrix int. time:"), 7, 0)
        settings_layout.addWidget(self.LineEditMatrixIntTime, 7, 1)

        control_layout.addWidget(settings)
        control_layout.addStretch()
        outer.addWidget(control_panel)

        plot_panel_holder = QWidget(self)
        plot_layout = QVBoxLayout(plot_panel_holder)

        plot_stack = QWidget(self)
        plot_stack_layout = QVBoxLayout(plot_stack)

        self.PlotSingle = VisPyPlotPanel(plot_stack, title="Single Counts")
        self.PlotSingle.add_line("alice", (0.93, 0.30, 0.30, 1.0), 2.5)
        self.PlotSingle.add_line("bob", (0.25, 0.74, 0.98, 1.0), 2.5)

        self.PlotCoin = VisPyPlotPanel(plot_stack, title="Coincidence Counts")
        self.PlotCoin.add_line("coin", (0.78, 0.82, 0.24, 1.0), 2.0)

        self.PlotCorr = VisPyPlotPanel(plot_stack, title="Correlation Trace")
        self.PlotCorr.add_line("corr", (0.78, 0.82, 0.24, 1.0), 2.0)

        self.TableCoin = QTableWidget(4, 4)
        self.TableCoin.setHorizontalHeaderLabels(["BV", "BH", "BD", "BA"])
        self.TableCoin.setVerticalHeaderLabels(["AV", "AH", "AD", "AA"])
        self.TableCoin.setAlternatingRowColors(True)

        for row in range(4):
            for col in range(4):
                self.TableCoin.setItem(row, col, QTableWidgetItem("-"))

        plot_layout.addWidget(plot_stack)
        plot_layout.addWidget(self.TableCoin)
        plot_panel_holder.setMinimumWidth(1000)
        outer.addWidget(plot_panel_holder)

        self.status_label = QLabel("Waiting for data...")
        self.status_label.setWordWrap(True)
        control_layout.addWidget(self.status_label)

        self.LabelAliceCountsPerSValue = QLabel("-")
        self.LabelBobCountsPerSValue = QLabel("-")
        self.LabelTotalCoin = QLabel("-")
        self.LabelS1 = QLabel("-")
        self.LabelS2 = QLabel("-")
        self.LabelS3 = QLabel("-")
        self.LabelS4 = QLabel("-")

        summary = QFrame(self)
        summary_layout = QGridLayout(summary)
        summary_layout.addWidget(QLabel("Alice total:"), 0, 0)
        summary_layout.addWidget(self.LabelAliceCountsPerSValue, 0, 1)
        summary_layout.addWidget(QLabel("Bob total:"), 1, 0)
        summary_layout.addWidget(self.LabelBobCountsPerSValue, 1, 1)
        summary_layout.addWidget(QLabel("Total coincidences:"), 2, 0)
        summary_layout.addWidget(self.LabelTotalCoin, 2, 1)
        summary_layout.addWidget(QLabel("S1:"), 3, 0)
        summary_layout.addWidget(self.LabelS1, 3, 1)
        summary_layout.addWidget(QLabel("S2:"), 4, 0)
        summary_layout.addWidget(self.LabelS2, 4, 1)
        summary_layout.addWidget(QLabel("S3:"), 5, 0)
        summary_layout.addWidget(self.LabelS3, 5, 1)
        summary_layout.addWidget(QLabel("S4:"), 6, 0)
        summary_layout.addWidget(self.LabelS4, 6, 1)
        control_layout.addWidget(summary)

        self.PushButtonTTConnect.clicked.connect(self.connect_tt)
        self.PushButtonTTDisconnect.clicked.connect(self.disconnect_tt)
        self.PushButtonTTApply.clicked.connect(self.apply_tt_parameters)
        self.PushButtonMeasureMatrix.clicked.connect(self.measure_matrix)
        self.PushButtonMeasureCounts.clicked.connect(self.measure_counts)
        self.PushButtonMeasureBellQuad.clicked.connect(self.measure_bell_quad)
        self.PushButtonMeasureCorrStep.clicked.connect(self.measure_corr_step)
        self.PushButtonMeasureCorrQuad.clicked.connect(self.measure_corr_quad)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(50)

    def _set_live_scan(self, checked: bool) -> None:
        self.config.live_scan = checked

    def _read_counts_from_adapter(self):
        if self.adapter is None or not self.adapter.is_connected():
            self.controller.update_state(self.controller.state.phase)
            return False

        try:
            raw = self.adapter.get_counter_data()
        except Exception as exc:  # pragma: no cover - runtime hardware path
            self.status_label.setText(f"Hardware read failed: {exc}")
            self.adapter = SimulatorAdapter()
            return False

        if raw is None or len(raw) < 2:
            self.controller.update_state(self.controller.state.phase)
            return False

        time_axis = np.asarray(raw[0], dtype=float)
        channel_data = [np.asarray(row, dtype=float) for row in raw[1:]]
        if not channel_data:
            self.controller.update_state(self.controller.state.phase)
            return False

        alice = channel_data[0] if len(channel_data) > 0 else np.zeros_like(time_axis)
        bob = channel_data[1] if len(channel_data) > 1 else np.zeros_like(time_axis)
        coin = channel_data[2] if len(channel_data) > 2 else np.zeros_like(time_axis)

        if time_axis.size:
            alice = alice[: time_axis.size]
            bob = bob[: time_axis.size]
            coin = coin[: time_axis.size]

        self.controller.state.phase = self.controller.state.phase
        self.controller.state.alice_counts = [float(v) for v in alice]
        self.controller.state.bob_counts = [float(v) for v in bob]
        self.controller.state.coin_counts = [float(v) for v in coin]
        self.controller.state.corr_values = [float(v) for v in np.asarray(self.adapter.get_corr_data()[0][1], dtype=float)]
        if self.controller.state.corr_values:
            self.controller.state.s_value = float(np.mean(self.controller.state.corr_values[:4]))
        else:
            self.controller.state.s_value = 0.0
        return True

    def _apply_adapter_settings(self) -> None:
        channels = [1, 2, 3, 4, 5, 6, 7, 8]
        if not self.adapter.is_connected():
            raise RuntimeError("Adapter is not connected")

        for channel in channels:
            delay_value = 0.0
            if channel <= 8:
                key = self.channel_labels[channel - 1]
                delay_field = getattr(self, f"LineEdit{key}Delay")
                try:
                    delay_value = float(delay_field.text())
                except ValueError:
                    delay_value = 0.0
            self.config.delays[channel] = delay_value
            self.adapter.setup_channel(channel, delay_value)

        self.adapter.setup_sm()
        self.adapter.setup_counters(channels, self.config.counts_binwidth, self.config.count_timeframe)
        self.adapter.setup_countrates(channels)
        alice_channels = [1, 2, 3, 4]
        bob_channels = [5, 6, 7, 8]
        self.adapter.setup_coincidences(alice_channels, bob_channels, self.config.coincidence_time_window)
        self.adapter.setup_correlations(alice_channels, bob_channels, self.config.corr_binwidth, self.config.corr_timeframe)

    def connect_tt(self) -> None:
        try:
            adapter = TimeTaggerAdapter()
            adapter.connect()
            self.adapter = adapter
            self.is_hardware_connected = True
            self.status_label.setText("TimeTagger connected")
        except Exception as exc:  # pragma: no cover - hardware may be unavailable in CI
            self.adapter = SimulatorAdapter()
            self.is_hardware_connected = False
            self.status_label.setText(f"TimeTagger unavailable, using simulator ({exc})")

    def disconnect_tt(self) -> None:
        if self.adapter is not None:
            try:
                self.adapter.disconnect()
            except Exception:
                pass
        self.adapter = SimulatorAdapter()
        self.is_hardware_connected = False
        self.status_label.setText("TimeTagger disconnected")

    def apply_tt_parameters(self) -> None:
        self.config.detector_angle = float(self.LineEditADelay.text() or 0.0)
        self.config.count_timeframe = float(self.LineEditCountsTimeFrame.text() or self.config.count_timeframe)
        self.config.counts_binwidth = float(self.LineEditCountsBinwidth.text() or self.config.counts_binwidth)
        self.config.coincidence_time_window = float(self.LineEditCoinTimeWindow.text() or self.config.coincidence_time_window)
        self.config.corr_binwidth = float(self.LineEditCorrBinwidth.text() or self.config.corr_binwidth)
        self.config.corr_timeframe = float(self.LineEditCorrTimeFrame.text() or self.config.corr_timeframe)
        self.config.matrix_integration_time = float(self.LineEditMatrixIntTime.text() or self.config.matrix_integration_time)

        if self.is_hardware_connected and self.adapter is not None:
            try:
                self._apply_adapter_settings()
                self.status_label.setText("TimeTagger configuration applied")
                return
            except Exception as exc:
                self.status_label.setText(f"TimeTagger configuration failed: {exc}")
                self.adapter = SimulatorAdapter()
                self.is_hardware_connected = False
                return

        self.status_label.setText("Simulation configuration applied")

    def measure_matrix(self) -> None:
        self.status_label.setText("Matrix saved")

    def measure_counts(self) -> None:
        self.status_label.setText("Counts saved")

    def measure_bell_quad(self) -> None:
        self.status_label.setText("Bell quad placeholder")

    def measure_corr_step(self) -> None:
        self.status_label.setText("Correlation step placeholder")

    def measure_corr_quad(self) -> None:
        self.status_label.setText("Correlation quad placeholder")

    def _reset_phase(self) -> None:
        self.controller.state.phase = 0.0

    def _measure_once(self) -> None:
        self.config.live_scan = False
        self.RadioButtonLiveData.setChecked(False)

    def _tick(self) -> None:
        phase = self.controller.state.phase
        if self.is_hardware_connected and self.adapter is not None:
            used_hardware = self._read_counts_from_adapter()
            if not used_hardware:
                self.controller.update_state(phase)
        else:
            self.controller.update_state(phase)

        t = np.linspace(0.0, self.config.count_timeframe, len(self.controller.state.alice_counts))
        alice = np.array(self.controller.state.alice_counts, dtype=float)
        bob = np.array(self.controller.state.bob_counts, dtype=float)
        coin = np.array(self.controller.state.coin_counts, dtype=float)
        corr = np.array(self.controller.state.corr_values, dtype=float)
        if corr.size == 0:
            corr = np.zeros(16, dtype=float)
        corr_t = np.arange(corr.size, dtype=float)

        if t.size == 0:
            t = np.linspace(0.0, self.config.count_timeframe, 1)
            alice = np.zeros(1)
            bob = np.zeros(1)
            coin = np.zeros(1)

        self.PlotSingle.set_data("alice", t, alice)
        self.PlotSingle.set_data("bob", t, bob)
        self.PlotSingle.set_range(x_range=(float(t.min()), float(t.max())), y_range=(0.0, max(float(alice.max()), float(bob.max())) * 1.3))

        self.PlotCoin.set_data("coin", t, coin)
        self.PlotCoin.set_range(x_range=(float(t.min()), float(t.max())), y_range=(0.0, max(float(coin.max()), 1.0) * 1.3))

        self.PlotCorr.set_data("corr", corr_t, corr)
        self.PlotCorr.set_range(x_range=(float(corr_t.min()), float(corr_t.max())), y_range=(0.0, max(float(corr.max()), 1.0) * 1.3))

        self.LabelAliceCountsPerSValue.setText(f"{alice.mean():.1f}")
        self.LabelBobCountsPerSValue.setText(f"{bob.mean():.1f}")
        self.LabelTotalCoin.setText(f"{coin.sum():.1f}")
        self.LabelS1.setText(f"{self.controller.state.s_value:.2f}")
        self.LabelS2.setText(f"{self.controller.state.s_value:.2f}")
        self.LabelS3.setText(f"{self.controller.state.s_value:.2f}")
        self.LabelS4.setText(f"{self.controller.state.s_value:.2f}")

        self.controller.state.phase += 0.03 if self.config.live_scan else 0.0
        self.status_label.setText(self.controller.summary_text())


def main() -> None:
    app = QApplication(sys.argv)
    window = SPDCMainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
