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
    ├── bell_matrix_plot.py        # matplotlib heatmap of the Bell-scan matrix
    ├── bell_history_plot.py       # matplotlib max|S|-per-cycle line plot (live-loop mode)
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

### Coincidence rate and total counts

`MeasurementController.configure()` calls `setup_coincidences()` *before*
`setup_countrates()` now, specifically so the coincidence (virtual)
channels it returns can be folded into the same countrate registration as
the singles: `setup_countrates(all_channels + coincidence_channels)`. This
means `get_countrate_data()`/`get_total_counts()` — both already part of
`MeasurementAdapter` and already used elsewhere (`BellScanController` reads
`get_total_counts()` per angle setting) — now also cover live coincidence
rate and running coincidence total, not just per-detector singles.
`MeasurementState.countrate_labels` records which array index is which
(`"ch 1"`, `"coin 1×3"`, ...) so `CountsPage._update_coincidence_labels()`
can sum just the `"coin "`-prefixed entries into the "Coincidence rate" /
"Total coincidences" labels next to the live plot — this is genuinely new
recorded data, not a different view of something Counts already showed.
Only wired against the simulator's data so far; real Time Tagger hardware
runs through the exact same `MeasurementAdapter` methods once connected.

### Bell-matrix heatmap

`gui/bell_matrix_plot.py`'s `BellMatrixPlot` is a small embedded matplotlib
`FigureCanvasQTAgg`, sitting next to the numeric `QTableWidget` in the Bell
summary card. It draws the 4×4 matrix as a color-coded heatmap with
E1–E4/S1–S4 annotated on the plot itself — a quick visual read of CHSH
violation strength, complementing rather than replacing the table's exact
values. It resets to a placeholder (`clear()`) at the start of every scan
and at first launch. This is a lighter port of
`old_spdc_to_port/spdc/bellvalue.py`'s `plot()` function, adapted to the
4×4 matrix this app actually produces — the old function plotted a full
4×16 angle-sweep visibility curve with the 4×4 Bell slice overlaid as a
table; this app's `BellScanController` only ever takes the four discrete
Bell-angle settings, so there's no sweep curve to draw. (`bellvalue.py`'s
other function, `bell_matrix()`, was itself an unfinished stub in the
original — it references undefined variables and ends in
`print("Coming Soon.")` — so there was nothing there to port.)

Everything about a scan is calculated live, one cell at a time, not only
once it finishes:

- `CountsPage._on_scan_cell()` (fed by `ScanWorker.cell_done`, emitted from
  `BellScanController.run()` on its own `QThread` and delivered to the GUI
  thread through Qt's normal queued cross-thread signal delivery — the
  scan itself never waits on any of this) updates a running partial
  matrix + a boolean "filled" mask, then redraws `BellMatrixPlot` on every
  one of the 16 settings. `update_matrix()`'s `filled` argument masks out
  not-yet-measured cells (drawn in a neutral color, not as if they were a
  real zero-count reading) and — the actual point — excludes them from the
  vmin/vmax color-scale normalization, so the colormap reflects only what's
  been measured so far and recalibrates as more cells arrive, rather than a
  range fixed up front. The title shows an "N/16 settings measured"
  progress line until `e`/`s` are supplied on the final call.
- The E/S summary labels update the same way, via
  `bell_math.e_readiness()`: it mirrors `calc_e_s`'s own 2×2-block
  indexing (`_E_BLOCKS`) to report which of the four E values are actually
  backed by real measurements yet, given the current filled mask. An E
  value only appears once every cell its formula reads has a real
  recorded count — not derived from a matrix still zero-padded for
  unmeasured cells — and none of the four S values appear until all four
  E values do, since each S combines all of them. Given the scan's actual
  fill order (Alice steps outer, Bob inner — see "Bell scan" above), E1
  becomes available after the 6th of 16 cells, E2 after the 8th, E3 after
  the 14th, and E4 (and so S) only at the very end.
- `CountsPage._render_bell_summary(e, s, e_ready)` is the single place
  that turns an (E, S, readiness) triple into label text, shared between
  the live per-cell path and the final `_on_scan_finished` call (which
  passes an all-`True` readiness, since the worker's `matrix`/`e`/`s` at
  that point are the authoritative completed-scan values, not
  recomputed locally).

### Live-loop scanning

Checking **Loop continuously (live)** on the Counts page turns the
single-shot Bell scan into a repeating one, re-running the full 16-setting
scan back to back after each cycle finishes, so the matrix/heatmap/E/S/S-
history keep reflecting whatever's currently being measured rather than a
single one-off snapshot.

**Sequencing — why the next cycle starts from `_on_scan_thread_finished`,
not `_on_scan_finished`.** The natural-looking implementation — decide
whether to loop and call `QTimer.singleShot(0, self._run_bell_scan)`
directly inside `_on_scan_finished` — has a real race: `worker.finished` is
connected to both `_on_scan_finished` and `self._scan_thread.quit()`, in
that order, so `_on_scan_finished` runs *before* the `QThread` has actually
stopped and `_on_scan_thread_finished` has cleared `self._scan_thread` back
to `None`. A `QTimer.singleShot(0, ...)` scheduled from inside
`_on_scan_finished` can fire before that cleanup completes, which trips
`_run_bell_scan`'s own reentrancy guard (`if self._scan_thread is not
None: return`) and silently stalls the entire loop after exactly one
cycle — no error, no crash, just nothing happening again. Restarting only
from `_on_scan_thread_finished` (which by definition only runs once the
`QThread` has genuinely finished) avoids this entirely. This was caught by
running the loop for real and watching it stop after cycle 1, not by
static reasoning about the code — worth remembering if this area gets
touched again.

**State that must survive a "should we continue?" decision made in two
different places.** `_on_scan_finished` decides whether *this* cycle should
be followed by another (based on the checkbox at that moment) and updates
the status text accordingly; `_on_scan_thread_finished` makes the same
check again once the thread has actually stopped, because the checkbox can
change in the gap between the two. Both paths that end up *not* continuing
must call `_stop_live_scan()` (which only resets `_live_scan_running`) —
missing this in `_on_scan_thread_finished`'s "stop" branch was a real bug:
`_live_scan_running` stayed `True` forever after a loop that stopped in
that exact gap, which then made the *next* "Run Bell scan" click
wrongly think it was continuing a still-active loop and skip resetting the
cycle count and `_s_history`. `_on_scan_thread_finished` also corrects the
status text in that same gap, since `_on_scan_finished` had already written
a "starting next…" message on the assumption the loop would continue.

**Accumulation, not per-cycle reset.** `self._live_matrix` and
`self._live_filled_mask` only reset on a genuinely fresh start (`not
self._live_scan_running`) — a loop continuation adds this cycle's values
into them cell by cell (`_on_scan_cell`) instead of replacing them, so the
displayed matrix keeps growing the way a longer-integrated measurement
should, rather than resetting to a fresh, independent, noisier reading
every cycle. `_display_matrix()` returns this accumulated matrix in live
mode (and the ordinary per-cycle `self._scan_matrix` in single-shot mode,
completely unchanged). `calc_e_s`/`e_readiness` are computed from whichever
of those `_display_matrix()` returns — unlike the rate-based normalization
this replaced (dividing by integration time, which is just a uniform
per-cell rescaling that provably changes nothing about E/S — see
`test_calc_e_s_is_invariant_to_overall_count_scale`), accumulation is a
genuinely larger dataset each cycle, so there's no reason to compute E/S
from anything other than what's actually displayed. The max|S| history
graph tracks this same accumulated running estimate at each cycle
checkpoint, so a run of cycles shows the estimate settling/converging
rather than independent per-cycle noise. Everything actually saved to disk
(the `.txt`, the SVG) matches whatever's currently displayed, live or not.

Because nothing is ever reset to a blank placeholder between cycles (only
a fresh start does that — see `_run_bell_scan`), the matrix/heatmap/E-S
never flash empty and refill; they're only ever added to while a loop
runs.

**`BellHistoryPlot`** (`gui/bell_history_plot.py`) is a small matplotlib
line plot of max|S| per completed cycle (`self._s_history`, capped at the
last 200 to bound memory/plot width for a long-running loop), with
reference lines at the classical bound (`CLASSICAL_BOUND = 2.0`) and the
Tsirelson bound (`TSIRELSON_BOUND = 2√2`), so a run shows a trend against
those two reference points rather than a bare number.

**Layout stability.** Every widget whose text/content changes every cycle
had a real, observed layout-stability problem, fixed by making its size a
fixed quantity instead of letting Qt/matplotlib recompute it from current
content on each redraw: `BellMatrixPlot`/`BellHistoryPlot` use
`figure.subplots_adjust(...)` (fixed margins, set once) instead of
`tight_layout=True` (recomputed per draw from the current title/tick
text) and `canvas.setFixedSize(...)` instead of `setMinimumHeight(...)`;
`status_label` has a fixed height for 3 wrapped lines so a shorter/longer
live-loop status message can't resize the whole Settings card;
`bell_e_label`/`bell_s_label` have a fixed minimum width so placeholder
dashes versus real numbers don't reflow the heatmap column beside them;
`bell_table`'s columns have a fixed width (`QHeaderView.ResizeMode.Fixed`)
so accumulated counts growing to more digits over a long run don't widen
them. `CountsPage`'s content also now lives inside a `QScrollArea` rather
than directly in the page's own layout, so a window too small for
everything (taller now, with the history graph) scrolls instead of
silently clipping.

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
- also saves the heatmap as `NN_quick_analysis.svg` next to the `.txt` —
  the same suffix `bellvalue.py`'s own SVG output used
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
| Counts | **Implemented** — live acquisition UI, VisPy plot, live coincidence rate/total, start/stop, Bell scan (driving HardwareManager's real stages), 4×4 matrix + heatmap, live-loop scanning with cross-cycle accumulation and a max-\|S\| history graph, E/S summary; Alice/Bob channel display is read-only, driven by Time Tagger Settings |
| Settings | **Implemented** — export directory only |
| Time Tagger Settings | **Implemented** — connection, 8-channel table, Alice/Bob assignment, timing, Apply/Load-from-device/Save-profile/Load-profile/Reset |
| Polarization | **Implemented** — Alice/Bob stage configuration, motion controls, Bell-angle presets |
| Time Tagger local | **Implemented** — adapter plus local backend selection |
| Time Tagger network | **Implemented** — single `host:port` server address |
| Elliptec | **Implemented** — adapter and Polarization-page controls |
| Simulator | **Implemented** — measurement backend and polarization stages |
| Config persistence | **Implemented** — two separate stores; see "Two persisted files, two different jobs" |
| Measurement export | **Implemented** — Save/auto-save the completed Bell-scan matrix and its quick-analysis SVG heatmap to the Settings export directory |
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
its duration), the live-loop scan (multiple cycles running unattended,
stopping cleanly — including the exact race-condition gap described in
"Live-loop scanning" above — the displayed value strictly increasing cycle
over cycle rather than resetting, never flashing back to the placeholder
between cycles, and the max-|S| history graph updating each cycle), the
layout-stability fixes (fixed canvas sizes across redraws, fixed table
column width under a long accumulated value, fixed status-label height,
the scroll-area wrapper), saving and auto-saving a completed
scan to a temp export directory, the Time Tagger Settings page's
connection/channel/profile controls, Polarization-page stage controls and
Bell-angle presets, four-theme cycling, and config persistence across a
simulated restart (`MainWindow` closed and rebuilt against temp paths for
both stores). Time Tagger backend tests cover both the local/network
adapter factory calls (with the vendor SDK mocked) and `HardwareManager`'s
reconnection guard, which requires the current backend to be disconnected
before `select()` can change it — the same rule already enforced for the
Alice/Bob stage backends.

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
