"""Network Time Tagger backend."""

from __future__ import annotations

from qozy.hardware.timetagger_adapter import TimeTaggerAdapter


class NetworkTimeTagger(TimeTaggerAdapter):
    """Connect to a Swabian Network Time Tagger server."""

    def __init__(self, address: str) -> None:
        address = address.strip()
        if not address:
            raise ValueError("A Network Time Tagger server address is required")
        super().__init__(address=address)
