"""Offscreen smoke tests for the PyQt6 shell."""

from __future__ import annotations

import time

from qozy.gui.main_window import MainWindow
from qozy.gui.theme import THEMES, apply_theme


def _pump(qapp, duration_s: float = 0.5) -> None:
    deadline = time.monotonic() + duration_s
    while time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)


def _page(window, index: int):
    return window.pages.widget(index)


def test_main_window_builds_all_pages(qapp) -> None:
    apply_theme(qapp, "classic-light")
    window = MainWindow(qapp)
    assert window.pages.count() == 7
    assert _page(window, 1).__class__.__name__ == "TimeTaggerSettingsPage"
    window.select_page(1)
    assert window.pages.currentIndex() == 1


def test_theme_button_cycles_all_four_themes(qapp) -> None:
    window = MainWindow(qapp)
    assert len(THEMES) == 6
    assert window.mode == "classic-light"
    for expected in ("classic-dark", "soft-dark", "soft-light", "classic-light"):
        window.cycle_theme()
        assert window.mode == expected
        assert THEMES[window.mode][0] in window.theme_button.text()


def test_timetagger_page_owns_hardware_connection(qapp) -> None:
    window = MainWindow(qapp)
    page = _page(window, 1)
    assert page.hardware is window.hardware
    assert page.connect_button.text() == "Disconnect"
    assert page.device_label.text() == "Simulator backend"
    page._toggle_connection()
    _pump(qapp, 0.25)
    assert not window.hardware.connected
    assert page.connect_button.text() == "Connect"
    page.backend_combo.setCurrentIndex(0)
    page._toggle_connection()
    _pump(qapp, 0.25)
    assert window.hardware.connected
    assert page.connect_button.text() == "Disconnect"


def test_timetagger_apply_updates_hardware_manager(qapp) -> None:
    window = MainWindow(qapp)
    page = _page(window, 1)
    counts_page = _page(window, 3)
    page.alice_edit.setText("5, 6")
    page.bob_edit.setText("7, 8")
    page.channel_table.item(4, 2).setText("3.5")
    page.channel_table.item(4, 3).setText("0.2")
    page._apply_settings()
    _pump(qapp, 0.25)
    assert window.hardware.timetagger_settings.alice_channels == [5, 6]
    assert window.hardware.timetagger_settings.bob_channels == [7, 8]
    assert counts_page.alice_edit.text() == "5, 6"
    assert counts_page.bob_edit.text() == "7, 8"
    assert window.hardware.timetagger_settings.channel_delay_map()[5] == 3.5


def test_counts_page_start_stop_cycle_updates_bell_summary(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    counts_page._start()
    _pump(qapp, 0.25)
    assert counts_page._worker is not None
    assert counts_page.live_checkbox.isChecked()
    counts_page._stop()
    _pump(qapp, 0.25)
    assert counts_page._worker is None
    assert counts_page._thread is None
    assert counts_page.status_label.text() == "Stopped"
    assert counts_page.start_button.isEnabled()


def test_counts_page_remains_responsive_during_acquisition(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    counts_page._start()
    states = []
    for _ in range(10):
        qapp.processEvents()
        states.append(counts_page.status_label.text())
        time.sleep(0.02)
    assert counts_page._worker is not None
    assert counts_page.status_label.text().startswith("Acquiring")
    assert any(state.startswith("Acquiring") for state in states)
    counts_page._stop()
    _pump(qapp, 0.25)
    assert counts_page._worker is None


def test_counts_page_bell_scan_updates_summary(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    counts_page._run_bell_scan()
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)
    assert counts_page.status_label.text() == "Scan complete"
    assert counts_page.bell_e_label.text() != "E: —"


def test_counts_page_bell_scan_uses_hardware_manager_stages(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    alice_stage, bob_stage = counts_page._bell_scan_stages()
    assert alice_stage is window.hardware.stages["alice"]
    assert bob_stage is window.hardware.stages["bob"]


def test_counts_page_bell_scan_requires_connected_stages(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    polarization_page = _page(window, 2)
    polarization_page._toggle_stage_connection("alice")
    _pump(qapp, 0.25)
    assert not window.hardware.stage_connected["alice"]
    counts_page._run_bell_scan()
    assert counts_page.status_label.text().startswith("Error: connect both polarization stages")
    assert counts_page._scan_thread is None


def test_counts_page_bell_scan_freezes_hardware_pages(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    polarization_page = _page(window, 2)
    timetagger_page = _page(window, 1)
    counts_page._run_bell_scan()
    assert not timetagger_page.connect_button.isEnabled()
    assert not polarization_page._stage_widgets["alice"]["connect"].isEnabled()
    assert not polarization_page._stage_widgets["bob"]["connect"].isEnabled()
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)
    assert timetagger_page.connect_button.isEnabled()
    assert polarization_page._stage_widgets["alice"]["connect"].isEnabled()
    assert polarization_page._stage_widgets["bob"]["connect"].isEnabled()


def test_counts_page_save_scan_button_disabled_until_scan_completes(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    assert not counts_page.save_scan_button.isEnabled()
    counts_page._run_bell_scan()
    assert not counts_page.save_scan_button.isEnabled()
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)
    assert counts_page.save_scan_button.isEnabled()


def test_counts_page_save_scan_writes_file_to_settings_export_dir(qapp, tmp_path) -> None:
    from qozy.core.export import day_folder

    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    settings_page = _page(window, 0)
    settings_page.export_dir.setText(str(tmp_path))
    counts_page._run_bell_scan()
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)
    counts_page.save_scan_button.click()
    assert list(day_folder(tmp_path).glob("*.txt"))
    assert counts_page.status_label.text().startswith("Saved to")


def test_counts_page_auto_save_writes_file_without_clicking_save(qapp, tmp_path) -> None:
    from qozy.core.export import day_folder

    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    settings_page = _page(window, 0)
    settings_page.export_dir.setText(str(tmp_path))
    counts_page.auto_save_checkbox.setChecked(True)
    counts_page._run_bell_scan()
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text().startswith("Scan complete"):
            break
        time.sleep(0.05)
    assert list(day_folder(tmp_path).glob("*.txt"))
    assert counts_page.status_label.text().startswith("Scan complete — saved to")


def test_polarization_page_controls_simulator_polarization_stages(qapp) -> None:
    window = MainWindow(qapp)
    polarization_page = _page(window, 2)
    alice = polarization_page._stage_widgets["alice"]
    alice["target"].setText("22.5")
    polarization_page._move_stage("alice")
    _pump(qapp, 0.25)
    assert alice["angle"].text() == "22.50°"
    assert alice["status"].text() == "Connected"
    polarization_page._toggle_stage_connection("alice")
    _pump(qapp, 0.25)
    assert alice["status"].text() == "Disconnected"
    assert alice["connect"].text() == "Connect"
    polarization_page._toggle_stage_connection("alice")
    _pump(qapp, 0.25)
    assert alice["status"].text() == "Connected"
    assert alice["connect"].text() == "Disconnect"


def test_polarization_page_bell_angle_preset_moves_stage(qapp) -> None:
    window = MainWindow(qapp)
    polarization_page = _page(window, 2)
    bob = polarization_page._stage_widgets["bob"]
    button = next(b for b in bob["presets"] if b.text() == "67.5°")
    button.click()
    _pump(qapp, 0.25)
    assert bob["angle"].text() == "67.50°"
    assert bob["target"].text() == "67.50"


def test_polarization_page_presets_disabled_while_disconnected(qapp) -> None:
    window = MainWindow(qapp)
    polarization_page = _page(window, 2)
    alice = polarization_page._stage_widgets["alice"]
    polarization_page._toggle_stage_connection("alice")
    _pump(qapp, 0.25)
    assert alice["status"].text() == "Disconnected"
    assert all(not button.isEnabled() for button in alice["presets"])


def test_settings_export_dir_propagates_to_counts_page(qapp) -> None:
    window = MainWindow(qapp)
    settings_page = _page(window, 0)
    counts_page = _page(window, 3)
    settings_page.export_dir.setText("/tmp/custom_export")
    assert counts_page._export_dir == "/tmp/custom_export"


def test_main_window_persists_config_across_restarts(qapp, tmp_path) -> None:
    window = MainWindow(qapp)
    timetagger_page = _page(window, 1)
    timetagger_page.alice_edit.setText("5, 6")
    timetagger_page.save_button.click()
    counts_page = _page(window, 3)
    counts_page.auto_save_checkbox.setChecked(True)
    settings_page = _page(window, 0)
    settings_page.export_dir.setText("/tmp/qozy_export")
    polarization_page = _page(window, 2)
    polarization_page._stage_widgets["alice"]["address"].setText("2")
    window.close()
    assert (tmp_path / "config.json").exists()
    window2 = MainWindow(qapp)
    assert window2.pages.widget(1).alice_edit.text() == "5, 6"
    assert window2.pages.widget(3).auto_save_checkbox.isChecked()
    assert window2.pages.widget(0).export_dir.text() == "/tmp/qozy_export"
    assert window2.pages.widget(2)._stage_widgets["alice"]["address"].text() == "2"


def test_closing_without_saving_does_not_touch_timetagger_profile(qapp, tmp_path) -> None:
    """``MainWindow.closeEvent`` always saves the automatic ``AppConfig``,
    but must never silently persist the Time Tagger settings *profile* —
    only explicit Save profile / Apply to backend actions do that (see
    ``TimeTaggerSettingsPage.export_config``'s docstring)."""
    window = MainWindow(qapp)
    timetagger_page = _page(window, 1)
    timetagger_page.alice_edit.setText("7, 8")  # edited, but never saved/applied

    window.close()

    assert not (tmp_path / "timetagger_settings.json").exists()
    assert (tmp_path / "config.json").exists()
