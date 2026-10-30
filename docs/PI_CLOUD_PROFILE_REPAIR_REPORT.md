# PI CLOUD STATUS + PROFILE SWITCHING REPORT

## REPOSITORY
Path: E:\mainfolder\startup
Branch: main
Initial status: clean; initial HEAD 89df4aa (Qt asset hardening). No commit created.

## CLOUD STATUS
Old status architecture: UIController's expiring DeviceConsole network probe, Settings-derived readiness labels, legacy network_state setting and independent pending-upload labels.
Root cause of "Cloud unverified": successful authenticated operations did not update the separate header probe; its 180-second expiry returned Unverified despite successful delivery.
Canonical state implementation: app/connectivity.py, shared persisted settings and an observed device HTTP transport; diagnostics adds canonical cloud_status.
Successful API request behavior: authenticated 2xx sets Online and last_cloud_success; covers account/profile, catalogue, content stream, institute delivery, heartbeat and upload clients built through DeviceApi.
Health/ready behavior: network failure is Offline; reachable but not ready is Server unavailable, without changing Wi-Fi/internet facts. Later authenticated success can restore Online.
Authentication behavior: authenticated 401/403 records Authentication required; no credential content is persisted or logged by the status holder.
Header behavior: Checking…, Online, Offline, Server unavailable or Authentication required. SQLite revision observation propagates background changes through statusChanged to header and Settings.
Sync behavior: independent Up to date / Syncing / X pending / Failed / Authentication required. Actual successful cycle/upload timestamps replace the old button-press timestamp. Old Syncing markers expire after ten minutes.

## PROFILE SWITCHING
Old behavior: startup picker with no Home switching entry; only index selection and partial refresh.
New Home control: full name/context identity area with dropdown indicator and 48px touch height; accessible Switch Profile action. Hidden on assessment screens.
Profile Picker reuse: startup and switch modes; Switch Study Profile title, current-profile indicator and Cancel. Account rows also select a profile directly.
Runtime selected profile: stable ID activation, selected index retained across cache reordering, profile/PIN eligibility revalidated before activation.
Offline switching: last synchronized linked profiles selectable without network, logout or reconnection.
Last-profile persistence: last_active_profile_id; valid cached profile is highlighted at startup but explicit selection remains required.
Invalid profile handling: archived/missing/unlinked profiles excluded; active removal returns to picker; a revoked pending PIN target cannot activate.
Profile metadata: display cached cloud exam_context rather than inventing a grade. New profile creation uses the existing cloud account_create operation instead of creating local-only student rows.

## PROFILE-SCOPED REFRESH
Home: selected identity, resume and recent history recomputed.
Library: new profile's visible_question_sets and catalogue; catalogue and selection signals emitted.
Practice: same authorization filter; Settings installed-pack model gets storage refresh signal.
History: completed-attempt query filtered by selected profile; historyChanged emitted and cached review/result data cleared.
Resume: validated persisted attempt for current profile only.
Selected pack/question state: outgoing service paused, new in-memory service created; subject/chapter/set/navigation, selected Qt pack/version, institute setup, timer, result and review caches cleared.
Institute Work: current Qt screen is an existing placeholder; header updates and framework assignment selection clears. No new assignment UI is claimed.

## IN-PROGRESS ATTEMPTS
Profile A: durable attempt, responses, exact content/order and ownership remain untouched by switching.
Profile B: fresh application engine and B-only resume/history/content queries.
Switch away: pause to persist progress, detach in-memory engine; do not abandon.
Switch back: validated Continue/Resume finds A's original attempt.
Resume preservation: automated real-SQLite A/B/A test verifies original attempt and selected answer remain.
Mid-question safety: switching slots reject assessment routes; return Home through the existing leave/save flow first.
PIN: repaired a pre-existing nonexistent verify() call to use PinUnlock.unlock(), including stable-ID revalidation.

## TESTS
Cloud success: PASS (catalogue, content stream, profile sync, heartbeat/empty sync).
Cloud failure: PASS (unreachable server -> Offline).
Server unavailable: PASS (503 and ready-not-ready classification).
Authentication failure: PASS (401 and 403).
Profile A -> B: PASS (real SQLite and Qt controllers).
Library isolation: PASS.
Practice isolation: PASS.
History isolation: PASS (distinct completed content for A/B).
Resume preservation: PASS.
Offline switching: PASS.
Last-profile highlighting / invalid target / PIN revocation: PASS.
Qt tests: PASS, including required-asset offscreen loading and no-fragile-path checks.
Existing device tests: 340 passed in 44.64 seconds; one existing Starlette/httpx deprecation warning.
Ruff: PASS for whole repository.
Whitespace: PASS (git diff --check).

## FILES CHANGED
- app/api/client.py
- app/auth/account_device.py
- app/data/repo.py
- app/diagnostics.py
- app/sync/service.py
- app/sync/worker.py
- app/ui/controller.py
- app/ui/device.py
- app/ui_qt/controllers/app_controller.py
- app/ui_qt/controllers/assessment_controller.py
- app/ui_qt/controllers/profile_controller.py
- app/ui_qt/controllers/settings_controller.py
- app/ui_qt/qml/components/AppHeader.qml
- app/ui_qt/qml/screens/AccountScreen.qml
- app/ui_qt/qml/screens/ChapterScreen.qml
- app/ui_qt/qml/screens/ContentScreen.qml
- app/ui_qt/qml/screens/HistoryScreen.qml
- app/ui_qt/qml/screens/HomeScreen.qml
- app/ui_qt/qml/screens/InstituteWorkScreen.qml
- app/ui_qt/qml/screens/PackScreen.qml
- app/ui_qt/qml/screens/ProfilePickerScreen.qml
- app/ui_qt/qml/screens/SubjectScreen.qml
- tests/integration/test_pilot_readiness.py
- tests/test_ui_qt.py
- tests/unit/test_student_ui_flow.py
- app/connectivity.py
- tests/unit/test_cloud_state.py
- docs/QT_PROFILE_SWITCHING.md
- docs/QT_CONNECTIVITY_STATE.md
- docs/PI_CLOUD_PROFILE_REPAIR_REPORT.md

## CLOUD CHANGES
None. startup-cloud not modified; existing APIs suffice.

## PHYSICAL PI VALIDATION
NOT YET VERIFIED. No connected Pi/web acceptance session was available. Automated HTTP mocks and offscreen Qt do not constitute hardware acceptance.

## FINAL STATUS
Implementation and automated validation complete. Manual remaining acceptance: launch on Pi, confirm authenticated sync changes Checking to Online and receives new web content, switch Alex/Maya on Home, verify profile-scoped Home/Library/Practice/History and switch back without reboot. Verify touch targets and PIN entry on the real 800x480 display. No physical PASS is claimed.

PI CLOUD STATUS + PROFILE SWITCHING: PASS
