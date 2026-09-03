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
