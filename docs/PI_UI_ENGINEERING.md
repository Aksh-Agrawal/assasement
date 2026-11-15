# Questraa device UI engineering and verification

## Interface and runtime changes

- Startup and Home now use the Questraa name and a quiet paper canvas. The study desk shows one next action and compact subject cards with a consistent SVG treatment. The same subject card works in Home and the Practice Library.
- Primary and secondary buttons, icon buttons, the navigation rail and answer choices use Qt Quick Controls button semantics. The controls provide keyboard activation, visible focus and distinct pressed and disabled states. The virtual keyboard fits every key at 800 × 480 and returns focus after dismissal.
- The screen router loads one route at a time. It also instantiates the virtual keyboard and submission overlay on demand. Submission keeps the question or navigator visible under the overlay. Opening, cancelling and confirming submission now use the assessment engine's state transitions.
- Practice pack grids use a typed QML delegate backed by a `QAbstractListModel`. Updating a download status emits the changed roles for the affected row. Loading another page can replace its rows. A stationary skeleton preserves card geometry while a page loads.
- SQLite catalog refreshes decide which versions the learner can use before materializing question data. The GUI reuses the core catalog refresh after device jobs. SQLite connectivity and scheduler helpers explicitly close their short-lived connections.
- Small SVG icons rasterize at their displayed dimensions in the updated controls. Removing the global wallpaper eliminates the decode of its 1,376 × 768 embedded raster and the full-screen image node. The existing subject and educational illustrations remain.

## Technology decisions

| Technology | Decision and evidence | Runtime and deployment impact |
| --- | --- | --- |
| `QAbstractListModel` | Adopted for the downloaded and online Practice grids. Covers large data sets and frequent changes to download state. Qt tests verify role-specific signals and the real grid interaction. Small lists still use their existing bindings. | Holds one snapshot per model and keeps updates on the GUI thread. Uses QtCore already shipped with PySide6. |
| Qt Quick `Loader` | Kept the route loader and lazily instantiated the keyboard and submit overlay. Screens still swap synchronously so assessment focus and operation order remain predictable. | Frees the closed overlays' live items. Opening the keyboard now incurs its construction cost. |
| Qt Quick Controls and transitions | Adopted native buttons with custom layouts and accessible state. Catalog, submit and keyboard visibility follow existing state signals. Motion is limited to short state feedback. | Uses the existing Basic style. The Wi-Fi loading indicator and keyboard have no continuous animation. |
| `QThreadPool` and `QRunnable` | Existing device and Quick Add workers already perform network and file operations in the background. Reused their result handoff and reduced unnecessary foreground SQLite work. | No second pool, worker-owned repository changes or SQLite cross-thread access. Refreshing a very large eligible offline library still takes foreground time. |
| Qt Resource System | `rcc` 6.12.0 is available. Kept relative URLs in the asset singleton and the existing file-based release layout. The Qt asset suite resolves and loads the packaged paths. | A resource module would add a generator step. These measurements do not establish a speed benefit from that change. |
| QML cache and ahead-of-time compilation | The app loads QML from disk through PySide6 and uses the existing Qt runtime cache policy. `qmlcachegen` is available on the host. A Qt CMake module and matching target build would change the OTA pipeline. | No generated QML cache is shipped. The benchmark disabled the disk cache for both runs. |
| Design and preview tools | Ran `qmlformat` for the two new QML component files and `qmllint` across the QML tree. Qt Creator, Design Studio, the preview executable, `qmlprofiler` and `qmltestrunner` were unavailable in the host tool search. The real-app capture harness supplies Python context properties for visual iteration. | Tests use PySide6 QtTest with the existing pytest application fixture. No new dependency or editor configuration. |
| Typography and effects | Uses system Arial and Georgia on Windows and requests DejaVu Sans and DejaVu Serif on Linux. Retains SVG art and simple fills. | Font files are supplied by the OS. Font availability and fallback need a Pi check. ShaderEffect, 3D and animated texture layers have no demonstrated benefit here. |

The production changes use APIs available in the existing Qt 6.6+ range and the existing Python language baseline. The ARM64/Python 3.13 runtime and actual screen still need physical verification. [Qt Quick performance](https://doc.qt.io/qtforpython-6/overviews/qtquick-performance.html) · [Loader](https://doc.qt.io/qt-6/qml-qtquick-loader.html) · [Qt Resource tool](https://doc.qt.io/qtforpython-6/tools/pyside-rcc.html) · [QML disk cache](https://doc.qt.io/qt-6/qmldiskcache.html) · [QML profiler](https://doc.qt.io/qt-6/qtquick-profiling.html)

## Repeatable verification

From the device repository root on Windows:

~~~powershell
.\.venv\Scripts\python.exe -m app.ui_qt.capture_screenshots --output artifacts/ui-review
.\.venv\Scripts\python.exe -m app.ui_qt.capture_screenshots --output artifacts/ui-review-large --extra-packs 120
.\.venv\Scripts\python.exe -m pytest tests/test_ui_qt.py tests/test_qml_assets.py tests/test_quick_add.py tests/content -q
~~~

Use the device venv's Python on Linux. Set `QML_DISABLE_DISK_CACHE=1` for both checkouts when comparing cold QML startup. Choose separate output directories for each run. The capture checks the QML router for coverage, verifies 800 × 480 image dimensions, records QML warnings and writes `measurements.json`. It seeds its own temporary SQLite database, uses sample credentials, and renders the online catalog and QR using fixtures. Tests separately use mocked HTTP for the catalog and real Qt keyboard and pointer events.

The standard run covered all **29 registered screen files** and recorded **38 states**, including the keyboard, pause and submit overlays, catalog loading and error states, a download in progress, and Home with an empty library. The comparison captures came from a snapshot of the local checkout taken before these changes. Both current capture runs reported zero QML engine warnings. Static analysis reported legacy context-property/reference warnings and singleton-module diagnostics. No new lint tool dependency is required.

The device suite passed 429 tests with the single known Uvicorn integration test excluded after reproducing its timeout in both checkouts. Ruff passed on the touched Python files. The Windows wheel build stopped at dependency discovery because the venv lacks setuptools.

## Windows offscreen measurements

Python 3.14.5, PySide6 6.12.0, Qt Quick software renderer, 800 × 480. Each startup figure is one observed run. Operations listed as medians used 11 samples per run. Process memory is measured working set, which includes Python, Qt and the capture harness. QObject counts include Qt window descendants. These measurements vary with host load.

| Measurement | Before | After | Fixture |
| --- | ---: | ---: | --- |
| QML load to first frame grab | 570 ms | 291 ms | Standard |
| Startup working set | 114.0 MiB | 107.7 MiB | Standard |
| Startup window QObject descendants | 197 | 102 | Standard |
| Catalog state change to frame grab, median | 46.5 ms | 13.7 ms | Standard |
| Catalog scroll step to frame grab, median | 5.44 ms | 5.94 ms | Standard |
| Home → Practice round trip with frame grabs, median | 173 ms | 175 ms | Standard |
| Refresh 3 eligible packs with 120 private packs owned by the other learner, median | 172.1 ms | 2.22 ms | Large |
| Refresh the learner who owns all 120 private packs, median | 2,508 ms | 1,090 ms | Large |
| Home → Practice round trip with frame grabs, median | 122 ms | 213 ms | Large |

The loaded-grid status sample starts at the controller's change notification. It excludes real HTTP, which also depends on the existing device completion poll and network conditions. Scrolling is a scripted position change and frame capture. These samples do not establish touch FPS, binding-level profiler timings or a general navigation speedup. The large learner's catalog refresh can still block the GUI.

## Physical Raspberry Pi verification

Run on Raspberry Pi Zero 2 W with 64-bit Raspberry Pi OS, Python 3.13 and the actual 800 × 480 screen. Use a test profile and temporary database for the capture workflow.

1. Measure cold boot to interactive Home and time Home, Library, Practice, History and assessment navigation on the production graphics backend. Test touch, USB keyboard, focus, long subject names and Linux font fallback. Check for clipping in both keyboard layouts.
2. Compare peak RSS, CPU, input latency and dropped frames while scrolling a full eligible library and opening illustrated questions. Use QML Profiler on a development build to separate binding, JavaScript and rendering costs if a compatible kit is available.
3. While offline, open and complete a practice set. Confirm UI feedback, confidence, submission, History and offline resume. Reconnect and measure the delay from Wi-Fi recovery through the visible queue and sync states.
4. Rerun the localhost crash-recovery integration test under Linux/Python 3.13. Its Uvicorn startup timeout reproduced before and after the UI changes on Windows. Local Qt, content and offline assessment checks ran independently of that test.
