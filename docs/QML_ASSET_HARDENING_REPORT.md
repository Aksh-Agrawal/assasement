# QT/QML ASSET PATH HARDENING REPORT

ROOT CAUSE:
Why paths kept breaking: PrimaryButton.iconSource was a string. App.qml supplied icons/home.svg, which Image.source resolved relative to PrimaryButton.qml in components/. Other files guessed their own ../icons prefixes. Dynamic JS model strings had the same lack of URL origin.

CENTRALIZATION:
Asset helper: app/ui_qt/qml/Assets.qml, registered as singleton Assets 1.0 in qmldir. Qt.resolvedUrl runs only there for icons. Existing Theme/local-directory import conventions are reused.
Number of icons centralized: 29 (all actual SVG files, exact case).
Components converted: 6 — AppHeader, EmptyState, IconButton, NavRail, PrimaryButton, SecondaryButton.
Screens converted: 19 — AboutScreen, AccountScreen, ChapterScreen, ContentScreen, DiagnosticsScreen, HistoryScreen, HomeScreen, PackScreen, PairingScreen, ProfilePickerScreen, QuestionScreen, ResultScreen, SettingsScreen, SoftwareUpdateScreen, StartupScreen, SubjectScreen, SyncScreen, TestSetupScreen, WifiScreen.
App.qml recovery Home button also converted. Conditional branches and JS navigation/settings models carry resolved URLs. No colors, layout, navigation, typography or workflows changed.

PRIMARYBUTTON:
Old behavior: property string iconSource; downstream Image interpreted a context-free relative string.
New behavior: property url iconSource; Image uses it directly, without path rewriting. Empty icons are hidden using toString().length. SecondaryButton, IconButton and EmptyState use the same URL contract.

VALIDATION:
Missing asset test: every declaration checked for an existing file; a negative missing-file test verifies the guard.
Case-sensitive test: exact directory entry names compared at every path segment, even on Windows; wrong-case file and directory negative tests included.
QML load test: every declared singleton URL is evaluated by QML and loaded through an actual synchronous QML Image with Image.Ready asserted. The expanded smoke test instantiates all 16 components, all 27 screens and App.qml offscreen and captures Qt/QML warnings.
Fragile relative-path test: rejects direct icon paths and literal SVG/image/font assets outside Assets.qml, string iconSource declarations, and undefined Assets names.
QML warnings: zero required-asset Cannot open / Cannot load / file not found errors in passing smoke validation. Unrelated warnings are captured but are not the asset regression gate.
Device tests: 329 passed in 43.60 seconds, including Qt/QML and asset tests; one existing Starlette/httpx deprecation warning.
Ruff: entire repository passes.
Whitespace: git diff --check passes.

RUNTIME SOURCE FILES CHANGED:
- app/ui_qt/qml/App.qml
- app/ui_qt/qml/components/AppHeader.qml
- app/ui_qt/qml/components/EmptyState.qml
- app/ui_qt/qml/components/IconButton.qml
- app/ui_qt/qml/components/NavRail.qml
- app/ui_qt/qml/components/PrimaryButton.qml
- app/ui_qt/qml/components/SecondaryButton.qml
- app/ui_qt/qml/qmldir
- app/ui_qt/qml/screens/AboutScreen.qml
- app/ui_qt/qml/screens/AccountScreen.qml
- app/ui_qt/qml/screens/ChapterScreen.qml
- app/ui_qt/qml/screens/ContentScreen.qml
- app/ui_qt/qml/screens/DiagnosticsScreen.qml
- app/ui_qt/qml/screens/HistoryScreen.qml
- app/ui_qt/qml/screens/HomeScreen.qml
- app/ui_qt/qml/screens/PackScreen.qml
- app/ui_qt/qml/screens/PairingScreen.qml
- app/ui_qt/qml/screens/ProfilePickerScreen.qml
- app/ui_qt/qml/screens/QuestionScreen.qml
- app/ui_qt/qml/screens/ResultScreen.qml
- app/ui_qt/qml/screens/SettingsScreen.qml
- app/ui_qt/qml/screens/SoftwareUpdateScreen.qml
- app/ui_qt/qml/screens/StartupScreen.qml
- app/ui_qt/qml/screens/SubjectScreen.qml
- app/ui_qt/qml/screens/SyncScreen.qml
- app/ui_qt/qml/screens/TestSetupScreen.qml
- app/ui_qt/qml/screens/WifiScreen.qml
- app/ui_qt/qml/Assets.qml (new)

TEST FILES CHANGED:
- tests/test_ui_qt.py
- tests/test_qml_assets.py (new)

DOCUMENTATION:
- docs/QML_ASSET_AUDIT.md: every original source/icon reference and exact asset filenames.
- docs/QML_ASSET_HARDENING_REPORT.md: this report.

DIRECT ICON REFERENCES REMAINING:
Zero outside Assets.qml. Its 29 declarations intentionally own icons/<exact-name>.svg. App.qml Loader retains screen-component routes; those are not image assets. Theme uses system-ui and no bundled font file.

FINAL STATUS
Implementation and automated validation complete. startup-cloud untouched. Physical Pi launch not tested; no physical PASS is claimed. The existing python -m app.ui_qt.main command and environment variables remain unchanged.

QT/QML ASSET PATH HARDENING: PASS
