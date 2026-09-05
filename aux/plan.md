# SPDC-to-Current-Project Port Plan

## Goal
Port the SPDC measurement GUI into the current project while using PyQt for the application shell and VisPy for the live plotting. The end result should keep the SPDC measurement logic, but move it into a cleaner project structure and replace the old plotting stack with a VisPy-based live plot embedded in a Qt window.

## Scope
- Keep the measurement and Bell-analysis behavior from the existing SPDC package.
- Replace the old pyqtgraph/matplotlib visualization with a PyQt + VisPy plotting surface.
- Keep the project lightweight and maintainable.
- Add a simulation mode so the GUI can be tested without hardware.

## Current code to port
Relevant files in the existing SPDC folder:
- `spdc/spdc/main.py` — current GUI and control flow
- `spdc/spdc/timetaggerlive.py` — TimeTagger setup and acquisition wrapper
- `spdc/spdc/bellvalue.py` — Bell analysis calculations
- `spdc/spdc/savedata.py` — save/export logic
- `spdc/layout/main.ui` — original Qt Designer layout

## Target architecture
Use a layered structure so UI, math, and hardware logic are separated:

- `app.py` — project launcher
- `spdc_app/__init__.py` — package marker
- `spdc_app/main_window.py` — PyQt application shell and layout
- `spdc_app/plot_panel.py` — VisPy canvas and live plotting helpers
- `spdc_app/controller.py` — orchestrates settings, worker, and updates
- `spdc_app/timetagger_adapter.py` — TimeTagger-specific acquisition wrapper
- `spdc_app/bell_math.py` — Bell calculation functions
- `spdc_app/simulator.py` — synthetic data generator for testing
- `spdc_app/data_model.py` — measurement config/state objects
- `spdc_app/export.py` — saves measurement output

## High-level port steps

### 1. Audit and extract the measurement logic
Review the SPDC app and pull out the core behaviors:
- detector channel setup
- delay configuration
- coincidence and correlation setup
- counts acquisition workflow
- Bell-value calculation
- data export behavior

The goal is to keep the same logical operations while moving them out of the monolithic UI class.

### 2. Rebuild the app around a PyQt main window
Create a `QMainWindow` that contains:
- left-side control panel
- right-side plotting area
- status bar or labels for measurement state

The window owns the application lifecycle but does not directly perform raw hardware or plotting operations.

### 3. Embed a VisPy canvas inside the Qt app
Use a `SceneCanvas` and add it to the Qt layout through `canvas.native`.

Suggested structure:
- `self.canvas = scene.SceneCanvas(...)`
- `self.view = self.canvas.central_widget.add_view()`
- `self.view.camera = "panzoom"`
- `self.line_alice = visuals.Line(...)`
- `self.line_bob = visuals.Line(...)`
- `self.line_coin = visuals.Line(...)`
- `self.line_corr = visuals.Line(...)`

This replaces the existing pyqtgraph/matplotlib plotting widgets while preserving the same live-monitoring purpose.

### 4. Separate control logic from rendering logic
Instead of wiring directly to UI object names like the old code does, the new design should use a model-driven approach:

- detector channels
- delay list
- counts bin width
- count time frame
- measurement time
- coincidence window
- correlation settings
- Bell matrix state
- live acquisition enabled

The controls update this model, and the model drives the hardware or simulator.

### 5. Port the TimeTagger backend into an adapter layer
Keep the TimeTagger code from `timetaggerlive.py`, but wrap it in a dedicated adapter class with a stable interface.

Example responsibilities:
- `connect()`
- `disconnect()`
- `setup_channel(channel, delay)`
- `setup_sm()`
- `setup_counters(...)`
- `setup_coincidences(...)`
- `setup_correlations(...)`
- `setup_countrates(...)`
- `start_sm()`
- `stop_sm()`
- `get_counter_data()`
- `get_corr_data()`
- `get_countrate_data()`

This lets the GUI remain unchanged even if the hardware backend changes or a simulator is used for tests.

### 6. Port the Bell analysis into a reusable calculation module
Move the Bell logic from `bellvalue.py` into a dedicated non-GUI module.

Responsibilities:
- accept a coincidence matrix or raw counts
- compute E values and S values
- return values in a numerically stable way
- avoid GUI and plotting code in the calculation layer

This makes it easier to test and reuse in both live and simulated modes.

### 7. Use Qt worker threads for live acquisition
The live update path should not run on the main GUI thread.

Plan:
- `QThread` or a `QObject` worker receives the acquisition settings
- worker polls the TimeTagger adapter for new data
- emits `data_ready(counter_data, corr_data, countrate_data)`
- main window updates the VisPy plots on the GUI thread

This mirrors the original live-data pattern but in a cleaner, safer architecture.

### 8. Add a simulator mode for development and CI
Add a `SimulatorAdapter` implementing the same interface as the TimeTagger adapter.

It produces synthetic values for:
- Alice counts
- Bob counts
- coincidence counts
- correlation trace
- Bell matrix summary

This allows the GUI to be tested without hardware and is useful during the porting phase.

### 9. Port the original control functions carefully
The old SPDC app has features like:
- connect/disconnect TimeTagger
- apply detector settings
- start/stop live data
- compute/measures counts
- calculate Bell value
- export results

The port should map them to a reduced but equivalent workflow:
- config panel
- start live acquisition
- observe signal curves
- evaluate coincidence matrix
- save/export data

### 10. Keep the app simple at first, then expand
The initial version should prioritize functioning live plots and basic measurement logic. Add more advanced features only after the core flow works.

Target MVP:
- PyQt window with VisPy plots
- channel configuration controls
- live acquisition toggle
- simulated or real TimeTagger data feed
- visible counts / coincidence trace
- Bell summary values

## Data flow design
The system should follow this pipeline:

1. User changes detector settings in the Qt controls.
2. Controller updates the measurement configuration model.
3. Adapter configures the TimeTagger or simulator.
4. Worker thread polls for new data.
5. Data is processed into plotting arrays and matrix values.
6. VisPy receives updated arrays and redraws the scene.
7. Bell math generates summary values.
8. UI labels and status readouts are refreshed.

## Recommended implementation order

### Phase 1: GUI shell and VisPy canvas
- create PyQt main window
- embed VisPy canvas
- prove the app opens and redraws
- verify navigation and control panel works

### Phase 2: data model and controller
- define detector configuration model
- add list of channels, delays, windows, and active states
- connect UI widgets to this model

### Phase 3: simulator backend
- implement synthetic data generator
- ensure plots update in real time with the GUI

### Phase 4: TimeTagger adapter integration
- port the hardware adapter from the SPDC package
- replace simulator with real hardware backend when available

### Phase 5: Bell calculation and matrix updates
- compute S-value and update summary text
- display live coincidence matrix

### Phase 6: export and persistence
- save counts and summary output
- add export utilities similar to `savedata.py`

## Testing plan
Add tests for:
- Bell math functions
- data conversion helpers
- simulator data validity
- model configuration logic
- adapter interface compatibility

Do not test the GUI visually in CI; test logic and data transformations instead.

## Risk areas
- Qt + VisPy backend mismatch
- VisPy canvas not displaying in embedded Qt window
- UI updates from worker thread
- TimeTagger hardware dependency during development
- differences between legacy SPDC assumptions and current project structure

## Mitigation
- use a single known backend (`PyQt5` in this project)
- keep the plotting area isolated in one class
- keep hardware logic behind an adapter boundary
- run simulator mode before hardware mode

## Success criteria
The port is successful when:
- the app launches from the current repo without the old pyqtgraph/matplotlib GUI dependency
- the main plotting area is a VisPy scene embedded in a PyQt window
- the detector settings can be changed live
- simulated SPDC-style data updates the lines dynamically
- Bell-value calculations remain available and testable
- the project works as a clean, maintainable Qt application

## Recommended first implementation milestone
Create a first working prototype with:
- `QMainWindow`
- `SceneCanvas` embedded in the right panel
- simple live plot with synthetic Alice/Bob data
- configuration controls for angle and live update
- Bell-style summary label

Once this works, connect the actual TimeTagger adapter and port the remaining SPDC logic.

## Final recommendation
Port in small steps rather than copying the old UI one-to-one. The SPDC GUI is functional, but it is tied to a now-legacy plotting stack. The cleanest path is to keep the measurement logic, replace the visualization layer, and add a simulator so the new GUI can be developed and validated independently of the hardware.
