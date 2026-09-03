# SPDC GUI project

This project contains a PyQt + VisPy GUI prototype for SPDC-style live signal monitoring and Bell-value analysis.

## Quick start with uv

```bash
uv sync --extra dev
uv run spdc-gui
```

## Run the package directly

```bash
uv run python -m spdc_app
```

## Tests

```bash
uv run pytest -q
```

## Project structure

- `spdc_app/` — the package containing the GUI, controller, data model, Bell math, and simulator
- `tests/` — project tests
- `pyproject.toml` — project metadata and uv install configuration
