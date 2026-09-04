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

The `elliptec` package is a normal runtime dependency because the Settings
page supports real Thorlabs Elliptec stages. The Swabian Instruments
TimeTagger SDK remains optional for simulator-only development and CI.

## Run

```bash
uv run qozy
# or
uv run python -m qozy.app
```

QOZY starts with the simulator connected by default, so the application and
GUI can be exercised without hardware.

The **Settings** page provides independent configuration for the acquisition
backend and the Alice/Bob polarization stages. Acquisition supports:

- Simulator
- Time Tagger (local USB)
- Time Tagger (network, using a `host:port` server address)

Each polarization stage supports:

- Simulator
- Elliptec, with serial port and device/bus address
- Connect / disconnect
- Move to an absolute angle
- Home
- Read the current angle

Hardware connection and motion calls are performed on background Qt worker
threads so vendor-library calls do not run on the GUI thread.

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
and displays the current counter/correlation data in a VisPy panel.

The **Run Bell scan** action is a separate 4×4 polarization scan. It moves
Alice and Bob through the four Bell-analysis angle settings, integrates the
coincidence signal for each of the 16 combinations, fills the coincidence
matrix as cells complete, and evaluates the resulting E/S values.

The simulator stages and simulator measurement adapter make this workflow
runnable without hardware.

## Test

```bash
uv run pytest
```

GUI smoke tests use `QT_QPA_PLATFORM=offscreen` (configured in
`tests/conftest.py`), so the PyQt6 shell can be exercised without a display.
The suite also covers Time Tagger backend behavior (including the network
backend and the connect/disconnect reconfiguration guard), simulator
polarization stages, Settings acquisition and stage controls, and the
four-theme cycling behavior.

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
