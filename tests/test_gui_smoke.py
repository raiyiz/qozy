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


def _layout_items(layout):
    return [layout.itemAt(i) for i in range(layout.count())]


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


def test_counts_page_bell_scan_updates_matrix_plot(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    counts_page._run_bell_scan()
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)

    # the placeholder axis is turned back on and titled with the E/S text
    # once a real matrix is drawn
    assert counts_page.bell_plot._ax.get_title() != ""


def _run_live_cycles(qapp, counts_page, min_cycles: int, timeout: float = 5.0) -> None:
    """Enable the live-loop checkbox, start a scan, and pump events until
    at least ``min_cycles`` have completed (or the timeout elapses)."""
    counts_page.live_scan_checkbox.setChecked(True)
    counts_page._run_bell_scan()
    deadline = time.time() + timeout
    while time.time() < deadline and counts_page._scan_cycle_count < min_cycles:
        qapp.processEvents()
        time.sleep(0.01)


def _stop_live_scan(qapp, counts_page, timeout: float = 5.0) -> None:
    """Uncheck the live-loop box and pump events until the loop has
    genuinely stopped. Every live-loop test must call this before
    finishing -- ideally from a try/finally -- or a loop left running
    keeps firing into whatever test runs next against the same
    session-scoped ``qapp``, which showed up for real once: a failed
    assertion skipped this cleanup, and the next test's window got a
    'wrapped C/C++ object has been deleted' error from the orphaned
    loop still trying to update a QLabel that no longer existed."""
    counts_page.live_scan_checkbox.setChecked(False)
    deadline = time.time() + timeout
    while time.time() < deadline:
        qapp.processEvents()
        if not counts_page._live_scan_running and counts_page._scan_thread is None:
            break
        time.sleep(0.01)


def test_counts_page_live_scan_loops_multiple_cycles_and_stops_when_unchecked(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)

    try:
        _run_live_cycles(qapp, counts_page, min_cycles=3)
        assert counts_page._scan_cycle_count >= 3, "loop should keep running cycles unattended"
        assert counts_page._live_scan_running
        assert not counts_page.scan_button.isEnabled()
        stopped_at = counts_page._scan_cycle_count
    finally:
        _stop_live_scan(qapp, counts_page)

    assert not counts_page._live_scan_running
    assert counts_page._scan_thread is None
    assert counts_page.scan_button.isEnabled()
    assert counts_page.start_button.isEnabled()
    # at most one more cycle (already in flight when unchecked) completes
    assert stopped_at <= counts_page._scan_cycle_count <= stopped_at + 1
    assert counts_page.status_label.text() == f"Live scan stopped after cycle {counts_page._scan_cycle_count}"


def test_counts_page_fresh_scan_after_live_loop_resets_cycle_state(qapp) -> None:
    """A brand-new "Run Bell scan" click must not be mistaken for a loop
    continuation and skip resetting the cycle count/history -- this would
    happen if _live_scan_running were ever left True after a loop
    genuinely stopped."""
    window = MainWindow(qapp)
    counts_page = _page(window, 3)

    try:
        _run_live_cycles(qapp, counts_page, min_cycles=2)
    finally:
        _stop_live_scan(qapp, counts_page)
    assert not counts_page._live_scan_running

    counts_page._run_bell_scan()
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)

    assert counts_page._scan_cycle_count == 1
    assert len(counts_page._s_history) == 1


def test_counts_page_live_scan_accumulates_instead_of_resetting_each_cycle(qapp) -> None:
    """The whole point of the live loop: the displayed matrix keeps
    growing cycle after cycle (a longer-integrated measurement should
    have larger counts), rather than resetting to a fresh, independent,
    noisier reading every cycle -- and it must never flash back to the
    "Run a Bell scan to see the matrix" placeholder in between."""
    window = MainWindow(qapp)
    counts_page = _page(window, 3)

    # single-shot mode is unaffected: each press is independent, no
    # accumulation, matching every existing single-shot test
    counts_page._run_bell_scan()
    for _ in range(50):
        qapp.processEvents()
        if counts_page._scan_thread is None and counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)
    single_shot_value = float(counts_page.bell_table.item(0, 0).text())

    try:
        counts_page.live_scan_checkbox.setChecked(True)
        counts_page._run_bell_scan()
        deadline = time.time() + 5
        cell_values_after_each_cycle = []
        last_cycle_seen = 0
        while time.time() < deadline and len(cell_values_after_each_cycle) < 3:
            qapp.processEvents()
            if counts_page._scan_cycle_count > last_cycle_seen:
                last_cycle_seen = counts_page._scan_cycle_count
                cell_values_after_each_cycle.append(float(counts_page.bell_table.item(0, 0).text()))
                # the placeholder text is never shown again once a live
                # loop has real data -- no flash back to it between cycles
                assert counts_page.bell_plot._ax.get_title() != ""
            time.sleep(0.01)
    finally:
        _stop_live_scan(qapp, counts_page)

    assert len(cell_values_after_each_cycle) >= 3
    # strictly increasing: cycle 2's total is more than cycle 1's, etc.
    assert cell_values_after_each_cycle == sorted(cell_values_after_each_cycle)
    assert cell_values_after_each_cycle[0] < cell_values_after_each_cycle[-1]
    # roughly single_shot_value * cycle count, since each cycle adds
    # about the same amount (same simulator, same integration time)
    assert cell_values_after_each_cycle[-1] > single_shot_value * 2


def test_counts_page_bell_history_plot_updates_after_each_cycle(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)

    try:
        _run_live_cycles(qapp, counts_page, min_cycles=3)
    finally:
        _stop_live_scan(qapp, counts_page)

    assert len(counts_page._s_history) >= 3
    assert counts_page.bell_history_plot._ax.lines
    title = counts_page.bell_history_plot._ax.get_title()
    assert f"cycle {len(counts_page._s_history)}" in title


def test_counts_page_bell_summary_updates_live_and_honestly(qapp) -> None:
    """E/S must be calculated as data comes in, not only once the scan
    finishes -- but each value should only appear once it's actually
    derivable from real measurements (see bell_math.e_readiness), not
    computed from a matrix still padded with not-yet-measured zeros."""
    window = MainWindow(qapp)
    counts_page = _page(window, 3)

    assert counts_page.bell_e_label.text() == "E: —, —, —, —"
    assert counts_page.bell_s_label.text() == "S: —, —, —, —"

    e_texts: list[str] = []
    s_texts: list[str] = []
    original = counts_page._render_bell_summary

    def spy(e, s, e_ready):
        original(e, s, e_ready)
        e_texts.append(counts_page.bell_e_label.text())
        s_texts.append(counts_page.bell_s_label.text())

    counts_page._render_bell_summary = spy
    counts_page._run_bell_scan()
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)

    # S never appears until every E does -- it's never partially shown
    for e_text, s_text in zip(e_texts[:-1], s_texts[:-1], strict=True):
        if "—" in e_text:
            assert s_text == "S: —, —, —, —"

    # by the end, both are fully populated with real numbers
    assert "—" not in e_texts[-1]
    assert "—" not in s_texts[-1]
    assert "max |S| =" in s_texts[-1]


def test_counts_page_bell_scan_updates_heatmap_live_per_cell(qapp) -> None:
    """The heatmap should update as each of the 16 settings completes, not
    only once at the very end -- and each of those live updates must show
    the not-yet-measured cells as still pending rather than plotted as if
    they were real zero-count readings."""
    window = MainWindow(qapp)
    counts_page = _page(window, 3)

    live_titles: list[str] = []
    filled_counts: list[int] = []
    original = counts_page.bell_plot.update_matrix

    def spy(matrix, filled=None, e=None, s=None):
        original(matrix, filled=filled, e=e, s=s)
        live_titles.append(counts_page.bell_plot._ax.get_title())
        if filled is not None:
            filled_counts.append(int(filled.sum()))

    counts_page.bell_plot.update_matrix = spy
    counts_page._run_bell_scan()
    for _ in range(50):
        qapp.processEvents()
        if counts_page.status_label.text() == "Scan complete":
            break
        time.sleep(0.05)

    # 16 live per-cell updates plus the final completed-scan update
    assert len(live_titles) == 17
    assert filled_counts == list(range(1, 17))
    assert live_titles[0] == "Scanning…  1/16 settings measured"
    assert live_titles[-2] == "Scanning…  16/16 settings measured"
    assert "Scanning" not in live_titles[-1]
    assert "E1=" in live_titles[-1]


def test_counts_page_bell_table_and_plot_are_stacked_without_a_gap(qapp) -> None:
    """A stretch item once ended up between the coincidence table and its
    own heatmap (see git history: 'small: fixed spacing between titles and
    objects on the counts page' briefly pushed the heatmap away from the
    table it illustrates). Pin the layout order down so it can't regress
    silently again."""
    window = MainWindow(qapp)
    counts_page = _page(window, 3)

    table_col = counts_page.bell_table.parentWidget().layout().itemAt(0).layout()
    widget_classes = [
        item.widget().__class__.__name__ for item in _layout_items(table_col) if item.widget()
    ]
    stretch_positions = [i for i, item in enumerate(_layout_items(table_col)) if item.spacerItem()]

    assert widget_classes == ["QLabel", "QTableWidget", "BellMatrixPlot"]
    # the stretch must come after every widget in the column, not between
    # the table and the plot
    assert stretch_positions and stretch_positions[0] == table_col.count() - 1


def test_counts_page_save_scan_also_writes_quick_analysis_svg(qapp, tmp_path) -> None:
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

    svg_files = list(tmp_path.rglob("*_quick_analysis.svg"))
    txt_files = list(tmp_path.rglob("*.txt"))
    assert len(svg_files) == 1
    assert len(txt_files) == 1
    assert svg_files[0].stat().st_size > 0
    assert "quick-analysis SVG" in counts_page.status_label.text()


def test_counts_page_live_acquisition_shows_coincidence_rate(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = _page(window, 3)

    counts_page._start()
    for _ in range(20):
        qapp.processEvents()
        if counts_page.coincidence_rate_label.text() != "Coincidence rate: —":
            break
        time.sleep(0.05)
    counts_page._stop()
    _pump(qapp, 0.25)

    assert counts_page.coincidence_rate_label.text() != "Coincidence rate: —"
    assert counts_page.total_coincidences_label.text() != "Total coincidences: —"


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
    # unfreezing happens once this cycle's QThread has actually finished
    # (_on_scan_thread_finished), a tick after the "Scan complete" status
    # text is set (_on_scan_finished) -- wait for the actual unfreeze, not
    # just the status text, so this isn't racy against that gap.
    for _ in range(50):
        qapp.processEvents()
        if timetagger_page.connect_button.isEnabled():
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


def test_counts_page_is_wrapped_in_a_scroll_area(qapp) -> None:
    """A small window (or a lot of vertical content, like the live-loop
    history graph next to the matrix and table) must scroll rather than
    silently clip content with no way to reach it."""
    from PyQt6.QtWidgets import QScrollArea

    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    assert isinstance(counts_page.layout().itemAt(0).widget(), QScrollArea)


def test_counts_page_bell_table_columns_have_a_fixed_width(qapp) -> None:
    """Accumulated live-loop counts grow to more digits over a long run;
    the column must not keep widening to fit them and reflow the rest of
    the row beside it."""
    from PyQt6.QtWidgets import QTableWidgetItem

    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    width_before = counts_page.bell_table.columnWidth(0)
    counts_page.bell_table.setItem(0, 0, QTableWidgetItem("123456789"))
    assert counts_page.bell_table.columnWidth(0) == width_before


def test_counts_page_status_label_has_a_fixed_height(qapp) -> None:
    """Prevents the Settings card (and everything below it) from jumping
    vertically as the live-loop status text changes length every cycle."""
    window = MainWindow(qapp)
    counts_page = _page(window, 3)
    height_before = counts_page.status_label.height()
    counts_page.status_label.setText(
        "Live — cycle 123 complete (max |S| = 2.83), starting next…"
    )
    assert counts_page.status_label.height() == height_before
