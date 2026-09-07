# Live Bell acquisition plan

## Goal

Support two explicit Bell acquisition workflows while sharing one live coincidence-matrix and Bell-metric pipeline:

1. **Sequential scan** — cycle Alice/Bob through the 16 Bell settings and integrate one cell at a time. The current cell updates continuously during its integration; previously completed cells remain visible.
2. **Simultaneous channels** — acquire multiple Bell coincidence channels at once. Every mapped matrix cell updates continuously from the same acquisition stream; no polarization cycling is performed.

Both modes must make the active workflow obvious in the GUI and provide live matrix, E, and S updates. Matrix normalization is display-only and must never alter the raw counts used for E/S.

## Architecture

```text
CountsPage
    |
    +-- SequentialBellAcquisition
    |       `-- stage cycling + integration state
    |
    +-- SimultaneousBellAcquisition
    |       `-- coincidence-channel -> matrix-cell mapping
    |
    `-- BellMatrixAccumulator
            +-- raw 4x4 coincidence matrix
            +-- filled/available cells
            +-- E values + readiness
            `-- S values + readiness
```

### `BellMatrixAccumulator` — new

Location: `src/qozy/core/bell_acquisition.py`.

Own the raw 4x4 matrix and derived Bell quantities. It must be independent of Qt and hardware. It provides cell/matrix updates, reset, normalized display data, E/S values, and readiness. Normalization is never applied to stored raw counts.

### `BellAcquisitionMode` — new

An enum with `SEQUENTIAL` and `SIMULTANEOUS`. The GUI and worker use this instead of ambiguous boolean flags.

### `BellAcquisitionOptions` — new/update

Stores acquisition-specific options such as mode and sequential integration time. Display options remain separate.

### `BellChannelMap` — new

Explicitly maps coincidence-channel indices to `(row, col)` matrix cells. This prevents simultaneous acquisition from depending on an implicit offset/order hidden in the GUI and permits partial mappings.

### `BellAcquisition` — new protocol

Common worker-facing interface implemented by both acquisition strategies. The worker should not need to know which strategy it is running.

### `SequentialBellAcquisition` — new/refactor of `LiveBellScan`

Own stage movement, current row/column, integration timing, cumulative-count baselines, and completion. It reports intermediate current-cell values on every poll and completed-cell transitions separately.

### `SimultaneousBellAcquisition` — new

Own the mapping from cumulative coincidence channels to all mapped matrix cells. It never moves stages and remains active until the generic acquisition is stopped.

### `AcquisitionWorker` — update

Remain responsible for the controller lifecycle and polling loop. Accept the common Bell acquisition interface, feed every `MeasurementState`/total-count snapshot into it, and emit unified Bell updates. It must not contain Bell equations or GUI logic.

### `CountsPage` — update

Expose an explicit Bell acquisition mode selector and status. Sequential mode shows current Alice/Bob settings, cell progress, and integration progress. Simultaneous mode shows channel/mapping status. Both render the same live matrix and E/S views.

### `BellMatrixPlot` — update

Render the current matrix and, for sequential acquisition, highlight the active cell. It remains visualization-only.

### `bell_math.py` — small refactor

Remain the mathematical authority (`calc_e_s`, `e_readiness`). The GUI should consume results through the accumulator rather than calculating E/S itself on every signal.

### `Simulator` — update

Support both workflows with the same observable count behavior as real hardware: angle-dependent coincidence generation for sequential operation and multiple mapped coincidence channels for simultaneous operation.

### `MeasurementController` — minimal/no Bell-specific logic

Continue to own generic hardware configuration/start/poll/stop. It should not know which Bell acquisition strategy is selected.

## GUI behavior

### Sequential

Display e.g.:

> Bell acquisition · Sequential  
> Alice: D · Bob: A  
> Cell 11 / 16 · 6.4 / 10.0 s

The active matrix cell changes continuously while it is being integrated. E values become ready as their required 2x2 blocks are complete; S becomes ready when all required E values are available.

### Simultaneous

Display e.g.:

> Bell acquisition · Simultaneous  
> 16 coincidence channels active  
> Acquiring…

All mapped cells update continuously. There is no artificial current cell.

## Data flow

```text
raw cumulative coincidence counts
            |
            +--> Bell acquisition strategy
            |       |
            |       `--> cell/matrix updates
            |
            `--> BellMatrixAccumulator
                    |
                    +--> raw matrix --> E/S
                    `--> display matrix --> optional normalization
```

## Persistence

Save raw matrix counts, acquisition mode, relevant channel/stage configuration, and E/S derived from raw counts. Do not persist only a normalized matrix.

## Implementation order

1. Add accumulator, acquisition mode/options, channel map, and common protocol.
2. Refactor `LiveBellScan` into `SequentialBellAcquisition` with structured live state.
3. Add unit tests for accumulator and both acquisition strategies.
4. Generalize `AcquisitionWorker` to the common interface.
5. Add explicit sequential/simultaneous GUI controls and live rendering.
6. Update simulator for simultaneous multi-channel behavior.
7. Refactor/remove old Bell worker/scan paths.
8. Update persistence.
9. Run Ruff/tests and verify both workflows with simulator and hardware.

## Commit strategy

Keep commits small and focused. Each implementation commit should state the most important architectural piece completed so the PR history remains readable.
