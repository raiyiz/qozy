"""Only one QApplication can exist per process, so it's a session-scoped
fixture here rather than something each GUI test creates itself.

QT_QPA_PLATFORM=offscreen is set before PyQt6 is imported anywhere so Qt
never tries to open a real display — required for CI and for this sandbox.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def isolated_persisted_files(tmp_path, monkeypatch):
    """Every test gets its own throwaway paths for both on-disk stores QOZY
    writes outside the repo — ``AppConfig`` (automatic, saved on every
    window close) and the Time Tagger settings profile (explicit
    Save/Apply only) — so the suite can never read or overwrite whatever
    real files happen to exist at ``~/.qozy/...`` on the machine running
    it. Individual tests are still free to pass their own explicit path to
    ``load_config``/``save_config``/``TimeTaggerSettingsStore``; this only
    changes what the no-argument defaults resolve to.
    """
    monkeypatch.setattr("qozy.core.app_config.DEFAULT_CONFIG_PATH", tmp_path / "config.json")
    monkeypatch.setattr(
        "qozy.core.settings_store.DEFAULT_SETTINGS_PATH",
        tmp_path / "timetagger_settings.json",
    )
