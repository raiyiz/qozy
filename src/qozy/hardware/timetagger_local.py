"""Local USB Swabian Time Tagger backend."""

from __future__ import annotations

from qozy.hardware.timetagger_adapter import TimeTaggerAdapter


class LocalTimeTagger(TimeTaggerAdapter):
    """Connect to a Time Tagger attached to this computer over USB."""

    def __init__(self) -> None:
        super().__init__(address=None)
