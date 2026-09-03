# QOZY architecture

```
src/qozy/
├── app.py                  # entry point (console script `qozy`)
├── core/                   # no PyQt, no TimeTagger SDK — fully unit-testable
│   ├── bell_math.py        # ported from old_spdc_to_port/spdc/bellvalue.py::calc_e_s
│   ├── data_model.py       # MeasurementConfig / MeasurementState dataclasses
│   ├── controller.py       # orchestrates config + adapter + bell math
│   └── export.py           # ported from old_spdc_to_port/spdc/savedata.py
├── hardware/
│   ├── base.py              # MeasurementAdapter Protocol — the shared shape
│   ├── timetagger_adapter.py  # ported from old_spdc_to_port/spdc/timetaggerlive.py
│   └── simulator.py         # synthetic adapter, same interface, no hardware needed
└── gui/                     # PyQt6, built out from the modern_pyqt_starter template
    ├── theme.py, components.py   # carried over unchanged
    ├── main_window.py            # sidebar + page stack
    ├── plot_panel.py             # VisPy canvas, replaces old pyqtgraph/matplotlib
    ├── worker.py                 # QThread polling, keeps GUI thread unblocked
    └── pages/
        ├── counts_page.py        # wired to controller + simulator (real, not a placeholder)
        └── settings_page.py, polytope_page.py, heralded_g2_page.py,
            state_tomography_page.py   # still placeholders — TODO in each file
```

## Why this split

- **`core/` has zero Qt and zero hardware-SDK imports.** Everything in it
  can be tested headlessly, which is why `tests/` covers `bell_math`,
  `data_model`, `controller`, and `export` without needing a display or a
  TimeTagger.
- **`hardware/base.py`** is a `Protocol`, not a base class — `TimeTaggerAdapter`
  and `SimulatorAdapter` don't inherit from anything, they just implement
  the same method set. `MeasurementController` only ever talks to that
  shape, so swapping hardware for the simulator (or vice versa) is a
  one-line change in `qozy/app.py`.
- **`gui/worker.py`** exists because `old_spdc_to_port/spdc/main.py` polled
  data straight from a `QTimer` on the GUI thread. That's fine for a
  synthetic demo; it stalls the UI once real Coincidence/Correlation
  measurements are involved. The worker+thread pattern here is the fix,
  and the offscreen smoke test in the port PR caught a real cross-thread
  `QTimer` bug in the first draft of `_stop()` — see the comments in
  `worker.py` and `counts_page.py` if touching that code again.

## What's real vs. placeholder right now

| Page | Status |
|---|---|
| Counts | **Real** — wired to `MeasurementController` + `SimulatorAdapter`, live VisPy plot, start/stop |
| Settings | Placeholder (backend/export-dir picker not wired yet) |
| Polytope | Placeholder — no equivalent in the old code to port |
| Heralded g2 | Placeholder — no equivalent in the old code to port |
| State tomography | Placeholder — no equivalent in the old code to port |

Bell E/S calculation (`core/bell_math.py`) and export (`core/export.py`) are
ported and tested, but not yet called from the Counts page UI — that's the
next wiring step (feed a real/simulated coincidence matrix into
`controller.evaluate_bell()` and show E/S + the coincidence-matrix table
somewhere in the Counts page, closer to what `bellvalue.plot()` used to
draw with matplotlib).

## Known debt carried over from the old code, not yet resolved

- `old_spdc_to_port/spdc/bellvalue.py::bell_matrix()` was dead/broken in
  the original (references undefined `data`/`B_detector_angles`) and was
  **not** ported. `plot()`'s matplotlib rendering also wasn't ported —
  only the math (`calc_e_s`) was pulled out, per plan.md's "no GUI/plotting
  code in the calculation layer."
- `old_spdc_to_port/spdc/savedata.py` hardcoded `/home/sci/qkd/data` as
  the save path. `core/export.py` makes this a parameter
  (`DEFAULT_BASE_DIR = ~/qozy_data`); the Settings page still needs a field
  to actually change it at runtime.

## Recommended next steps (plan.md phases 2 onward)

1. Wire `controller.evaluate_bell()` into the Counts page (or a dedicated
   Bell-summary panel) once there's a real/simulated coincidence-matrix
   source.
2. Add `export.save_measurement()` to a "Save" button on the Counts page.
3. Swap `SimulatorAdapter` for `TimeTaggerAdapter` in `qozy/app.py` once
   hardware is available, and test against real correlation/coincidence
   timing.
4. Decide whether Polytope / Heralded g2 / State tomography get real
   measurement logic or get cut from the shell — nothing in
   `old_spdc_to_port` covers them, so it's an open question, not a
   forgotten port.
