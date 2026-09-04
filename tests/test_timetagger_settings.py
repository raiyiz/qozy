from qozy.core.data_model import TimeTaggerSettings
from qozy.core.settings_store import TimeTaggerSettingsStore
from qozy.hardware.simulator import SimulatorAdapter


def test_timetagger_settings_validation_rejects_overlap() -> None:
    settings = TimeTaggerSettings(alice_channels=[1, 2], bob_channels=[2, 4])
    errors = settings.validate()
    assert any("distinct" in e for e in errors)


def test_timetagger_settings_store_roundtrip(tmp_path) -> None:
    path = tmp_path / "settings.json"
    store = TimeTaggerSettingsStore(path)
    settings = TimeTaggerSettings(
        backend_mode="simulator",
        alice_channels=[1, 5],
        bob_channels=[2, 6],
        counts_bin_width_ms=50.0,
        coincidence_window_ns=3.2,
    )
    store.save(settings)
    loaded = store.load()
    assert loaded.alice_channels == [1, 5]
    assert loaded.bob_channels == [2, 6]
    assert loaded.counts_bin_width_ms == 50.0
    assert loaded.coincidence_window_ns == 3.2


def test_simulator_read_current_settings_reflects_config() -> None:
    adapter = SimulatorAdapter(seed=0)
    adapter.connect()
    adapter.setup_sm()
    adapter.setup_channel(1, delay=4.5, trigger_level_v=0.2)
    adapter.setup_counters([1, 2, 3], counts_bin_width_ms=50.0, counts_time_frame_s=2.0)
    adapter.setup_coincidences([1, 2], [3, 4], coin_time_window_ns=2.5)
    adapter.setup_correlations([1, 2], [3, 4], corr_bin_width_ns=1.5, corr_time_frame_ns=90.0)

    settings = adapter.read_current_settings()
    assert settings.backend_mode == "simulator"
    assert settings.alice_channels == [1, 2]
    assert settings.bob_channels == [3, 4]
    assert settings.counts_bin_width_ms == 50.0
    assert settings.counts_time_frame_s == 2.0
    assert settings.coincidence_window_ns == 2.5
    assert settings.correlation_bin_width_ns == 1.5
    assert settings.correlation_time_frame_ns == 90.0
    first = settings.channel_settings[0]
    assert first.channel == 1
    assert first.delay_ns == 4.5
    assert first.trigger_level_v == 0.2
