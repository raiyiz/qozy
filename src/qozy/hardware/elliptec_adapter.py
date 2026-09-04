"""Thorlabs Elliptec rotator adapter (ELL14/ELL18-class rotation mounts),
used to set the Alice/Bob polarization angles for a Bell scan.

Uses the ``elliptec`` PyPI package (https://pypi.org/project/elliptec/):
``elliptec.Controller(port=...)`` opens the serial connection shared by all
rotators on that port; ``elliptec.Rotator(controller, address=...)`` talks
to one physical stage by its bus address. Both ``Rotator.set_angle()`` and
``.home()`` block on the device's own serial response, so there's no
separate "wait until settled" step needed here — the call returning means
the move finished.

Like ``TimeTaggerAdapter``, the vendor library is imported lazily inside
``connect()`` so importing this module never requires ``elliptec`` (or a
connected device) to be installed.
"""

from __future__ import annotations


class ElliptecAdapter:
    """One rotator on a shared Elliptec serial bus.

    ``port`` is the serial device (e.g. ``"/dev/ttyUSB0"``); ``address`` is
    the rotator's bus address as a single hex-digit string (``"0"``,
    ``"1"``, ...) — set on the device itself, not chosen here. Two of
    these, on the same or different ports, make up Alice's and Bob's
    stages.
    """

    def __init__(self, port: str, address: str = "0") -> None:
        self.port = port
        self.address = address
        self._controller = None
        self._rotator = None

    def connect(self) -> None:
        import elliptec

        self._controller = elliptec.Controller(port=self.port)
        self._rotator = elliptec.Rotator(self._controller, address=self.address)

    def disconnect(self) -> None:
        if self._controller is not None:
            self._controller.close_connection()

    def home(self) -> None:
        self._rotator.home()

    def get_angle(self) -> float:
        angle = self._rotator.get_angle()
        if angle is None:
            raise RuntimeError(
                f"Elliptec rotator at {self.port}:{self.address} did not report an angle"
            )
        return angle

    def set_angle(self, angle_deg: float) -> float:
        angle = self._rotator.set_angle(angle_deg)
        if angle is None:
            raise RuntimeError(
                f"Elliptec rotator at {self.port}:{self.address} did not confirm move to {angle_deg}°"
            )
        return angle
