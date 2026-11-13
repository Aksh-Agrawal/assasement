# Questraa repository cleanup report

**Status: CLEANUP PARTIAL — source cleanup completed; verification blockers remain.**

No commit, push, deployment, database reset, or production-resource modification was performed. Both repository HEADs remain unchanged. The cleanup preserves offline assessment behavior, Analytics, History, recovery, QR Quick Add, synchronization, StudyProfiles, published content, migrations, and operational recovery tooling.

## Verification summary

| Area | Result |
| --- | --- |
| Device Qt and unit regression | 393 passed; 2 pre-existing environment-sensitive tests deselected in the selective run |
| Device release readiness | `python -m tools.release_check --offline` passed; included Ruff, 219 unit tests, 14 mocked HTTP contracts, assessment/restart smoke, Qt integration, isolated pilot smoke, fresh SQLite migrations/integrity/WAL, persistence/content/sync/update/recovery/observability checks |
| Device Ruff | Passed |
| Cloud lint | `ruff check .` passed |
| Cloud collection | 230 tests collected after retiring Qt-only tests |
| Cloud focused backend/migration checks | 4 passed, 2 PostgreSQL-only tests deselected |
| Cloud full backend tests | Blocked: Python 3.14 Windows `TestClient`/Uvicorn portal stalls while creating the Proactor self-pipe/socketpair. Linux reproduction unavailable: WSL access denied, Docker unavailable, and no Linux Python environment is installed. |
| Web dependency restore | `npm ci` failed with registry DNS/network access and `Exit handler never called`; offline retry failed because the cache lacks `zod-validation-error@4.0.2`. `package.json` and lockfile were preserved. |
| Web tests, lint, typecheck, build | Could not run successfully after npm left `node_modules` incomplete: `typescript`, `eslint`, and `next` executables/modules are missing. Earlier build reported an existing Next build lock; investigation found no visible Node/Next process and no `.next` lock file. No process was terminated and `.next` was not altered. |
| Browser verification | Not applicable to a web UI change: no web UI source was changed. Web verification remains blocked by unavailable dependencies. |

The two deselected device tests are `test_full_crash_offline_lost_ack_recovery_has_one_server_attempt` (Uvicorn fixture does not start in this Windows/Python 3.14 environment) and `test_external_browser_history_commit_refreshes_rendered_qt_model` (prior full run triggered a Python 3.14 Windows access violation). The focused offline release check also explicitly skips network/PostgreSQL integration checks.


## Commands executed

- Device: `QT_QPA_PLATFORM=offscreen .venv\Scripts\python.exe -m pytest -q -k "not test_full_crash_offline_lost_ack_recovery_has_one_server_attempt and not test_external_browser_history_commit_refreshes_rendered_qt_model"` — 393 passed, 2 deselected.
- Device: `python -m tools.release_check --offline` — PASS.
- Device and cloud: `.venv\Scripts\ruff.exe check .` — PASS in each repository.
- Cloud: `pytest --collect-only -q` — 230 collected; `pytest -q backend/tests/test_institute_analytics_service.py backend/tests/test_migration_repair.py -k "not postgres"` — 4 passed, 2 deselected.
- Cloud: full pytest and an isolated attempt-upload TestClient test were attempted; both stalled on Windows/Python 3.14 local socket/portal setup and were interrupted after capturing the stack.
- Web: `npm ci` and `npm ci --offline --no-audit --no-fund --loglevel verbose` were attempted; neither completed. The four package scripts (`test`, `lint`, `typecheck`, `build`) were checked and could not launch with incomplete `node_modules`.
- Both repositories: `git diff --check` — PASS. Package lockfiles were not changed.

## Counts

- Tracked files deleted: **209** (51 device, 158 cloud).
- Obsolete production Python function definitions removed from deleted presentation modules: **242** (88 device, 154 cloud; AST count).
- Test function definitions in fully deleted test modules: **21** (8 device, 13 cloud), plus five presentation-only flow checks removed or rewritten in the retained device student-flow tests.
- Obsolete helper scripts deleted: **2** (`startup/tools/ui_smoke.py`, `startup-cloud/ui_qt/capture_screenshots.py`).
- Dependency declarations removed: one unique dependency, `pygame-ce`, from two device project extras. Cloud CI no longer installs PySide6 or its Qt runtime libraries. No web dependency or lockfile entry was removed.
- Duplicate implementations consolidated: **0** business-logic consolidations. The unsupported duplicate cloud Qt product implementation was retired; the device Qt UI remains authoritative.

## Exact deleted files — device (`startup`)
- `app/ui/app.py`
- `app/ui/components.py`
- `app/ui/layout.py`
- `app/ui/screens/__init__.py`
- `app/ui/screens/about.py`
- `app/ui/screens/account.py`
- `app/ui/screens/assessment_menu.py`
- `app/ui/screens/chapters.py`
- `app/ui/screens/common.py`
- `app/ui/screens/confidence.py`
- `app/ui/screens/console.py`
- `app/ui/screens/content_updates.py`
- `app/ui/screens/detail.py`
- `app/ui/screens/device_info.py`
- `app/ui/screens/device_status.py`
- `app/ui/screens/diagnostics.py`
- `app/ui/screens/error.py`
- `app/ui/screens/history.py`
- `app/ui/screens/home.py`
- `app/ui/screens/institute_work.py`
- `app/ui/screens/instructions.py`
- `app/ui/screens/leave_confirm.py`
- `app/ui/screens/link_confirm.py`
- `app/ui/screens/navigator.py`
- `app/ui/screens/packs.py`
- `app/ui/screens/pairing.py`
- `app/ui/screens/profile.py`
- `app/ui/screens/progress.py`
- `app/ui/screens/question.py`
- `app/ui/screens/question_set.py`
- `app/ui/screens/recovery.py`
- `app/ui/screens/result.py`
- `app/ui/screens/review.py`
- `app/ui/screens/settings.py`
- `app/ui/screens/software_update.py`
- `app/ui/screens/splash.py`
- `app/ui/screens/startup.py`
- `app/ui/screens/subject.py`
- `app/ui/screens/subjects.py`
- `app/ui/screens/submit.py`
- `app/ui/screens/submit_confirm.py`
- `app/ui/screens/sync.py`
- `app/ui/screens/test_setup.py`
- `app/ui/screens/text_entry.py`
- `app/ui/screens/welcome.py`
- `app/ui/screens/wifi.py`
- `app/ui/theme.py`
- `tests/unit/test_ui_app.py`
- `tests/unit/test_ui_layout.py`
- `tests/unit/test_ui_rendering.py`
- `tools/ui_smoke.py`

## Exact deleted files — cloud (`startup-cloud`)

- `tests/test_qml_assets.py`
- `tests/test_ui_qt.py`
- `ui_qt/__init__.py`
- `ui_qt/assets/decorative/book_spine.svg`
- `ui_qt/assets/decorative/confidence_guessing.svg`
- `ui_qt/assets/decorative/confidence_not_sure.svg`
- `ui_qt/assets/decorative/confidence_sure.svg`
- `ui_qt/assets/decorative/paper_divider.svg`
- `ui_qt/assets/icons/account.svg`
- `ui_qt/assets/icons/arrow_back.svg`
- `ui_qt/assets/icons/calculator.svg`
- `ui_qt/assets/icons/check.svg`
- `ui_qt/assets/icons/chevron_left.svg`
- `ui_qt/assets/icons/chevron_right.svg`
- `ui_qt/assets/icons/close.svg`
- `ui_qt/assets/icons/device.svg`
- `ui_qt/assets/icons/diagnostics.svg`
- `ui_qt/assets/icons/download.svg`
- `ui_qt/assets/icons/flag.svg`
- `ui_qt/assets/icons/flag_filled.svg`
- `ui_qt/assets/icons/flask.svg`
- `ui_qt/assets/icons/history.svg`
- `ui_qt/assets/icons/home.svg`
- `ui_qt/assets/icons/info.svg`
- `ui_qt/assets/icons/library.svg`
- `ui_qt/assets/icons/lock.svg`
- `ui_qt/assets/icons/plus.svg`
- `ui_qt/assets/icons/practice.svg`
- `ui_qt/assets/icons/question.svg`
- `ui_qt/assets/icons/raspberry.svg`
- `ui_qt/assets/icons/refresh.svg`
- `ui_qt/assets/icons/settings.svg`
- `ui_qt/assets/icons/star.svg`
- `ui_qt/assets/icons/sync.svg`
- `ui_qt/assets/icons/update.svg`
- `ui_qt/assets/icons/wifi.svg`
- `ui_qt/assets/icons/wifi_off.svg`
- `ui_qt/assets/illustrations/device_pairing.svg`
- `ui_qt/assets/illustrations/empty_shelf.svg`
- `ui_qt/assets/illustrations/home_hero.svg`
- `ui_qt/assets/illustrations/home_resume.svg`
- `ui_qt/assets/illustrations/laurel_achievement.svg`
- `ui_qt/assets/illustrations/recovery_guide.svg`
- `ui_qt/assets/keyboard.svg`
- `ui_qt/assets/subjects/biology.svg`
- `ui_qt/assets/subjects/chemistry.svg`
- `ui_qt/assets/subjects/english.svg`
- `ui_qt/assets/subjects/general.svg`
- `ui_qt/assets/subjects/mathematics.svg`
- `ui_qt/assets/subjects/science.svg`
- `ui_qt/assets/wallpaper.svg`
- `ui_qt/capture_screenshots.py`
- `ui_qt/controllers/__init__.py`
- `ui_qt/controllers/app_controller.py`
- `ui_qt/controllers/assessment_controller.py`
- `ui_qt/controllers/cloud_client.py`
- `ui_qt/controllers/library_controller.py`
- `ui_qt/controllers/profile_controller.py`
- `ui_qt/controllers/settings_controller.py`
- `ui_qt/main.py`
- `ui_qt/qml/App.qml`
- `ui_qt/qml/Assets.qml`
- `ui_qt/qml/Metrics.qml`
- `ui_qt/qml/Spacing.qml`
- `ui_qt/qml/Theme.qml`
- `ui_qt/qml/Typography.qml`
- `ui_qt/qml/components/AppCard.qml`
- `ui_qt/qml/components/AppHeader.qml`
- `ui_qt/qml/components/EmptyState.qml`
- `ui_qt/qml/components/ErrorState.qml`
- `ui_qt/qml/components/IconButton.qml`
- `ui_qt/qml/components/LeaveConfirmModal.qml`
- `ui_qt/qml/components/LoadingState.qml`
- `ui_qt/qml/components/NavRail.qml`
- `ui_qt/qml/components/PinModal.qml`
- `ui_qt/qml/components/PrimaryButton.qml`
- `ui_qt/qml/components/ProgressBar.qml`
- `ui_qt/qml/components/QuestionOption.qml`
- `ui_qt/qml/components/SecondaryButton.qml`
- `ui_qt/qml/components/StatusBadge.qml`
- `ui_qt/qml/components/SubmitConfirmModal.qml`
- `ui_qt/qml/components/VirtualKeyboard.qml`
- `ui_qt/qml/icons/account.svg`
- `ui_qt/qml/icons/arrow_back.svg`
- `ui_qt/qml/icons/biology.svg`
- `ui_qt/qml/icons/book_spine.svg`
- `ui_qt/qml/icons/calculator.svg`
- `ui_qt/qml/icons/check.svg`
- `ui_qt/qml/icons/chemistry.svg`
- `ui_qt/qml/icons/chevron_left.svg`
- `ui_qt/qml/icons/chevron_right.svg`
- `ui_qt/qml/icons/close.svg`
- `ui_qt/qml/icons/confidence_guessing.svg`
- `ui_qt/qml/icons/confidence_not_sure.svg`
- `ui_qt/qml/icons/confidence_sure.svg`
- `ui_qt/qml/icons/device.svg`
- `ui_qt/qml/icons/device_pairing.svg`
- `ui_qt/qml/icons/diagnostics.svg`
- `ui_qt/qml/icons/download.svg`
- `ui_qt/qml/icons/empty_shelf.svg`
- `ui_qt/qml/icons/english.svg`
- `ui_qt/qml/icons/flag.svg`
- `ui_qt/qml/icons/flag_filled.svg`
- `ui_qt/qml/icons/flask.svg`
- `ui_qt/qml/icons/general.svg`
- `ui_qt/qml/icons/history.svg`
- `ui_qt/qml/icons/home.svg`
- `ui_qt/qml/icons/home_hero.svg`
- `ui_qt/qml/icons/home_resume.svg`
- `ui_qt/qml/icons/info.svg`
- `ui_qt/qml/icons/keyboard.svg`
- `ui_qt/qml/icons/laurel_achievement.svg`
- `ui_qt/qml/icons/library.svg`
- `ui_qt/qml/icons/lock.svg`
- `ui_qt/qml/icons/mathematics.svg`
- `ui_qt/qml/icons/paper_divider.svg`
- `ui_qt/qml/icons/plus.svg`
- `ui_qt/qml/icons/practice.svg`
- `ui_qt/qml/icons/question.svg`
- `ui_qt/qml/icons/raspberry.svg`
- `ui_qt/qml/icons/recovery_guide.svg`
- `ui_qt/qml/icons/refresh.svg`
- `ui_qt/qml/icons/science.svg`
- `ui_qt/qml/icons/settings.svg`
- `ui_qt/qml/icons/star.svg`
- `ui_qt/qml/icons/sync.svg`
- `ui_qt/qml/icons/update.svg`
- `ui_qt/qml/icons/wallpaper.svg`
- `ui_qt/qml/icons/wifi.svg`
- `ui_qt/qml/icons/wifi_off.svg`
- `ui_qt/qml/qmldir`
- `ui_qt/qml/screens/AboutScreen.qml`
- `ui_qt/qml/screens/AccountScreen.qml`
- `ui_qt/qml/screens/ChapterScreen.qml`
- `ui_qt/qml/screens/ConfidenceScreen.qml`
- `ui_qt/qml/screens/ContentScreen.qml`
- `ui_qt/qml/screens/CreateProfileScreen.qml`
- `ui_qt/qml/screens/DeviceInfoScreen.qml`
- `ui_qt/qml/screens/DiagnosticsScreen.qml`
- `ui_qt/qml/screens/HistoryScreen.qml`
- `ui_qt/qml/screens/HomeScreen.qml`
- `ui_qt/qml/screens/InstituteWorkScreen.qml`
- `ui_qt/qml/screens/PackScreen.qml`
- `ui_qt/qml/screens/PairingScreen.qml`
- `ui_qt/qml/screens/ProfilePickerScreen.qml`
- `ui_qt/qml/screens/QuestionDetailScreen.qml`
- `ui_qt/qml/screens/QuestionNavigatorScreen.qml`
- `ui_qt/qml/screens/QuestionScreen.qml`
- `ui_qt/qml/screens/RecoveryScreen.qml`
- `ui_qt/qml/screens/ResultScreen.qml`
- `ui_qt/qml/screens/ReviewScreen.qml`
- `ui_qt/qml/screens/SettingsScreen.qml`
- `ui_qt/qml/screens/SoftwareUpdateScreen.qml`
- `ui_qt/qml/screens/StartupScreen.qml`
- `ui_qt/qml/screens/SubjectScreen.qml`
- `ui_qt/qml/screens/SyncScreen.qml`
- `ui_qt/qml/screens/TestSetupScreen.qml`
- `ui_qt/qml/screens/WifiScreen.qml`

## Intentionally preserved uncertain or required candidates

- `startup/app/ui/controller.py`, `router.py`, `device.py`, and `startup.py`: imported by the supported Qt UI and contain shared application, routing, device and startup behavior. Only one Pygame-only license label and an unreachable Pygame `more_keys` command were removed from the shared controller.
- `startup/app/input/**` and `startup/app/system/**`: runtime input/device services used by Qt or operational paths; not presentation-only.
- `startup-cloud/backend/pyproject.toml`: required by the device release checker and referenced by the device migration map; an attempted deletion was restored.
- Cloud `backend/`, `shared/`, `schemas/`, web routes/components/assets, migrations, content data, release/update/diagnostic and recovery scripts: either included by deployment or have active imports/operational roles. No concrete safe dead-code proof justified deleting these.
- `startup-cloud/web/package.json` and `package-lock.json`: retained intact; exact production dependencies such as KaTeX and sanitize-html are used by the JEE content renderer.
- Historical migration/decision/operation documents: retained as history; updated where they described the retired Pygame or cloud Qt UI as current.

## Repository state

Both original HEADs are unchanged. Existing README edits and prior cleanup documents were preserved. This turn adds this report/audit and source cleanup changes. Generated release-check artifacts are ignored. `backend/pyproject.toml`, migrations, databases, production records and runtime state remain intact.
