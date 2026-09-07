"""Shared state and acquisition strategies for live Bell measurements."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

import numpy as np

from qozy.core.bell_math import BELL_ANGLES_DEG, calc_e_s, e_readiness
from qozy.hardware.base import MeasurementAdapter, PositionerAdapter


class BellAcquisitionMode(str, Enum):
    """Supported ways of populating the Bell coincidence matrix."""

    SEQUENTIAL = "sequential"
    SIMULTANEOUS = "simultaneous"


@dataclass
class BellAcquisitionOptions:
    """Settings for a Bell acquisition strategy."""

    mode: BellAcquisitionMode = BellAcquisitionMode.SEQUENTIAL
    integration_time_s: float = 0.5


@dataclass(frozen=True)
class BellChannelMap:
    """Map coincidence-channel indices to Bell matrix cells."""

    coincidence_indices: dict[tuple[int, int], int]

    def __post_init__(self) -> None:
        for (row, col), index in self.coincidence_indices.items():
            if not (0 <= row < 4 and 0 <= col < 4):
                raise ValueError(f"invalid Bell matrix cell ({row}, {col})")
            if index < 0:
                raise ValueError(f"invalid coincidence-channel index {index}")

    @property
    def cells(self) -> tuple[tuple[int, int], ...]:
        return tuple(self.coincidence_indices)

    @classmethod
    def row_major(cls, count: int = 16) -> BellChannelMap:
        if not 0 <= count <= 16:
            raise ValueError("count must be between 0 and 16")
        return cls(
            {
                (row, col): row * 4 + col
                for row in range(4)
                for col in range(4)
                if row * 4 + col < count
            }
        )


class BellMatrixAccumulator:
    """Own raw Bell coincidence counts and derived E/S values."""

    def __init__(self) -> None:
        self.matrix = np.zeros((4, 4), dtype=float)
        self.filled = np.zeros((4, 4), dtype=bool)

    def reset(self) -> None:
        self.matrix.fill(0.0)
        self.filled.fill(False)

    def update_cell(self, row: int, col: int, value: float) -> None:
        if not 0 <= row < 4 or not 0 <= col < 4:
            raise IndexError(f"invalid Bell matrix cell ({row}, {col})")
        self.matrix[row, col] = float(value)
        self.filled[row, col] = True

    def update_matrix(self, matrix: np.ndarray, filled: np.ndarray | None = None) -> None:
        values = np.asarray(matrix, dtype=float)
        if values.shape != (4, 4):
            raise ValueError(f"expected a 4x4 matrix, got {values.shape}")
        self.matrix[:, :] = values
        if filled is None:
            self.filled.fill(True)
            return
        mask = np.asarray(filled, dtype=bool)
        if mask.shape != (4, 4):
            raise ValueError(f"expected a 4x4 filled mask, got {mask.shape}")
        self.filled[:, :] = mask

    def normalized_matrix(self) -> np.ndarray:
        result = self.matrix.copy()
        measured = result[self.filled]
        maximum = float(np.max(measured)) if measured.size else 0.0
        if maximum > 0.0:
            result /= maximum
        return result

    def e_values(self) -> np.ndarray:
        return calc_e_s(self.matrix)[0]

    def s_values(self) -> np.ndarray:
        return calc_e_s(self.matrix)[1]

    def e_readiness(self) -> np.ndarray:
        return e_readiness(self.filled)

    def s_ready(self) -> bool:
        return bool(self.e_readiness().all())


@dataclass(frozen=True)
class BellUpdate:
    """Snapshot returned by a Bell acquisition strategy after an update."""

    matrix: np.ndarray
    filled: np.ndarray
    row: int | None = None
    col: int | None = None
    completed: bool = False
    done: bool = False


class BellAcquisition(Protocol):
    """Worker-facing interface shared by Bell acquisition strategies."""

    @property
    def done(self) -> bool: ...

    @property
    def matrix(self) -> BellMatrixAccumulator: ...

    def start(self, total_counts: object) -> BellUpdate: ...

    def update(self, total_counts: object) -> BellUpdate: ...


class SequentialBellAcquisition:
    """Cycle through Bell settings and integrate one matrix cell at a time."""

    def __init__(
        self,
        adapter: MeasurementAdapter,
        alice_stage: PositionerAdapter,
        bob_stage: PositionerAdapter,
        alice_channels: list[int],
        bob_channels: list[int],
        config: BellAcquisitionOptions | None = None,
        settings_deg: tuple[float, ...] = BELL_ANGLES_DEG,
    ) -> None:
        self.adapter = adapter
        self.alice_stage = alice_stage
        self.bob_stage = bob_stage
        self.alice_channels = alice_channels
        self.bob_channels = bob_channels
        self.options = config or BellAcquisitionOptions()
        self.settings_deg = settings_deg
        self.matrix = BellMatrixAccumulator()
        self.row = 0
        self.col = 0
        self._baseline = 0.0
        self._started_at = 0.0
        self._done = False
        self._set_angle_context = getattr(adapter, "set_angle_context", None)

    @property
    def done(self) -> bool:
        return self._done

    @property
    def completed_cells(self) -> int:
        return self.row * len(self.settings_deg) + self.col if not self._done else len(self.settings_deg) ** 2

    def start(self, total_counts: object) -> BellUpdate:
        self.row = 0
        self.col = 0
        self.matrix.reset()
        self._done = False
        self._move_to_current_cell()
        self._baseline = self._coincidence_total(self.adapter.get_total_counts())
        self._started_at = time.monotonic()
        return self._snapshot(completed=False)

    def update(self, total_counts: object) -> BellUpdate:
        if self._done:
            return self._snapshot(completed=True)

        value = max(0.0, self._coincidence_total(total_counts) - self._baseline)
        self.matrix.update_cell(self.row, self.col, value)
        if time.monotonic() - self._started_at < self.options.integration_time_s:
            return self._snapshot(completed=False)

        completed_row, completed_col = self.row, self.col
        if self.col == len(self.settings_deg) - 1:
            if self.row == len(self.settings_deg) - 1:
                self._done = True
                return self._snapshot(
                    completed=True, row=completed_row, col=completed_col
                )
            self.row += 1
            self.col = 0
        else:
            self.col += 1

        self._move_to_current_cell()
        self._baseline = self._coincidence_total(self.adapter.get_total_counts())
        self._started_at = time.monotonic()
        return self._snapshot(completed=True, row=completed_row, col=completed_col)

    def _snapshot(
        self,
        completed: bool,
        row: int | None = None,
        col: int | None = None,
    ) -> BellUpdate:
        return BellUpdate(
            self.matrix.matrix.copy(),
            self.matrix.filled.copy(),
            self.row if row is None else row,
            self.col if col is None else col,
            completed,
            self._done,
        )

    def _move_to_current_cell(self) -> None:
        a_angle = self.settings_deg[self.row]
        b_angle = self.settings_deg[self.col]
        self.alice_stage.set_angle(a_angle)
        self.bob_stage.set_angle(b_angle)
        if self._set_angle_context is not None:
            self._set_angle_context(a_angle, b_angle)

    def _coincidence_total(self, total_counts: object) -> float:
        values = np.asarray(total_counts, dtype=float).reshape(-1)
        offset = len(self.alice_channels) + len(self.bob_channels)
        count = len(self.alice_channels) * len(self.bob_channels)
        if values.size < offset + count:
            raise ValueError(
                "Sequential Bell acquisition requires cumulative coincidence totals "
                "from the configured acquisition"
            )
        return float(np.sum(values[offset : offset + count]))


@dataclass(frozen=True)
class SequentialBellState:
    """Current progress of a sequential Bell scan."""

    row: int
    col: int
    elapsed_s: float
    integration_time_s: float
    completed_cells: int
    total_cells: int


class SequentialBellAcquisition:
    """Cycle the 16 polarization settings over an existing acquisition.

    The acquisition itself remains owned by ``MeasurementController``. This
    object only moves stages and interprets cumulative coincidence counts, so
    every worker poll can update the currently active matrix cell.
    """

    def __init__(
        self,
        adapter: MeasurementAdapter,
        alice_stage: PositionerAdapter,
        bob_stage: PositionerAdapter,
        alice_channels: list[int],
        bob_channels: list[int],
        settings_deg: Sequence[float] = BELL_ANGLES_DEG,
        integration_time_s: float = 0.5,
    ) -> None:
        if len(settings_deg) != 4:
            raise ValueError("a Bell acquisition requires four polarization settings")
        if integration_time_s <= 0:
            raise ValueError("integration_time_s must be positive")
        self.adapter = adapter
        self.alice_stage = alice_stage
        self.bob_stage = bob_stage
        self.alice_channels = alice_channels
        self.bob_channels = bob_channels
        self.settings_deg = tuple(float(angle) for angle in settings_deg)
        self.integration_time_s = float(integration_time_s)
        self.matrix = BellMatrixAccumulator()
        self.row = 0
        self.col = 0
        self._baseline = 0.0
        self._started_at = 0.0
        self._done = False
        self._set_angle_context = getattr(adapter, "set_angle_context", None)

    @property
    def done(self) -> bool:
        return self._done

    def start(self, total_counts: object) -> BellUpdate:
        self.matrix.reset()
        self._done = False
        return self.update(total_counts)

    def update(self, total_counts: object) -> BellUpdate:
        values = np.asarray(total_counts, dtype=float).reshape(-1)
        required = [
            self.coincidence_offset + index
            for index in self.channel_map.coincidence_indices.values()
        ]
        if required and values.size <= max(required):
            raise ValueError(
                "Sequential Bell acquisition requires cumulative coincidence totals "
                "from the configured acquisition"
            )
        for cell, index in self.channel_map.coincidence_indices.items():
            self.matrix.update_cell(*cell, values[self.coincidence_offset + index])
        return BellUpdate(
            self.matrix.matrix.copy(), self.matrix.filled.copy(), done=False
        )

    def stop(self) -> None:
        self._done = True


# Backwards-compatible alias while callers migrate from the old name.
LiveBellScan = SequentialBellAcquisition
