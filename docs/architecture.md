# QOZY architecture

QOZY is split into a hardware-independent measurement core, hardware adapters,
and a PyQt6 GUI. The important boundary is that GUI pages never need to know
which vendor backend is underneath them.

```text
src/qozy/
├── app.py                         # console entry point
├── core/
│   ├── bell_math.py              # Bell/CHSH calculations and angle constants
│   ├── data_model.py              # measurement config/state + TimeTaggerSettings dataclasses
│   ├── controller.py              # MeasurementController
│   ├── scan_controller.py         # hardware-independent 4×4 Bell angle scan
│   ├── export.py                  # measurement export helpers
│   ├── app_config.py              # automatic "last used" GUI field values
│   └── settings_store.py          # explicit Time Tagger settings profile (Save/Load)
├── hardware/
│   ├── base.py                    # MeasurementAdapter + PositionerAdapter protocols
│   ├── manager.py                 # process-wide acquisition/stage/settings ownership
│   ├── simulator.py                # simulator acquisition + simulator stages
│   ├── timetagger_adapter.py      # Swabian TimeTagger SDK adapter
│   ├── timetagger_local.py        # local TimeTagger backend
│   ├── timetagger_network.py      # network TimeTagger backend
│   └── elliptec_adapter.py        # Thorlabs Elliptec rotator adapter
└── gui/
    ├── theme.py                   # four QOZY visual presets
    ├── components.py              # reusable Qt widgets
    ├── main_window.py             # sidebar + page stack + theme cycling + config load/save
    ├── hardware_worker.py         # background connection/stage/Time-Tagger-config operations
    ├── worker.py                  # background live acquisition
    ├── scan_worker.py             # background Bell scan
    ├── plot_panel.py              # VisPy live plotting
    └── pages/
        ├── settings_page.py            # export directory only
        ├── timetagger_settings_page.py # Time Tagger connection, channels, timing, profile
        ├── polarization_page.py        # Alice/Bob stage configuration, motion, Bell-angle presets
        ├── counts_page.py              # live acquisition + Bell scan UI
        ├── polytope_page.py            # placeholder
        ├── heralded_g2_page.py         # placeholder
        └── state_tomography_page.py    # placeholder
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
├── polarization stages
│   ├── Alice → SimulatorStage or ElliptecAdapter
│   └── Bob   → SimulatorStage or ElliptecAdapter
└── timetagger_settings: TimeTaggerSettings  # last configured/applied values
```

The default state is a connected simulator acquisition backend and two
connected simulator stages. A stage can be reconfigured only after it has
been disconnected. `timetagger_settings` starts as `TimeTaggerSettings()`
defaults regardless of any saved profile — see "Two persisted files" below
for why the manager itself never auto-loads a profile.

For Elliptec, each stage stores a serial port and a single device/bus address.
The adapter supports either separate serial controllers or multiple rotators
sharing one controller/port, because the underlying constructor receives both
`port` and `address`.

`manager.configure_timetagger(settings)` and
`manager.read_timetagger_settings()` push/pull a `TimeTaggerSettings` to/from
whatever acquisition adapter is currently connected, using the same
`connected`-guard pattern as `select()`/`select_stage()`.

## GUI threading rule

Potentially blocking vendor operations must not run on the Qt GUI thread.
The Time Tagger Settings page delegates connect/disconnect and
apply/load-from-device to `HardwareWorker`; Polarization delegates stage
connect/disconnect/move/home/position reads to `StageWorker`. Live
acquisition uses `AcquisitionWorker`; the Bell scan uses `ScanWorker`.

Workers are one-shot or long-running background jobs owned by `QThread`. The
GUI does not call `QThread.wait()` during normal stop handling. Live acquisition
uses a thread-safe `threading.Event` stop request so the worker can leave its
loop without relying on a queued Qt callback being processed by a busy worker
thread.

## Settings page

Settings only holds the export directory now — everything else that used
to live here moved to its own page as QOZY grew (acquisition backend and
connection to Time Tagger Settings, stage configuration to Polarization).
It exists mainly so there is a stable, obviously-general-purpose place for
whatever doesn't belong to one specific hardware page.

## Time Tagger Settings page

`TimeTaggerSettingsPage` owns everything about the Time Tagger: connection
*and* measurement configuration, because on real hardware they are the same
device and the channel/timing setup has to travel with whichever backend is
connected.

- **Connection**: backend (Simulator, Time Tagger local, Time Tagger
  network), network server address, Connect/Disconnect, device status
  (reads `adapter.get_device_info()` when connected)
- **Channel configuration**: an 8-row table — enabled, channel number,
  delay (ns), trigger level (V) — one row per physical channel
- **Acquisition configuration**: Alice/Bob channel assignment, counts bin
  width/time frame, coincidence window, correlation bin width/time frame,
  measurement time frame
- **Actions**:
  - **Apply to backend** validates the current fields into a
    `TimeTaggerSettings`, saves it as the profile (see below), and pushes
    it to the connected adapter via `HardwareManager.configure_timetagger()`
    on a background thread
  - **Load from device** reads the connected adapter's current
    configuration back via `HardwareManager.read_timetagger_settings()`
    and repopulates every field
  - **Save profile** / **Load profile** explicitly write/read the settings
    profile independent of any connection state
  - **Reset defaults** repopulates the fields from `TimeTaggerSettings()`

`settings_changed` (emitted whenever settings are applied or loaded) is
what `CountsPage.set_timetagger_settings()` listens to, so Counts' Alice/Bob
channel display always matches this page — there is exactly one place that
edits channel assignment.

## Polarization page

Polarization owns Alice/Bob stage configuration and motion, separately from
Settings and Time Tagger, so each has room for its own controls. Alice and
Bob each have:

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
and `TimeTaggerSettingsPage.set_busy()` freeze their own controls. The
simulator makes all of these controls usable without hardware and is
covered by GUI smoke tests.

## Two persisted files, two different jobs

QOZY writes two separate on-disk files, and it's deliberate that they are
separate rather than one combined settings blob:

### `core/app_config.py` — automatic, "last used GUI state"

`AppConfig` is a plain, Qt-free dataclass holding the GUI field values a
user actually selects day-to-day and would be annoyed to retype every
launch: acquisition backend + network address, export directory, and each
stage's backend/port/address. `load_config()`/`save_config()` read/write it
as JSON at `~/.qozy/config.json` (`DEFAULT_CONFIG_PATH`, overridable per
call for testing).

`MainWindow` loads it once at startup and passes it to `SettingsPage`,
`TimeTaggerSettingsPage`, `PolarizationPage`, and `CountsPage` as
`initial=...` so each page pre-fills its own widgets from it. Each of those
pages implements `export_config(config)`, copying its current widget values
back onto a shared `AppConfig`; `MainWindow.closeEvent()` gathers all four
and writes them out — every time, no matter what.

Only *selections* persist here, deliberately never live connection state:
`HardwareManager` always starts with the simulator connected (acquisition
and both stages) regardless of what backend was last selected, so a stale
saved network address or serial port can never cause an unattended
connection attempt to real hardware on startup — the user still presses
Connect. `load_config()` falls back to `AppConfig()` defaults on a missing,
corrupt, or unexpectedly-shaped file rather than raising, so a bad config
file can never stop QOZY from starting.

### `core/settings_store.py` — explicit, "a saved measurement profile"

`TimeTaggerSettingsStore` persists a `TimeTaggerSettings` (channel table,
Alice/Bob assignment, timing) as JSON at `~/.qozy/timetagger_settings.json`
(`DEFAULT_SETTINGS_PATH`). Unlike `AppConfig`, this file is **only** ever
written by an explicit action on the Time Tagger Settings page — **Save
profile** or **Apply to backend** — never by closing the window.
`TimeTaggerSettingsPage.export_config()` (called from `MainWindow.closeEvent`
the same as every other page) only relays the backend/network-address
*selection* into the shared `AppConfig`; it never touches the profile
store. This matters in practice: without it, an unsaved, half-typed edit in
a channel field would silently clobber a working profile just because the
window happened to close. The profile is still loaded automatically at
startup as a starting point — `TimeTaggerSettingsPage.__init__` calls
`self.store.load()` — it just isn't re-saved unless the user asks for that.

`TimeTaggerSettingsStore.load()` has the same missing/corrupt/wrong-shape
fallback to defaults as `load_config()`, for the same reason.

### Test isolation

Both stores default to real paths under the user's home directory, so
`tests/conftest.py` has an **autouse** fixture (`isolated_persisted_files`)
that points both `app_config.DEFAULT_CONFIG_PATH` and
`settings_store.DEFAULT_SETTINGS_PATH` at a fresh `tmp_path` for *every*
test — including ones that don't look like they touch persistence, since
just constructing a `MainWindow` builds a `TimeTaggerSettingsPage`, which
loads a profile in its constructor. Before this fixture existed, running
the suite actually read and wrote the real `~/.qozy_timetagger_settings.json`
on whatever machine ran it.

## Counts page and Bell scan

Live acquisition and the Bell scan are separate operations because both use
the coincidence measurement backend and the scan additionally needs exclusive
control of both polarization stages.

`MeasurementController` handles the ordinary start/poll/stop lifecycle.
`AcquisitionWorker` keeps that lifecycle on its worker thread and periodically
emits the resulting `MeasurementState` to the GUI.

`BellScanController` performs the actual 4×4 scan, driving
`HardwareManager.stages["alice"]`/`["bob"]` — whatever backend Polarization
currently has connected, simulator or Elliptec — rather than page-local
stage objects, via `CountsPage._bell_scan_stages()`:

1. Configure coincidence measurement.
2. For each Alice Bell angle, move Alice.
3. For each Bob Bell angle, move Bob.
4. Integrate for the configured interval.
5. Record one matrix cell.
6. Repeat all 16 settings.
7. Evaluate E/S from the completed matrix.

`ScanWorker` emits each completed cell so the Counts table can update during
the scan rather than waiting for the final result.

Because the scan drives the same stage objects Polarization's Move/Home/
preset buttons do, `CountsPage`:

- refuses to start a scan unless both `hardware.stage_connected["alice"]`
  and `["bob"]` are true, with an inline error naming the Polarization page
  instead of a confusing failure partway through the scan
- emits `acquisition_changed` around the scan the same way it does around
  live acquisition, so `SettingsPage.set_busy()`,
  `TimeTaggerSettingsPage.set_busy()`, and `PolarizationPage.set_busy()`
  all freeze their controls for the duration — a manual Move from
  Polarization, or a reconfiguration from Time Tagger Settings, mid-scan
  would otherwise race the scan's own stage motion or measurement config
  on the same physical devices

A `CountsPage` built with only a `MeasurementController` (no
`HardwareManager` — used by a couple of tests) falls back to page-local
`SimulatorStage` instances instead, since there is no manager to pull real
stages from.

The simulator has a small angle-dependent coincidence model so the Bell scan
is useful for development and produces a non-flat example matrix.

### Saving a completed scan

The completed 4×4 coincidence matrix is the one thing Counts actually saves
(live counter/correlation data is a continuously-updating array with no
natural "this is the measurement" moment, so it isn't exportable from the
GUI). `CountsPage`:

- tracks Settings' export-directory field via
  `settings_page.export_dir.textChanged` wired straight to
  `counts_page.set_export_dir` in `MainWindow` — no direct reference
  between the two pages
- enables **Save scan** once a scan finishes, and calls
  `core.export.save_measurement(matrix, base_dir=...)` on click, which
  writes into the dated `year/month/day/NN.txt` folder structure and
  reports the exact path back in the status line
- also offers an **Auto-save after scan** checkbox; when checked,
  `_on_scan_finished` calls the same save path itself as soon as the scan
  completes, no click needed
- reports a save failure (a full day folder, an unwritable directory) in
  the status line rather than raising, the same way every other
  background-worker error in this GUI is surfaced

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
| Counts | **Implemented** — live acquisition UI, VisPy plot, start/stop, Bell scan (driving HardwareManager's real stages), 4×4 matrix, E/S summary; Alice/Bob channel display is read-only, driven by Time Tagger Settings |
| Settings | **Implemented** — export directory only |
| Time Tagger Settings | **Implemented** — connection, 8-channel table, Alice/Bob assignment, timing, Apply/Load-from-device/Save-profile/Load-profile/Reset |
| Polarization | **Implemented** — Alice/Bob stage configuration, motion controls, Bell-angle presets |
| Time Tagger local | **Implemented** — adapter plus local backend selection |
| Time Tagger network | **Implemented** — single `host:port` server address |
| Elliptec | **Implemented** — adapter and Polarization-page controls |
| Simulator | **Implemented** — measurement backend and polarization stages |
| Config persistence | **Implemented** — two separate stores; see "Two persisted files, two different jobs" |
| Measurement export | **Implemented** — Save/auto-save the completed Bell-scan matrix to the Settings export directory |
| Polytope | Placeholder |
| Heralded g2 | Placeholder |
| State tomography | Placeholder |

## Time Tagger dependency

`Swabian-TimeTagger` is a normal, required runtime dependency (same as
`elliptec`) — not an optional extra. `TimeTaggerAdapter` still only imports
`Swabian.TimeTagger` lazily, inside `connect()`, so nothing about
simulator-only development, tests, or CI ever needs a physical device
attached; the package just needs to be installed, which `uv sync` (or
`pip install -e .`) already does.

The network backend currently accepts one server address and calls the SDK's
network factory with a one-element address list. The adapter shape can be
extended to multiple synchronized servers later without changing the core
measurement interface.

## Testing and CI

The test suite covers the core math/data/controller/export/app_config/
settings_store code without a display, plus PyQt6 smoke tests for the main
window, live acquisition start/stop, Bell scan (including that it uses
`HardwareManager`'s real stages, refuses to start with a stage
disconnected, and freezes Settings/Time Tagger Settings/Polarization for
its duration), saving and auto-saving a completed scan to a temp export
directory, the Time Tagger Settings page's connection/channel/profile
controls, Polarization-page stage controls and Bell-angle presets,
four-theme cycling, and config persistence across a simulated restart
(`MainWindow` closed and rebuilt against temp paths for both stores). Time
Tagger backend tests cover both the local/network adapter factory calls
(with the vendor SDK mocked) and `HardwareManager`'s reconnection guard,
which requires the current backend to be disconnected before `select()`
can change it — the same rule already enforced for the Alice/Bob stage
backends.

`tests/conftest.py` has an autouse `isolated_persisted_files` fixture (see
"Two persisted files, two different jobs" above) that points both
`AppConfig` and the Time Tagger settings profile at a fresh `tmp_path` for
every test, so the suite never reads or writes the real `~/.qozy/` on the
machine running it — regardless of whether an individual test looks like
it cares about persistence.

For GUI tests, `tests/conftest.py` also sets `QT_QPA_PLATFORM=offscreen`. CI
installs the Qt/OpenGL system libraries needed by the offscreen PyQt6
platform, then runs:

```bash
uv run ruff check .
uv run pytest -q
```

The GitLab and GitHub CI definitions are kept aligned.

## Remaining design work

The main open work is experiment-specific measurement logic for Polytope,
Heralded g2, and state tomography.
