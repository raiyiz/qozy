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
│   ├── export.py                 # measurement export helpers
│   └── app_config.py             # persisted "last used" GUI field values
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
    ├── main_window.py            # sidebar + page stack + theme cycling + config load/save
    ├── hardware_worker.py        # background connection/stage operations
    ├── worker.py                 # background live acquisition
    ├── scan_worker.py            # background Bell scan
    ├── plot_panel.py             # VisPy live plotting
    └── pages/
        ├── settings_page.py      # acquisition backend configuration and controls
        ├── polarization_page.py  # Alice/Bob stage configuration, motion, Bell-angle presets
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
`HardwareWorker`, and Polarization delegates stage connect/disconnect/
move/home/position reads to `StageWorker`. Live acquisition uses
`AcquisitionWorker`; the Bell scan uses `ScanWorker`.

Workers are one-shot or long-running background jobs owned by `QThread`. The
GUI does not call `QThread.wait()` during normal stop handling. Live acquisition
uses a thread-safe `threading.Event` stop request so the worker can leave its
loop without relying on a queued Qt callback being processed by a busy worker
thread.

## Settings page

Settings is the acquisition-backend/configuration page. It contains:

- backend: Simulator, Time Tagger (local), or Time Tagger (network)
- network server address for the network backend
- connect/disconnect
- connection status
- export-directory field (configuration field only; export wiring is still
  incomplete)

## Polarization page

Polarization owns Alice/Bob stage configuration and motion, separately from
Settings, so each has room for its own controls. Alice and Bob each have:

- backend: Simulator or Elliptec
- serial port
- Elliptec device/bus address
- connection status
- current angle
- target angle
- Connect/Disconnect
- Move (to the typed target angle)
- Bell-angle presets — one-tap buttons for 0°, 22.5°, 67.5°, 112.5°, and
  157.5° (`qozy.core.bell_math.BELL_ANGLES_DEG` plus 0° as a neutral
  reference), the same settings `BellScanController` steps through, so lining
  a stage up by hand for a manual check doesn't require typing and
  confirming an angle
- Home
- Refresh position

Every stage control (including the presets) is disabled while its stage is
disconnected or mid-operation, and `PolarizationPage.set_busy()` freezes both
stages during acquisition/Bell scan the same way `SettingsPage.set_busy()`
freezes the acquisition backend controls. The simulator makes all of these
controls usable without hardware and is covered by GUI smoke tests.

## Persisted configuration (`core/app_config.py`)

`AppConfig` is a plain, Qt-free dataclass holding the GUI field values a user
actually edits: acquisition backend + network address, export directory,
each stage's backend/port/address, and the Alice/Bob detector channels.
`load_config()`/`save_config()` read/write it as JSON at `~/.qozy/config.json`
(`DEFAULT_CONFIG_PATH`, overridable per call for testing).

`MainWindow` loads the config once at startup and passes it to `SettingsPage`,
`PolarizationPage`, and `CountsPage` as `initial=...` so each page pre-fills
its own widgets from it. Each of those pages implements
`export_config(config)`, which copies its current widget values back onto a
shared `AppConfig`; `MainWindow.closeEvent()` gathers all three and writes
them out.

Only *selections* persist, deliberately never live connection state:
`HardwareManager` always starts with the simulator connected (acquisition
and both stages) regardless of what backend was last selected, so a stale
saved network address or serial port can never cause an unattended
connection attempt to real hardware on startup — the user still presses
Connect. `load_config()` falls back to `AppConfig()` defaults on a missing,
corrupt, or unexpectedly-shaped file rather than raising, so a bad config
file can never stop QOZY from starting.

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
| Settings | **Implemented** — acquisition backend controls |
| Polarization | **Implemented** — Alice/Bob stage configuration, motion controls, Bell-angle presets |
| Time Tagger local | **Implemented** — adapter plus local backend selection |
| Time Tagger network | **Implemented** — single `host:port` server address |
| Elliptec | **Implemented** — adapter and Polarization-page controls |
| Simulator | **Implemented** — measurement backend and polarization stages |
| Config persistence | **Implemented** — Settings/Polarization/Counts field values saved on close, reloaded on startup |
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

The test suite covers the core math/data/controller/export/app_config code
without a display, plus PyQt6 smoke tests for the main window, live
acquisition start/stop, Bell scan, Polarization-page stage controls and
Bell-angle presets, four-theme cycling, the Settings network-backend field
enabling/validation, and config persistence across a simulated restart
(`MainWindow` closed and rebuilt against a temp config path). Time Tagger
backend tests cover both the local/network adapter factory calls (with the
vendor SDK mocked) and `HardwareManager`'s reconnection guard, which
requires the current backend to be disconnected before `select()` can
change it — the same rule already enforced for the Alice/Bob stage
backends.

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
