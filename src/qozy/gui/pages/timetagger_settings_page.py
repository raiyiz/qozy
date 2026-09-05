"""Dedicated Time Tagger configuration and connection page."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from qozy.core.app_config import AppConfig
from qozy.core.data_model import TimeTaggerChannelSettings, TimeTaggerSettings
from qozy.core.settings_store import TimeTaggerSettingsStore
from qozy.gui.components import Card
from qozy.gui.hardware_worker import HardwareWorker
from qozy.hardware.manager import BackendName, HardwareManager


class TimeTaggerSettingsPage(QWidget):
    """Own all Time Tagger connection, input, and acquisition settings."""

    adapter_ready = pyqtSignal(object)
    connection_changed = pyqtSignal(bool)
    settings_changed = pyqtSignal(object)

    _BACKENDS: tuple[tuple[str, BackendName], ...] = (
        ("Simulator", "simulator"),
        ("Time Tagger (local)", "timetagger-local"),
        ("Time Tagger (network)", "timetagger-network"),
    )

    def __init__(self, hardware: HardwareManager, initial: AppConfig | None = None) -> None:
        super().__init__()
        self.hardware = hardware
        self._initial = initial or AppConfig()
        self.store = TimeTaggerSettingsStore()
        self.settings = self.store.load()
        self._thread: QThread | None = None
        self._worker: HardwareWorker | None = None
        self._busy = False

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)
        title = QLabel("Time Tagger Settings")
        title.setObjectName("PageTitle")
        root.addWidget(title)
        root.addWidget(self._build_connection_card())
        root.addWidget(self._build_channel_card())
        root.addWidget(self._build_acquisition_card())
        root.addWidget(self._build_actions_card())
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        self.status_label.setProperty("role", "muted")
        root.addWidget(self.status_label)
        root.addStretch()

        self._populate_ui(self.settings)
        self._restore_backend_selection()
        self._update_device_status()
        self._update_connection_controls()

    def export_config(self, config: AppConfig) -> None:
        config.acquisition_backend = self._selected_backend()
        config.network_address = self.network_address.text().strip() or config.network_address
        try:
            settings = self._collect_settings()
        except (TypeError, ValueError):
            return
        if settings.validate():
            return
        self.settings = settings
        self.store.save(settings)

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._update_connection_controls()
        if busy:
            for widget in self._config_widgets():
                widget.setEnabled(False)

    def _config_widgets(self) -> tuple[QWidget, ...]:
        return (
            self.backend_combo,
            self.network_address,
            self.channel_table,
            self.alice_edit,
            self.bob_edit,
            self.counts_bin_width_edit,
            self.counts_time_frame_edit,
            self.coin_window_edit,
            self.corr_bin_width_edit,
            self.corr_time_frame_edit,
            self.measure_time_frame_edit,
            self.apply_button,
            self.load_device_button,
            self.save_button,
            self.load_button,
            self.reset_button,
        )

    def _build_connection_card(self) -> QWidget:
        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        self.backend_combo = QComboBox()
        for label, _ in self._BACKENDS:
            self.backend_combo.addItem(label)
        self.backend_combo.currentIndexChanged.connect(self._backend_changed)
        form.addRow("Backend", self.backend_combo)

        self.network_address = QLineEdit(
            self._initial.network_address or self.hardware.network_address
        )
        self.network_address.setPlaceholderText("host:41101")
        form.addRow("Network server", self.network_address)

        self.connect_button = QPushButton("Disconnect" if self.hardware.connected else "Connect")
        self.connect_button.setObjectName("Primary")
        self.connect_button.clicked.connect(self._toggle_connection)
        form.addRow("Device", self.connect_button)

        self.device_label = QLabel("Disconnected")
        self.device_label.setProperty("role", "muted")
        form.addRow("Status", self.device_label)
        return card

    def _build_channel_card(self) -> QWidget:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        section = QLabel("Channel configuration")
        section.setObjectName("SectionTitle")
        layout.addWidget(section)
        self.channel_table = QTableWidget(8, 4)
        self.channel_table.setHorizontalHeaderLabels(
            ["Enabled", "Channel", "Delay (ns)", "Trigger (V)"]
        )
        self.channel_table.verticalHeader().setVisible(False)
        self.channel_table.horizontalHeader().setStretchLastSection(True)
        for row in range(8):
            enabled = QCheckBox()
            enabled.setChecked(True)
            self.channel_table.setCellWidget(row, 0, enabled)
            item = QTableWidgetItem(str(row + 1))
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.channel_table.setItem(row, 1, item)
            self.channel_table.setItem(row, 2, QTableWidgetItem("0.0"))
            self.channel_table.setItem(row, 3, QTableWidgetItem("0.1"))
        layout.addWidget(self.channel_table)
        return card

    def _build_acquisition_card(self) -> QWidget:
        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)
        self.alice_edit = QLineEdit("1, 2")
        self.bob_edit = QLineEdit("3, 4")
        self.counts_bin_width_edit = QLineEdit("100.0")
        self.counts_time_frame_edit = QLineEdit("5.0")
        self.coin_window_edit = QLineEdit("2.0")
        self.corr_bin_width_edit = QLineEdit("1.0")
        self.corr_time_frame_edit = QLineEdit("1000.0")
        self.measure_time_frame_edit = QLineEdit("1.0")
        for label, widget in (
            ("Alice channels", self.alice_edit),
            ("Bob channels", self.bob_edit),
            ("Counts bin width (ms)", self.counts_bin_width_edit),
            ("Counts time frame (s)", self.counts_time_frame_edit),
            ("Coincidence window (ns)", self.coin_window_edit),
            ("Correlation bin width (ns)", self.corr_bin_width_edit),
            ("Correlation time frame (ns)", self.corr_time_frame_edit),
            ("Measurement time frame (s)", self.measure_time_frame_edit),
        ):
            form.addRow(label, widget)
        return card

    def _build_actions_card(self) -> QWidget:
        card = Card()
        row = QHBoxLayout(card)
        row.setContentsMargins(20, 14, 20, 14)
        row.setSpacing(10)
        self.apply_button = QPushButton("Apply to backend")
        self.apply_button.setObjectName("Primary")
        self.load_device_button = QPushButton("Load from device")
        self.save_button = QPushButton("Save profile")
        self.load_button = QPushButton("Load profile")
        self.reset_button = QPushButton("Reset defaults")
        self.apply_button.clicked.connect(self._apply_settings)
        self.load_device_button.clicked.connect(self._load_from_device)
        self.save_button.clicked.connect(self._save_settings)
        self.load_button.clicked.connect(self._load_settings)
        self.reset_button.clicked.connect(self._reset_defaults)
        for button in (
            self.apply_button,
            self.load_device_button,
            self.save_button,
            self.load_button,
            self.reset_button,
        ):
            row.addWidget(button)
        return card

    def _restore_backend_selection(self) -> None:
        names = [name for _, name in self._BACKENDS]
        if self._initial.acquisition_backend in names:
            self.backend_combo.setCurrentIndex(names.index(self._initial.acquisition_backend))

    def _selected_backend(self) -> BackendName:
        return self._BACKENDS[self.backend_combo.currentIndex()][1]

    def _backend_changed(self, _index: int) -> None:
        self._update_connection_controls()

    def _update_device_status(self) -> None:
        if not self.hardware.connected:
            self.device_label.setText("Disconnected")
            self.connect_button.setText("Connect")
            return
        info = getattr(self.hardware.adapter, "get_device_info", None)
        try:
            self.device_label.setText(info() if info else "Connected")
        except Exception:  # noqa: BLE001
            self.device_label.setText("Connected")
        self.connect_button.setText("Disconnect")

    def _update_connection_controls(self) -> None:
        if self._thread is not None:
            self.connect_button.setEnabled(False)
            return
        connected = self.hardware.connected
        if not self._busy:
            for widget in self._config_widgets():
                widget.setEnabled(True)
        self.backend_combo.setEnabled(not connected and not self._busy)
        self.network_address.setEnabled(
            not connected and not self._busy and self._selected_backend() == "timetagger-network"
        )
        self.connect_button.setEnabled(not self._busy)
        self.connect_button.setText("Disconnect" if connected else "Connect")

    def _toggle_connection(self) -> None:
        if self._thread is not None or self._busy:
            return
        if self.hardware.connected:
            self._start_hardware_worker("disconnect")
            return
        backend = self._selected_backend()
        address = self.network_address.text().strip()
        if backend == "timetagger-network" and not address:
            self.status_label.setText("Error: enter a network server address")
            return
        try:
            self.hardware.select(backend, address)
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Error: {exc}")
            return
        self._start_hardware_worker("connect")

    def _start_hardware_worker(
        self, action: str, settings: TimeTaggerSettings | None = None
    ) -> None:
        self._thread = QThread()
        self._worker = HardwareWorker(self.hardware, action, settings)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.connected.connect(self._on_connected)
        self._worker.disconnected.connect(self._on_disconnected)
        self._worker.result.connect(self._on_worker_result)
        self._worker.error.connect(self._on_worker_error)
        self._worker.connected.connect(self._thread.quit)
        self._worker.disconnected.connect(self._thread.quit)
        self._worker.result.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._on_worker_finished)
        self.connect_button.setEnabled(False)
        labels = {
            "connect": "Connecting…",
            "disconnect": "Disconnecting…",
            "configure_timetagger": "Applying settings…",
            "read_timetagger_settings": "Reading device…",
        }
        self.status_label.setText(labels.get(action, "Working…"))
        self._thread.start()

    def _on_connected(self, adapter: object) -> None:
        self._update_device_status()
        self.adapter_ready.emit(adapter)
        self.connection_changed.emit(True)
        self.status_label.setText(
            "Time Tagger connected. Apply the current settings to configure it."
        )

    def _on_disconnected(self) -> None:
        self._update_device_status()
        self.connection_changed.emit(False)
        self.status_label.setText("Time Tagger disconnected.")

    def _on_worker_result(self, result: object) -> None:
        if isinstance(result, TimeTaggerSettings):
            self.settings = result
            self._populate_ui(result)
            self.store.save(result)
            self.settings_changed.emit(result)
            self.status_label.setText("Time Tagger settings applied/read successfully.")

    def _on_worker_error(self, message: str) -> None:
        self.status_label.setText(f"Hardware error: {message}")
        self._update_device_status()

    def _on_worker_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._update_connection_controls()

    @staticmethod
    def _parse_channel_list(text: str) -> list[int]:
        return [int(part.strip()) for part in text.split(",") if part.strip()]

    def _collect_settings(self) -> TimeTaggerSettings:
        channels: list[TimeTaggerChannelSettings] = []
        for row in range(self.channel_table.rowCount()):
            enabled = self.channel_table.cellWidget(row, 0)
            channels.append(
                TimeTaggerChannelSettings(
                    channel=int(self.channel_table.item(row, 1).text()),
                    enabled=bool(enabled and enabled.isChecked()),
                    delay_ns=float(self.channel_table.item(row, 2).text()),
                    trigger_level_v=float(self.channel_table.item(row, 3).text()),
                )
            )
        return TimeTaggerSettings(
            backend_mode="simulator" if self._selected_backend() == "simulator" else "hardware",
            channel_settings=channels,
            alice_channels=self._parse_channel_list(self.alice_edit.text()),
            bob_channels=self._parse_channel_list(self.bob_edit.text()),
            counts_bin_width_ms=float(self.counts_bin_width_edit.text()),
            counts_time_frame_s=float(self.counts_time_frame_edit.text()),
            coincidence_window_ns=float(self.coin_window_edit.text()),
            correlation_bin_width_ns=float(self.corr_bin_width_edit.text()),
            correlation_time_frame_ns=float(self.corr_time_frame_edit.text()),
            measure_time_frame_s=float(self.measure_time_frame_edit.text()),
        )

    def _populate_ui(self, settings: TimeTaggerSettings) -> None:
        self.alice_edit.setText(", ".join(map(str, settings.alice_channels)))
        self.bob_edit.setText(", ".join(map(str, settings.bob_channels)))
        self.counts_bin_width_edit.setText(str(settings.counts_bin_width_ms))
        self.counts_time_frame_edit.setText(str(settings.counts_time_frame_s))
        self.coin_window_edit.setText(str(settings.coincidence_window_ns))
        self.corr_bin_width_edit.setText(str(settings.correlation_bin_width_ns))
        self.corr_time_frame_edit.setText(str(settings.correlation_time_frame_ns))
        self.measure_time_frame_edit.setText(str(settings.measure_time_frame_s))
        by_channel = {item.channel: item for item in settings.channel_settings}
        for row in range(self.channel_table.rowCount()):
            item = by_channel.get(row + 1, TimeTaggerChannelSettings(channel=row + 1))
            enabled = self.channel_table.cellWidget(row, 0)
            if enabled is not None:
                enabled.setChecked(item.enabled)
            self.channel_table.item(row, 2).setText(str(item.delay_ns))
            self.channel_table.item(row, 3).setText(str(item.trigger_level_v))

    def _apply_settings(self) -> None:
        try:
            settings = self._collect_settings()
        except (TypeError, ValueError) as exc:
            self.status_label.setText(f"Invalid settings value: {exc}")
            return
        errors = settings.validate()
        if errors:
            self.status_label.setText(f"Validation failed: {' | '.join(errors)}")
            return
        self.settings = settings
        self.store.save(settings)
        if not self.hardware.connected:
            self.status_label.setText("Settings saved. Connect a backend before applying them.")
            return
        self._start_hardware_worker("configure_timetagger", settings)

    def _save_settings(self) -> None:
        try:
            settings = self._collect_settings()
        except (TypeError, ValueError) as exc:
            self.status_label.setText(f"Invalid settings value: {exc}")
            return
        errors = settings.validate()
        if errors:
            self.status_label.setText(f"Validation failed: {' | '.join(errors)}")
            return
        self.settings = settings
        self.store.save(settings)
        self.status_label.setText(f"Settings saved to {self.store.path}.")

    def _load_settings(self) -> None:
        self.settings = self.store.load()
        self._populate_ui(self.settings)
        self.status_label.setText(f"Settings loaded from {self.store.path}.")

    def _load_from_device(self) -> None:
        if not self.hardware.connected:
            self.status_label.setText("Connect a backend before loading device values.")
            return
        if not hasattr(self.hardware.adapter, "read_current_settings"):
            self.status_label.setText("This backend does not support device readback.")
            return
        self._start_hardware_worker("read_timetagger_settings")

    def _reset_defaults(self) -> None:
        self.settings = TimeTaggerSettings()
        self._populate_ui(self.settings)
        self.status_label.setText("Reset to default Time Tagger settings. Click Apply to use them.")
