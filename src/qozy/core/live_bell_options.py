"""Configuration for optional continuous Bell-matrix updates."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LiveBellOptions:
    enabled: bool = False
    normalize: bool = True
    update_s: bool = True
