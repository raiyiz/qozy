# QOZY architecture

QOZY is split into a hardware-independent measurement core, hardware adapters,
and a PyQt6 GUI. The important boundary is that GUI pages never need to know
which vendor backend is underneath them.

```text
src/qozy/
├── app.py                         # console entry point
├── core/
│   ├── bell_math.py              # Bell/CHSH calculations and angle constants
│   ├── data_model.py             # measurement configuration/state dataclasses
│   ├── controller.py             # MeasurementController
│   ├── scan_controller.py        # hardware-independent 4×4 Bell angle scan
│   └── export.py                 # measurement export helpers
├── hardware/
│   ├── base.py                   # MeasurementAdapter + PositionerAdapter protocols
│   ├── manager.py                # process-wide acquisition/stage ownership
│   ├── simulator.py              # simulator acquisition + simulator stages
│   ├── timetagger_adapter.py     # Swabian TimeTagger SDK adapter
│   ├── timetagger_local.py       # local TimeTagger backend
│   ├── timetagger_network.py     # network TimeTagger backend
│   └── elliptec_adapter.py       # Thorlabs Elliptec rotator adapter
└── gui/
    ├── theme.py                  # four QOZY visual presets
    ├── components.py             # reusable Qt widgets
    ├── main_window.py            # sidebar + page stack + theme cycling
    ├── hardware_worker.py        # background connection/stage operations
    ├── worker.py                 # background live acquisition
    ├── scan_worker.py            # background Bell scan
    ├── plot_panel.py             # VisPy live plotting
    └── pages/
        ├── settings_page.py      # hardware configuration and controls
        ├── counts_page.py        # live acquisition + Bell scan UI
        ├── polytope_page.py      # placeholder
        ├── heralded_g2_page.py   # placeholder
        └── state_tomography_page.py # placeholder
```

## Core / hardware boundary

`core/` has no Qt imports and no vendor-SDK imports. It receives small
interfaces instead of concrete devices.

`hardware/base.py` defines two protocols:

- `MeasurementAdapter` for photon-counting/time-tagging measurements.
- `PositionerAdapter` for polarization stages (`connect`, `disconnect`,
  `home`, `get_angle`, `set_angle`).

`MeasurementController` only consumes `MeasurementAdapter`. `BellScanController`
consumes one `MeasurementAdapter` plus Alice and Bob `PositionerAdapter`s.
This keeps both workflows testable with the simulator implementations.

## HardwareManager

`hardware/manager.py` is the central owner of connected hardware and contains
no Qt code. It maintains:

```text
HardwareManager
├── acquisition
│   ├── SimulatorAdapter
│   ├── LocalTimeTagger
│   └── NetworkTimeTagger
└── polarization stages
    ├── Alice → SimulatorStage or ElliptecAdapter
    └── Bob   → SimulatorStage or ElliptecAdapter
```

The default state is a connected simulator acquisition backend and two
connected simulator stages. A stage can be reconfigured only after it has
been disconnected.

For Elliptec, each stage stores a serial port and a single device/bus address.
The adapter supports either separate serial controllers or multiple rotators
sharing one controller/port, because the underlying constructor receives both
`port` and `address`.

## GUI threading rule

Potentially blocking vendor operations must not run on the Qt GUI thread.
Settings therefore delegates acquisition connection/disconnection to
`HardwareWorker` and stage connect/disconnect/move/home/position reads to
`StageWorker`. Live acquisition uses `AcquisitionWorker`; the Bell scan uses
`ScanWorker`.

Workers are one-shot or long-running background jobs owned by `QThread`. The
GUI does not call `QThread.wait()` during normal stop handling. Live acquisition
uses a thread-safe `threading.Event` stop request so the worker can leave its
loop without relying on a queued Qt callback being processed by a busy worker
thread.

## Settings page

Settings is the hardware/configuration page rather than an experiment page.
It currently contains:

### Acquisition

- backend: Simulator, Time Tagger (local), or Time Tagger (network)
- network server address for the network backend
- connect/disconnect
- connection status
- export-directory field (configuration field only; export wiring is still
  incomplete)

### Polarization stages

Alice and Bob each have:

- backend: Simulator or Elliptec
- serial port
- Elliptec device/bus address
- connection status
- current angle
- target angle
- Connect/Disconnect
- Move
- Home
- Refresh position

The simulator makes all of these controls usable without hardware and is
covered by GUI smoke tests.

## Counts page and Bell scan

Live acquisition and the Bell scan are separate operations because both use
the coincidence measurement backend and the scan additionally needs exclusive
control of both polarization stages.

`MeasurementController` handles the ordinary start/poll/stop lifecycle.
`AcquisitionWorker` keeps that lifecycle on its worker thread and periodically
emits the resulting `MeasurementState` to the GUI.

`BellScanController` performs the actual 4×4 scan:

1. Configure coincidence measurement.
2. For each Alice Bell angle, move Alice.
3. For each Bob Bell angle, move Bob.
4. Integrate for the configured interval.
5. Record one matrix cell.
6. Repeat all 16 settings.
7. Evaluate E/S from the completed matrix.

`ScanWorker` emits each completed cell so the Counts table can update during
the scan rather than waiting for the final result.

The simulator has a small angle-dependent coincidence model so the Bell scan
is useful for development and produces a non-flat example matrix.

## Themes

`gui/theme.py` defines four named presets in `THEME_ORDER`:

```text
classic-light → classic-dark → soft-dark → soft-light
```

Each preset has its own semantic palette and also tunes visual parameters such
as page-title size, heading weight, button weight, control height, navigation
height, and corner radii. The sidebar button displays the current and next
preset and cycles through the four themes.

`light` and `dark` remain compatibility aliases for existing startup callers;
they are not part of the four-theme cycle.

## What is implemented vs. placeholder

| Area | Status |
|---|---|
| Counts | **Implemented** — live acquisition UI, VisPy plot, start/stop, Bell scan, 4×4 matrix, E/S summary |
| Settings | **Implemented** — acquisition backend controls, Alice/Bob stage configuration and motion controls |
| Time Tagger local | **Implemented** — adapter plus local backend selection |
| Time Tagger network | **Implemented** — single `host:port` server address |
| Elliptec | **Implemented** — adapter and Settings-stage controls |
| Simulator | **Implemented** — measurement backend and polarization stages |
| Polytope | Placeholder |
| Heralded g2 | Placeholder |
| State tomography | Placeholder |
| Measurement export | Core helper exists; GUI Save workflow is not yet wired |

## Time Tagger dependency

The Swabian Instruments SDK is imported lazily by `TimeTaggerAdapter`, so
simulator-only development and CI do not require the vendor SDK. The normal
runtime dependency set includes `elliptec`; the optional hardware extra is
reserved for the TimeTagger SDK.

The network backend currently accepts one server address and calls the SDK's
network factory with a one-element address list. The adapter shape can be
extended to multiple synchronized servers later without changing the core
measurement interface.

## Testing and CI

The test suite covers the core math/data/controller/export code without a
display, plus PyQt6 smoke tests for the main window, live acquisition start/stop,
Bell scan, simulator stage controls, four-theme cycling, and the Settings
network-backend field enabling/validation. Time Tagger backend tests cover
both the local/network adapter factory calls (with the vendor SDK mocked)
and `HardwareManager`'s reconnection guard, which requires the current
backend to be disconnected before `select()` can change it — the same rule
already enforced for the Alice/Bob stage backends.

For GUI tests, `tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen`. CI installs
the Qt/OpenGL system libraries needed by the offscreen PyQt6 platform, then
runs:

```bash
uv run ruff check .
uv run pytest -q
```

The GitLab and GitHub CI definitions are kept aligned.

## Remaining design work

The next significant hardware integration step is to have experiment code
consume the `HardwareManager`'s real Alice/Bob stages directly rather than
constructing simulator stages locally. That will let a real Bell scan use the
Elliptec devices configured in Settings while preserving the same
`BellScanController` interface.

After that, the main open work is experiment-specific measurement logic for
Polytope, Heralded g2, and state tomography, plus a proper GUI export/save
workflow.
