# Qt/QML device UI verification

## Default UI

The normal Pi launch path is PySide6/Qt Quick. The GUI install extra installs PySide6; the kiosk session and setup documentation launch app.ui_qt.main. The older pygame prototype remains an optional development extra, not the normal kiosk UI. The illustrated paper-and-ink background and subject art remain in place.

The practice setup presents topic, difficulty, question count, shuffle and mode within the existing illustrated layout. Selectors use the Basic Qt Controls style for consistent touch-device rendering. Missing palette/type aliases and QML layout warnings found during capture were corrected.

## Automated evidence

- QML suite: 20 passed when run in isolation; the suite renders both Progress and History routes at 800x480.
- Combined repository suite: 399 passed, one localhost Uvicorn integration test deselected.
  That test fails to start its server under this Windows Python 3.14 host; rerun it on the
  supported Linux/Python 3.13.5 environment.
- Ruff check on the full repository: passed.
- Qt startup smoke: exited successfully; backend selected Mock / Offline.
- QML render test opens the app at exactly 800×480 and captures practice setup and Quick Add.
- Capture harness rendered Progress/Analytics and Assessment History as separate routes, plus 26 other named Qt screens, at 800×480 to ../artifacts/pi-ui-verification/.
- Progress displays SQLite-backed completed attempts, graded accuracy, correct/incorrect/skipped answers, confidence outcomes, practice duration, average answer time and a chronological ten-attempt accuracy trend.
- Qt regression tests verify cloud History refresh and deduplication of an echoed local Pi attempt using a temporary SQLite database.
- Screens were rendered with Qt Quick's offscreen platform on the development host. This is simulated 800×480 rendering, not a physical display test.
- Test setup screenshot: ../artifacts/pi-ui-verification/07_test_setup_800x480.png
- Progress screenshot: ../artifacts/pi-ui-verification/13_progress_analytics_800x480.png
- History screenshot: ../artifacts/pi-ui-verification/14_history_800x480.png
- Quick Add screenshot: ../artifacts/pi-ui-verification/28_quick_add_800x480.png
- Existing illustration assets remain visible and selector labels are readable in the captures.

Run from the device repository root:

~~~powershell
.\.venv\Scripts\python.exe -m pytest tests/test_ui_qt.py -q
.\.venv\Scripts\python.exe -m app.ui_qt.capture_screenshots
~~~

The capture harness uses a temporary test database under the OS temp directory and does not modify a working SQLite database.

## Automated navigation

The capture harness waits for dynamic QML delegates before switching screens. Final 28-screen capture completed without QML warnings or stderr output.

## Not verified on hardware

The development host is not the Raspberry Pi Zero 2 W. No claim is made for actual panel colors, touch/controller input, display rotation, memory pressure, startup latency, Wi-Fi recovery or kiosk service behavior. Complete the checklist in PHYSICAL_PI_ACCEPTANCE.md on the Pi.
