from __future__ import annotations

from PyQt6.QtCore import Qt
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

from qozy.core.data_model import TimeTaggerChannelSettings, TimeTaggerSettings
from qozy.core.settings_store import TimeTaggerSettingsStore
from qozy.gui.components import Card
from qozy.hardware.simulator import SimulatorAdapter
from qozy.hardware.timetagger_adapter import TimeTaggerAdapter


def _parse_channel_list(text: str) -> list[int]:
    channels: list[int] = []
    for part in text.split(","):
        part = part.strip()
        if part:
            channels.append(int(part))
    return channels


class TimeTaggerSettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.store = TimeTaggerSettingsStore()
        self.settings = self.store.load()
        self.adapter = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(18)

        title = QLabel("TimeTagger Settings")
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

    def _build_connection_card(self) -> QWidget:
        card = Card()
        form = QFormLayout(card)
        form.setContentsMargins(20, 20, 20, 20)
        form.setSpacing(12)

        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["Simulator", "TimeTagger (hardware)"])
        form.addRow("Backend", self.backend_combo)

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")
        self.connect_button.clicked.connect(self._connect_backend)
        self.disconnect_button.clicked.connect(self._disconnect_backend)
        row_layout.addWidget(self.connect_button)
        row_layout.addWidget(self.disconnect_button)
        form.addRow("Device", row)

        self.device_label = QLabel("Disconnected")
        self.device_label.setProperty("role", "muted")
        form.addRow("Status", self.device_label)
        return card

    def _build_channel_card(self) -> QWidget:
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(10)

        section = QLabel("Channel configuration")
        section.setObjectName("SectionTitle")
        card_layout.addWidget(section)

        self.channel_table = QTableWidget(8, 4)
        self.channel_table.setHorizontalHeaderLabels(
            ["Enabled", "Channel", "Delay (ns)", "Trigger (V)"]
        )
        self.channel_table.verticalHeader().setVisible(False)
        self.channel_table.horizontalHeader().setStretchLastSection(True)

        for row in range(8):
            enabled = QCheckBox()
            enabled.setChecked(True)
            enabled.setStyleSheet("margin-left: 14px;")
            self.channel_table.setCellWidget(row, 0, enabled)

            channel_item = QTableWidgetItem(str(row + 1))
            channel_item.setFlags(channel_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.channel_table.setItem(row, 1, channel_item)
            self.channel_table.setItem(row, 2, QTableWidgetItem("0.0"))
            self.channel_table.setItem(row, 3, QTableWidgetItem("0.1"))

        card_layout.addWidget(self.channel_table)
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

        form.addRow("Alice channels", self.alice_edit)
        form.addRow("Bob channels", self.bob_edit)
        form.addRow("Counts bin width (ms)", self.counts_bin_width_edit)
        form.addRow("Counts time frame (s)", self.counts_time_frame_edit)
        form.addRow("Coincidence window (ns)", self.coin_window_edit)
        form.addRow("Correlation bin width (ns)", self.corr_bin_width_edit)
        form.addRow("Correlation time frame (ns)", self.corr_time_frame_edit)
        form.addRow("Measurement time frame (s)", self.measure_time_frame_edit)
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

        row.addWidget(self.apply_button)
        row.addWidget(self.load_device_button)
        row.addWidget(self.save_button)
        row.addWidget(self.load_button)
        row.addWidget(self.reset_button)
        return card

    def _collect_settings(self) -> TimeTaggerSettings:
        mode = "hardware" if self.backend_combo.currentIndex() == 1 else "simulator"
        channels: list[TimeTaggerChannelSettings] = []
        for row in range(self.channel_table.rowCount()):
            enabled_widget = self.channel_table.cellWidget(row, 0)
            enabled = bool(enabled_widget and enabled_widget.isChecked())
            channel = int(self.channel_table.item(row, 1).text())
            delay_ns = float(self.channel_table.item(row, 2).text())
            trigger_level_v = float(self.channel_table.item(row, 3).text())
            channels.append(
                TimeTaggerChannelSettings(
                    channel=channel,
                    enabled=enabled,
                    delay_ns=delay_ns,
                    trigger_level_v=trigger_level_v,
                )
            )
        settings = TimeTaggerSettings(
            backend_mode=mode,
            channel_settings=channels,
            alice_channels=_parse_channel_list(self.alice_edit.text()),
            bob_channels=_parse_channel_list(self.bob_edit.text()),
            counts_bin_width_ms=float(self.counts_bin_width_edit.text()),
            counts_time_frame_s=float(self.counts_time_frame_edit.text()),
            coincidence_window_ns=float(self.coin_window_edit.text()),
            correlation_bin_width_ns=float(self.corr_bin_width_edit.text()),
            correlation_time_frame_ns=float(self.corr_time_frame_edit.text()),
            measure_time_frame_s=float(self.measure_time_frame_edit.text()),
        )
        return settings

    def _populate_ui(self, settings: TimeTaggerSettings) -> None:
        self.backend_combo.setCurrentIndex(1 if settings.backend_mode == "hardware" else 0)
        self.alice_edit.setText(", ".join(str(v) for v in settings.alice_channels))
        self.bob_edit.setText(", ".join(str(v) for v in settings.bob_channels))
        self.counts_bin_width_edit.setText(str(settings.counts_bin_width_ms))
        self.counts_time_frame_edit.setText(str(settings.counts_time_frame_s))
        self.coin_window_edit.setText(str(settings.coincidence_window_ns))
        self.corr_bin_width_edit.setText(str(settings.correlation_bin_width_ns))
        self.corr_time_frame_edit.setText(str(settings.correlation_time_frame_ns))
        self.measure_time_frame_edit.setText(str(settings.measure_time_frame_s))

        table_by_channel = {item.channel: item for item in settings.channel_settings}
        for row in range(self.channel_table.rowCount()):
            channel = row + 1
            item = table_by_channel.get(channel, TimeTaggerChannelSettings(channel=channel))
            enabled_widget = self.channel_table.cellWidget(row, 0)
            if enabled_widget is not None:
                enabled_widget.setChecked(item.enabled)
            self.channel_table.item(row, 2).setText(str(item.delay_ns))
            self.channel_table.item(row, 3).setText(str(item.trigger_level_v))

    def _connect_backend(self) -> None:
        try:
            if self.backend_combo.currentIndex() == 1:
                adapter = TimeTaggerAdapter()
            else:
                adapter = SimulatorAdapter()
            adapter.connect()
            self.adapter = adapter
            if hasattr(adapter, "get_device_info"):
                self.device_label.setText(adapter.get_device_info())
            else:
                self.device_label.setText("Connected")
            self.status_label.setText("Backend connected.")
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            self.adapter = None
            self.device_label.setText("Disconnected")
            self.status_label.setText(
                "Failed to connect backend: "
                f"{exc}. If you don't have hardware SDK installed, choose Simulator."
            )

    def _disconnect_backend(self) -> None:
        if self.adapter is None:
            self.device_label.setText("Disconnected")
            self.status_label.setText("No backend connection to close.")
            return
        try:
            self.adapter.disconnect()
            self.device_label.setText("Disconnected")
            self.status_label.setText("Backend disconnected.")
        except (OSError, RuntimeError, ValueError) as exc:
            self.status_label.setText(f"Failed to disconnect backend: {exc}")
        finally:
            self.adapter = None

    def _apply_settings(self) -> None:
        try:
            settings = self._collect_settings()
        except ValueError as exc:
            self.status_label.setText(f"Invalid settings value: {exc}")
            return

        errors = settings.validate()
        if errors:
            self.status_label.setText(f"Validation failed: {' | '.join(errors)}")
            return

        self.settings = settings
        self.store.save(settings)

        if self.adapter is None:
            self.status_label.setText("Settings saved. Connect a backend to apply immediately.")
            return

        try:
            self.adapter.setup_sm()
            enabled_channels = settings.enabled_channels()
            for channel in settings.channel_settings:
                if not channel.enabled:
                    continue
                self.adapter.setup_channel(
                    channel.channel, channel.delay_ns, channel.trigger_level_v
                )

            channel_list = enabled_channels or sorted(
                set(settings.alice_channels + settings.bob_channels)
            )
            self.adapter.setup_counters(
                channel_list,
                settings.counts_bin_width_ms,
                settings.counts_time_frame_s,
            )
            self.adapter.setup_countrates(channel_list)
            self.adapter.setup_coincidences(
                settings.alice_channels, settings.bob_channels, settings.coincidence_window_ns
            )
            self.adapter.setup_correlations(
                settings.alice_channels,
                settings.bob_channels,
                settings.correlation_bin_width_ns,
                settings.correlation_time_frame_ns,
            )
            self.status_label.setText("Settings applied to backend and saved.")
        except (OSError, RuntimeError, ValueError, AttributeError) as exc:
            self.status_label.setText(f"Failed to apply settings to backend: {exc}")

    def _save_settings(self) -> None:
        try:
            settings = self._collect_settings()
        except ValueError as exc:
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
        if self.adapter is None:
            self.status_label.setText("Connect a backend before loading device values.")
            return
        if not hasattr(self.adapter, "read_current_settings"):
            self.status_label.setText("This backend does not support device readback.")
            return
        try:
            settings = self.adapter.read_current_settings()
        except (OSError, RuntimeError, ValueError, AttributeError) as exc:
            self.status_label.setText(f"Failed to read settings from device: {exc}")
            return
        self.settings = settings
        self._populate_ui(settings)
        self.store.save(settings)
        self.status_label.setText("Loaded current values from backend and saved profile.")

    def _reset_defaults(self) -> None:
        self.settings = TimeTaggerSettings()
        self._populate_ui(self.settings)
        self.status_label.setText("Reset to default TimeTagger settings.")
