# QOZY

SPDC / Bell-test measurement GUI — PyQt6 shell with a VisPy live-plotting
canvas, ported from the older PyQt5 + pyqtgraph/matplotlib prototype. See
`docs/architecture.md` for the module layout and porting status.

## Install (editable, dev)

```bash
python -m pip install -e ".[dev]"
```

## Run

```bash
qozy
# or: python -m qozy.app
```

Runs against a built-in data simulator by default — no TimeTagger hardware
required. Swapping in the real adapter is a one-line change in
`src/qozy/app.py` (see `docs/architecture.md`).

## Test

```bash
pytest
```

`core/` and `hardware/` tests run headless with no display needed. GUI
smoke-testing (building `MainWindow`, exercising the Counts page start/stop
cycle) can be run with `QT_QPA_PLATFORM=offscreen pytest` once GUI tests are
added to `tests/` — not yet included here, see `docs/architecture.md` for
what's still open.
