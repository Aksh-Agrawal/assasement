# PI CONTENT + ATTEMPT RECONCILIATION REPAIR REPORT

## REPOSITORY
Path: E:\mainfolder\startup
Branch: main
Initial status: clean working tree. No commits created.

## ROOT CAUSES

| Symptom | Root cause | Fix |
|---|---|---|
| Stale Practice heading | can_start_pack allowed any shared/legacy installed version without checking an owned profile's grant | Owned profiles now require their own link-specific eligibility |
| Stale Library heading | Same shared-byte bypass fed visible_question_sets; physical storage was treated as availability | Profile-filtered installed sets; cloud metadata remains profile scoped |
| Profile already has in-progress attempt | Catalogue removal changed eligibility but left attempts.status=in_progress and its unique profile lock | Atomically abandon revoked partial attempts, preserving response/order/event rows |
| Resume validation error | AssessmentEngine.resume_attempt requires IDLE; service reused IN_QUESTION engine | Validate persisted state, pause valid timing, restore through a fresh engine |
| Qt stale model | Background SQLite commits/status changes did not emit Library property notifications; selected IDs and engine persisted | Observe data_version/local writes, refresh Library, clear revoked selection/session/timer, emit signals |

The exact hardware exception was not captured in this session. The matching engine transition failure is reproduced by repeated resume; broken order validation is tested separately. Workspace database inspected read-only; physical Pi database unavailable.

## STATE MODEL
Cloud authoritative state: account, StudyProfile ownership/link, personal selection and eligibility.
Profile visibility: owned profiles require current exact grants; independent across profiles.
Physical pack storage: SQLite question_sets/questions retained regardless of removal; no physical deletion.
In-progress attempts: eligible exact-version attempts remain resumable offline; revoked/invalid partial attempts become abandoned and non-blocking. Institute removal follows the same terminal policy.
Completed attempts: preserved, including ownership, responses and content references.
Resume state: persisted status query plus in-memory engine; abandoned row clears query pointer, UI drops engine/timer pointer.

## RECONCILIATION
Startup: repository opens/migrates then runs repeat-safe transactional repair against the cached snapshot.
Automatic sync: profile delivery refresh transaction replaces grants and repairs partial attempts.
Sync Now: existing run_cycle(refresh=True) uses the same profile delivery service.
Profile switching: reloads profile-scoped catalogue and emits Library notifications.

## REMOVAL FLOW
Cloud removal received: complete paginated catalogue, including empty list.
Profile selection removed: eligible=0 in cache; retained metadata is not availability.
Library visibility removed: owned-profile grant filter.
Practice visibility removed: same filter.
Selected pack cleared: invalid Qt pack/version/subject/chapter reset.
Resume pointer cleared: status no longer in_progress; abandoned live engine/timer dropped.
Orphan attempt repaired: existing abandoned status, within catalogue transaction.
Qt model refreshed: catalogue, selection, question, navigator and timer signals; no restart.
Offline behavior: last successful snapshot retained on network failure.
Failure behavior: injected repair failure rolls back both eligibility and attempt changes.

## TESTS
Removed Practice item: automated coverage.
Installed pack but revoked profile: automated legacy/shared and private-byte coverage.
Two-profile isolation: automated A removed/B retained coverage.
Orphan attempt: automated revocation and startup repair coverage.
Completed history preservation: automated completed row, result and response preservation coverage.
Resume cleanup: automated durable pointer and live engine cleanup coverage.
New assessment after cleanup: automated authorized new start coverage.
Offline valid practice: existing offline start, resume and still-selected exact-version coverage passes.
Qt refresh: offscreen real repository test changes grants on a second SQLite connection and verifies cards/signals/selection/session.
Existing device tests: 323 passed, one existing Starlette/httpx deprecation warning (41.76 seconds). Full tests directory includes Qt, offline assessment, resume, content, profile isolation, sync and fault recovery.
Ruff: entire repository passes.
Whitespace: git diff --check passes.

## FILES CHANGED
- app/data/repo.py: authorization, shared transactional repair, startup validation, revision observation.
- app/assessment.py: repair before start/resume, fresh engine restoration, invalid session cleanup.
- app/ui/controller.py: resume validation and filtered selection bounds.
- app/ui_qt/controllers/app_controller.py: background commit detection and Library refresh.
- app/ui_qt/controllers/library_controller.py: selection/session cleanup and signals.
- app/ui_qt/controllers/assessment_controller.py: controller registration and safe resume error text with traceback logging.
- app/ui_qt/controllers/profile_controller.py: Library refresh on switching.
- tests/content/test_profile_library.py: old-state reproduction, rollback, repeated resume, history/isolation regressions; removal expectation updated to requested policy.
- tests/content/test_institute_work.py: terminal removal policy and completed ownership/history preservation.
- tests/test_ui_qt.py: actual cross-connection background removal and model refresh regression.
- tests/unit/test_profile_links.py: explicit grant required for owned-profile start fixture.
- app/diagnostics.py and tests/unit/test_connectivity_mapping.py: remove two existing unused bindings so whole-repository Ruff passes; health request retained.
- docs/CONTENT_RECONCILIATION_AUDIT.md: state inventory and traced root causes.
- docs/CONTENT_RECONCILIATION_POLICY.md: authority, removal, offline and conservative garbage collection policy.
- docs/CONTENT_RECONCILIATION_REPAIR_REPORT.md: this report.

## CLOUD CHANGES
None. Existing selected-profile catalogue communicates removal completely; startup-cloud read only.

## DEFERRED
Physical-Pi acceptance for Chemistry Basics and Cell: The Unit of Life, actual web removal/Sync Now, hardware offline resume and physical History inspection. No connected Pi or authenticated acceptance environment was provided. Automated tests exercise these device paths using temporary SQLite databases, mock cloud transport and real offscreen Qt controllers; they do not substitute for hardware acceptance.

## FINAL STATUS
Implementation and automated validation complete. Overall acceptance cannot be certified until the required physical-Pi/web manual flows are run.
Blocker: physical Pi and authenticated web acceptance environment unavailable in this session.

PI CONTENT + ATTEMPT RECONCILIATION: FAIL
