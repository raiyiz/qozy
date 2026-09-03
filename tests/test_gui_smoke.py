"""Offscreen smoke tests for the PyQt6 shell.

These don't assert on pixels — they build the real window, drive the
Counts page's start/stop cycle against the simulator, and pump the Qt
event loop, which is enough to catch wiring bugs like the cross-thread
QTimer bug this caught during development (see comments in
qozy/gui/worker.py and qozy/gui/pages/counts_page.py).
"""

from __future__ import annotations

import time

from qozy.gui.main_window import MainWindow
from qozy.gui.theme import apply_theme


def test_main_window_builds_all_pages(qapp) -> None:
    apply_theme(qapp, "light")
    window = MainWindow(qapp)
    assert window.pages.count() == 5
    window.select_page(1)
    assert window.pages.currentIndex() == 1


def test_counts_page_start_stop_cycle_updates_bell_summary(qapp) -> None:
    window = MainWindow(qapp)
    counts_page = window.pages.widget(1)

    counts_page._start()
    for _ in range(5):
        qapp.processEvents()
        time.sleep(0.05)
    qapp.processEvents()

    counts_page._stop()
    qapp.processEvents()

    assert counts_page.status_label.text() == "Stopped"
    # the simulator's get_coincidence_matrix() should have driven at least
    # one Bell-summary update while acquiring
    assert counts_page.bell_e_label.text() != "E: —"
    assert "not available" not in counts_page.bell_e_label.text()
