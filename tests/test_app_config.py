from __future__ import annotations

from qozy.core.app_config import AppConfig, StageConfig, load_config, save_config


def test_load_config_missing_file_returns_defaults(tmp_path) -> None:
    config = load_config(tmp_path / "does-not-exist.json")
    assert config == AppConfig()


def test_save_then_load_round_trips(tmp_path) -> None:
    path = tmp_path / "config.json"
    original = AppConfig(
        acquisition_backend="timetagger-network",
        network_address="tagger.example:41101",
        export_dir="/data/qozy",
        alice_stage=StageConfig(backend="elliptec", port="/dev/ttyUSB0", address="0"),
        bob_stage=StageConfig(backend="elliptec", port="/dev/ttyUSB1", address="1"),
        alice_channels="1, 2, 5",
        bob_channels="3, 4",
        auto_save_scan=True,
    )
    save_config(original, path)

    loaded = load_config(path)
    assert loaded == original


def test_save_config_creates_parent_directory(tmp_path) -> None:
    path = tmp_path / "nested" / "config.json"
    save_config(AppConfig(), path)
    assert path.exists()


def test_load_config_falls_back_to_defaults_on_corrupt_file(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text("not valid json {")
    assert load_config(path) == AppConfig()


def test_load_config_falls_back_to_defaults_on_unexpected_shape(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text('"just a string, not an object"')
    assert load_config(path) == AppConfig()


def test_load_config_ignores_unknown_fields(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"acquisition_backend": "simulator", "future_field": 123}')
    config = load_config(path)
    assert config.acquisition_backend == "simulator"
