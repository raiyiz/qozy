# QOZY

SPDC / Bell-test measurement GUI — PyQt6 shell with a VisPy live-plotting
canvas, ported from the older PyQt5 + pyqtgraph/matplotlib prototype. See
`docs/architecture.md` for the module layout and porting status.

## Install (uv)

```bash
uv sync --extra dev
```

This creates `.venv/` and installs the project plus dev tools (pytest,
pytest-qt, ruff) from `uv.lock`. Plain `pip install -e ".[dev]"` also
works if you'd rather not use uv.

## Run

```bash
uv run qozy
# or: uv run python -m qozy.app
```

Runs against a built-in data simulator by default — no TimeTagger hardware
required. Swapping in the real adapter is a one-line change in
`src/qozy/app.py` (see `docs/architecture.md`).

## Test

```bash
uv run pytest
```

`core/` and `hardware/` tests run headless with no display needed.
`tests/test_gui_smoke.py` builds the real PyQt6 window and drives the
Counts page's start/stop cycle; it runs with `QT_QPA_PLATFORM=offscreen`
automatically (set in `tests/conftest.py`), so no display server is
required locally or in CI.

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


