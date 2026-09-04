from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from qozy.core.data_model import TimeTaggerChannelSettings, TimeTaggerSettings


class TimeTaggerSettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path.home() / ".qozy_timetagger_settings.json"

    def load(self) -> TimeTaggerSettings:
        if not self.path.exists():
            return TimeTaggerSettings()
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        channels = [
            TimeTaggerChannelSettings(**item) for item in raw.get("channel_settings", [])
        ] or [TimeTaggerChannelSettings(channel=i) for i in range(1, 9)]
        return TimeTaggerSettings(
            backend_mode=raw.get("backend_mode", "simulator"),
            channel_settings=channels,
            alice_channels=list(raw.get("alice_channels", [1, 2])),
            bob_channels=list(raw.get("bob_channels", [3, 4])),
            counts_bin_width_ms=float(raw.get("counts_bin_width_ms", 100.0)),
            counts_time_frame_s=float(raw.get("counts_time_frame_s", 5.0)),
            coincidence_window_ns=float(raw.get("coincidence_window_ns", 2.0)),
            correlation_bin_width_ns=float(raw.get("correlation_bin_width_ns", 1.0)),
            correlation_time_frame_ns=float(raw.get("correlation_time_frame_ns", 1000.0)),
            measure_time_frame_s=float(raw.get("measure_time_frame_s", 1.0)),
        )

    def save(self, settings: TimeTaggerSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
