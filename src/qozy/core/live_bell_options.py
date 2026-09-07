"""Display options for continuous Bell-matrix updates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LiveBellOptions:
    """UI policy for rendering the Bell scan while acquisition is running."""

    enabled: bool = False
    normalize: bool = True
    update_s: bool = True
