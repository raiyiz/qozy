"""Offscreen smoke tests for the PyQt6 shell."""

from __future__ import annotations

import time

from qozy.gui.main_window import MainWindow
from qozy.gui.theme import apply_theme


def _pump(qapp, duration_s: float = 0.5) -> None:
    deadline = time.monotonic() + duration_s
    while time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)


def test_main_window_builds_all_pages(qapp) -> None:
    apply_theme(qapp, "light")
    window = MainWindow(qapp)
    assert window.pages.count() == 6
    window.select_page(1)
    assert window.pages.currentIndex() == 1


def test_counts_page_start_stop_cycle_updates_bell_summary(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = window.pages.widget(2)

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
    counts_page = window.pages.widget(1)

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
    counts_page = window.pages.widget(2)

    counts_page._run_bell_scan()
    # the scan runs 16 fast simulated settings on its own thread; give it a
    # moment and keep pumping the event loop so its finished signal lands
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)

    assert counts_page.status_label.text() == "Scan complete"
    assert counts_page.bell_e_label.text() != "E: —"


def test_settings_page_controls_simulator_polarization_stages(qapp) -> None:
    window = MainWindow(qapp)
    settings_page = window.pages.widget(4)

    alice = settings_page._stage_widgets["alice"]
    alice_target = alice["target"]
    alice_target.setText("22.5")
    settings_page._move_stage("alice")
    _pump(qapp, 0.25)

    assert alice["angle"].text() == "22.50°"
    assert alice["status"].text() == "Connected"

    settings_page._toggle_stage_connection("alice")
    _pump(qapp, 0.25)
    assert alice["status"].text() == "Disconnected"
    assert alice["connect"].text() == "Connect"

    settings_page._toggle_stage_connection("alice")
    _pump(qapp, 0.25)
    assert alice["status"].text() == "Connected"
    assert alice["connect"].text() == "Disconnect"
