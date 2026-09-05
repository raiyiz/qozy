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
