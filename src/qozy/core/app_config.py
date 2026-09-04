"""Persisted "last used" GUI field values.

This only covers what the user actually types or selects in Settings,
Polarization, and Counts — acquisition backend, network/serial addresses,
detector channels, export directory — never live connection state, which
always starts fresh (see the GUI threading rule in ``docs/architecture.md``:
we never want to auto-reconnect to real hardware on startup without the
user pressing Connect).

Deliberately no Qt here, same as the rest of ``qozy.core``: the config is a
plain JSON file so loading/saving can be unit tested without a display, and
so a missing or corrupt file can never stop QOZY from starting — it just
falls back to defaults.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / ".qozy" / "config.json"


@dataclass
class StageConfig:
    """Last-used polarization-stage backend selection."""

    backend: str = "simulator"
    port: str = ""
    address: str = "0"


@dataclass
class AppConfig:
    """Everything the GUI pre-fills its widgets from at startup."""

    acquisition_backend: str = "simulator"
    network_address: str = "localhost:41101"
    export_dir: str = "~/qozy_data"
    alice_stage: StageConfig = field(default_factory=lambda: StageConfig(address="0"))
    bob_stage: StageConfig = field(default_factory=lambda: StageConfig(address="1"))
    alice_channels: str = "1, 2"
    bob_channels: str = "3, 4"


def load_config(path: Path | None = None) -> AppConfig:
    """Load the persisted config, falling back to defaults on any problem.

    Covers a missing file (first run), a corrupt file, and a file written
    by an older/newer schema — none of those should ever stop QOZY from
    starting, so they all just fall back to ``AppConfig()``.
    """
    path = path or DEFAULT_CONFIG_PATH
    try:
        raw = json.loads(path.read_text())
    except (OSError, ValueError):
        return AppConfig()

    if not isinstance(raw, dict):
        return AppConfig()

    try:
        alice_raw = raw.pop("alice_stage", {}) or {}
        bob_raw = raw.pop("bob_stage", {}) or {}
        stage_fields = {f.name for f in fields(StageConfig)}
        config_fields = {f.name for f in fields(AppConfig)}
        config = AppConfig(**{k: v for k, v in raw.items() if k in config_fields})
        config.alice_stage = StageConfig(**{k: v for k, v in alice_raw.items() if k in stage_fields})
        config.bob_stage = StageConfig(**{k: v for k, v in bob_raw.items() if k in stage_fields})
        return config
    except (TypeError, ValueError):
        return AppConfig()


def save_config(config: AppConfig, path: Path | None = None) -> None:
    """Write ``config`` to ``path`` as JSON, creating the parent directory."""
    path = path or DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(config), indent=2))
