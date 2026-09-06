# QOZY

SPDC / Bell-test measurement GUI built with PyQt6 and VisPy, ported from
the older PyQt5 + pyqtgraph/matplotlib prototype. See
`docs/architecture.md` for the current module layout and hardware model.

## Install (uv)

```bash
uv sync --extra dev
```

This creates `.venv/` and installs QOZY plus the development tools
(`pytest`, `pytest-qt`, and `ruff`) from `uv.lock`. Plain
`pip install -e ".[dev]"` also works if you prefer pip.

The `elliptec` package and the Swabian Instruments `Swabian-TimeTagger` SDK
are both normal, required runtime dependencies (the Polarization page
supports real Thorlabs Elliptec stages, and the Time Tagger Settings page
supports real Time Tagger hardware). `matplotlib` is also required, for the
Bell-scan matrix heatmap and the quick-analysis SVG export (see
"Measurement and Bell scan" below). None of the three need a physical
device attached to import: `TimeTaggerAdapter` only imports
`Swabian.TimeTagger` lazily inside `connect()`, so simulator-only
development, tests, and CI never touch the vendor SDK's device-facing code.

## Run

```bash
uv run qozy
# or
uv run python -m qozy.app
```

QOZY starts with the simulator connected by default, so the application and
GUI can be exercised without hardware.

The sidebar has four hardware/experiment pages plus three measurement
placeholders:

- **Settings** — just the export directory. Everything else that used to
  live here moved to its own page as QOZY grew.
- **Time Tagger** — owns the acquisition backend and connection:
  - Simulator
  - Time Tagger (local USB)
  - Time Tagger (network, using a `host:port` server address)

  plus the actual measurement configuration: an 8-channel table (enabled,
  delay, trigger level), Alice/Bob channel assignment, counts/correlation
  bin widths and time frames, and the coincidence window. Connect/Disconnect
  and channel/timing changes run on a background Qt worker thread, same as
  everywhere else in this GUI. Four buttons act on that configuration:
  - **Apply to backend** pushes it to whatever is currently connected
  - **Load from device** reads the current configuration back
  - **Save profile** / **Load profile** explicitly save/restore this
    configuration as a named file, independent of the connection state
- **Polarization** — configures and moves the Alice and Bob stages used by
  the Counts page's Bell scan. Each stage supports:
  - Simulator
  - Elliptec, with serial port and device/bus address
  - Connect / disconnect
  - Move to an absolute angle, or one tap on a Bell-angle preset
    (0°, 22.5°, 67.5°, 112.5°, 157.5° — the same settings
    `BellScanController` scans through)
  - Home
  - Read the current angle
- **Counts** — live acquisition and the Bell scan (see "Measurement and Bell
  scan" below). Its Alice/Bob channel fields are read-only, driven by
  whatever the Time Tagger page currently has configured.

Hardware connection, motion, and configuration calls are all performed on
background Qt worker threads so vendor-library calls never run on the GUI
thread.

## Settings persistence

QOZY has two separate, intentionally different persisted files:

- **`~/.qozy/config.json`** (`core/app_config.py`) is automatic: Settings'
  export directory, Time Tagger's backend/network address selection, each
  Polarization stage's backend/port/address, and Counts' auto-save-after-scan
  checkbox are all saved here on every window close and reloaded to pre-fill
  those same fields next launch, no action needed. Only the *selections*
  persist, never live connection state — QOZY always starts with the
  simulator connected (acquisition and both stages), and switching to a real
  backend still needs its Connect button pressed, so a stale saved address
  can never cause an unattended connection attempt to real hardware. A
  missing or corrupt file is treated like a first run rather than an error.
- **`~/.qozy/timetagger_settings.json`** (`core/settings_store.py`) is the
  Time Tagger measurement profile — channel table, Alice/Bob assignment,
  timing — and is **only** written by an explicit action on the Time Tagger
  page: **Save profile** or **Apply to backend**. It is loaded automatically
  at startup as a starting point, but closing the window never silently
  overwrites it, so an unsaved edit in a field can't clobber a working
  profile. (It's still read at every launch, same missing/corrupt-file
  fallback as above.)

## Themes

The sidebar theme control cycles through four presets:

`Classic Light → Classic Dark → Soft Dark → Soft Light`

The classic pair uses stronger contrast and a more technical appearance.
The soft pair uses quieter surfaces, softer borders, gentler text hierarchy,
and slightly roomier controls. The four presets share the same semantic
color roles and widget styling, but tune colors, typography, spacing, and
corner radii differently.

## Measurement and Bell scan

The Counts page can run live acquisition through `MeasurementController`
and displays the current counter/correlation data in a VisPy panel. Its
Alice/Bob channel fields are read-only — they track whatever the Time
Tagger page currently has configured (`settings_changed` signal), so there
is exactly one place to set channel assignment, not two.

Live acquisition also tracks a **coincidence rate and running total** —
`setup_countrates()` now covers the coincidence (virtual) channels
alongside the per-detector singles, so "Coincidence rate" and "Total
coincidences" on the Counts page reflect real recorded data, not a
derived guess. Right now this only runs against the simulator by default;
real Time Tagger hardware exercises the same code path once connected.

The **Run Bell scan** action is a separate 4×4 polarization scan. It moves
Alice and Bob through the four Bell-analysis angle settings, integrates the
coincidence signal for each of the 16 combinations, fills the coincidence
matrix as cells complete, and evaluates the resulting E/S values.

The scan drives the same Alice/Bob stages configured on the Polarization
page (simulator or real Elliptec hardware), so it requires both stages to
be connected first, and it freezes Settings/Time Tagger/Polarization
controls for its duration to avoid a manual move or reconfiguration racing
the scan on the same device.

The simulator stages and simulator measurement adapter make this workflow
runnable without hardware.

Next to the numeric coincidence-matrix table, a small matplotlib **heatmap**
shows the same matrix colored by count rate, with E1–E4/S1–S4 annotated
directly on the plot — a quick visual read of CHSH violation strength
alongside the table's exact numbers.

Once a scan finishes, **Save scan** writes the 4×4 coincidence matrix to
Settings' export directory as a tab-delimited `.txt` file, in a
`year/month/day/NN.txt` folder structure (`NN` is the first free two-digit
number that day), *and* saves the heatmap as `NN_quick_analysis.svg`
alongside it — the same naming `old_spdc_to_port/spdc/bellvalue.py` used
for its own SVG report. Checking **Auto-save after scan** saves both files
automatically as soon as the scan completes, no click needed. The saved
paths (or a save error, e.g. a full day folder) are reported in the status
line.

## Test

```bash
uv run pytest
```

GUI smoke tests use `QT_QPA_PLATFORM=offscreen` (configured in
`tests/conftest.py`), so the PyQt6 shell can be exercised without a display.
`tests/conftest.py` also has an autouse fixture that points both persisted
files (`AppConfig` and the Time Tagger settings profile) at a fresh
`tmp_path` for every single test — no test ever reads or writes the real
`~/.qozy/` on the machine running the suite.

The suite also covers Time Tagger backend behavior (including the network
backend and the connect/disconnect reconfiguration guard), the Time Tagger
Settings page's connection/channel/profile controls (including that a
window close without an explicit Save/Apply never touches the profile
file), simulator polarization stages and Bell-angle presets on the
Polarization page, the Bell scan driving HardwareManager's real stages
(including its connected-stage guard and cross-page freeze), the live
coincidence-rate/total-counts readout, saving and auto-saving a completed
scan (matrix + quick-analysis SVG), config persistence across a simulated
restart, and the four-theme cycling behavior.

## Lint

```bash
uv run ruff check .
```

Same commands CI runs — see `.gitlab-ci.yml` (source of truth) and
`.github/workflows/ci.yml` (mirror), documented in `docs/architecture.md`.

## Troubleshooting

### Permission denied when connection to TimeTagger

`ERR: Could not open device file(/dev/bus/usb/004/002): Permission denied`

Solution
---
Find out Vednor and Device ID
`ls -l /dev/bus/usb/004/002`

1. First identify the device

`lsusb`

You'll get something like:

`Bus 004 Device 002: ID 1234:5678 Some Measurement Device`

The important part is:

1234:5678
^^^^   ^^^^
VID    PID

2. Create a group and add your user to it:
`sudo groupadd qozy`
`sudo usermod -aG qozy "$USER"`


3. Add udev rule:
`sudo nano /etc/udev/rules.d/99-qozy.rules`
fill it with this content:

`SUBSYSTEM=="usb", ATTR{idVendor}=="1234", ATTR{idProduct}=="5678", GROUP="qozy", MODE="0660"`
 
4. logout-login again
