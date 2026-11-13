# Device/cloud integration report

## Repositories and comparison

- Target: startup (this repository), branch main.
- Reference: startup-cloud, master at b74ebce8979a6af879599b7d38e271bbe14cc587.
- The reference checkout was inspected locally; it had no newer working-tree changes at audit time.
- No cloud production database, migration, or cloud source was modified.

## Compatible workflows

1. A paired device uses its bearer credential for cloud operations. StudyProfile-bound content uses the profile link and selected local profile.
2. A complete profile catalog is cached; exact pack bytes are downloaded, size/hash checked, validated and installed transactionally in SQLite.
3. MCQ attempts use local pack bytes and the installed version. Responses and progress persist locally so a network outage does not block practice, save/resume, submission or review.
4. Pending completed attempts are uploaded with a stable UUID/idempotency key. The device payload includes per-response correctness, confidence, skip state, timing and overall duration.
5. The cloud's profile-scoped history is fetched and cached only for the selected StudyProfile. History now visibly identifies Web versus Raspberry Pi origin.
6. Cloud recovery-to-Pi creates an ordinary profile-owned versioned delivery. Existing Pi sync imports it and presents it in the normal practice library.
7. QR Quick Add remains in the Qt route and existing upload workflow. Normal content sync continues independently.
8. The native Qt Progress screen calculates profile-scoped metrics from completed SQLite attempts and the authorized cloud History cache: attempts, graded accuracy, correct/incorrect/skipped answers, confidence outcomes, practice duration, average answer time and the latest ten accuracy points. A Pi attempt echoed in cloud History is suppressed by UUID when the local copy exists, so it counts once.

## Current HTTP contract alignment

The target uses the cloud/device contract shape documented in the reference repository:
- Profile content catalogue/download/status uses the active device link plus local profile identity.
- Profile catalogue and exact-version download explicitly request `pack_schema=2`; the cloud
  route defaults to schema 1, which would otherwise omit schema-2 MCQ packs and reject their
  downloads. Figure fetches use the authenticated profile route and verify PNG signature/hash.
- Attempt upload uses the device attempt v1 payload and stable attempt UUID.
- Profile History summaries use `GET /api/v1/profile-content/{link_id}/history`; completed review evidence uses `GET /api/v1/profile-content/{link_id}/history/{attempt_uuid}`. Both are scoped to the same active device/profile link and validated against the owning StudyProfile before SQLite cache update.
- Recovery is initiated by the cloud route POST /api/v1/student/profiles/{profile_id}/analytics/recovery/{concept_id}/send-to-pi. The Pi consumes the resulting delivery via profile-content; no parallel recovery endpoint implementation is added.

The cloud pack v1 contract requires an immutable set ID/version, MCQ A–D options, topic, difficulty, marking, nullable relative media reference and valid pack schema. Device pack validation and SQLite persistence retain those fields and solution_ref used by the current content pack.

## Evidence and gaps

Cloud History identifies uploaded device attempts under the intended StudyProfile when the device is paired to that profile and the API accepts the upload. The device summary and detail routes both require the paired device credential and exact active local-profile link. Detail includes only completed attempts; browser drafts remain inaccessible. The device validates and caches review evidence atomically, preserves richer detail across summary-only retry, and skips cloud echo review for an attempt already held locally. A temporary authenticated integration test is configured in cloud CI; no production account was used.

The student web dashboard derives metrics from its profile-authorized History response; `/analytics` is recovery eligibility and Pi delivery state, not aggregate performance. See the corrected `startup-cloud/docs/ANALYTICS_CONTRACT.md`. Device Progress uses the same accuracy denominator from retained History evidence.

The current v1 attempt payload has no explicit custom question subset manifest. Full-pack attempts match the canonical cloud set; custom subset meaning is not fully reconstructable in cloud History. Do not present this as solved by local result storage.

## Pi update and launch

See PHYSICAL_PI_ACCEPTANCE.md for the deploy command, non-destructive update steps, normal Qt launch command, systemd restart commands, and the physical-only checks.

## File inventory

Application and schema: README.md; app/assessment.py; app/content/client.py; app/content/profile_library.py; app/content/validator.py; app/core/engine.py; app/core/models.py; app/data/migrations/README.md; app/data/migrations/0008_question_solution_figures.sql; app/data/repo.py; app/sync/mobile_upload.py; app/ui/controller.py; app/ui_qt/capture_screenshots.py; app/ui_qt/controllers/assessment_controller.py; app/ui_qt/controllers/library_controller.py; app/ui_qt/controllers/quick_add_controller.py; app/ui_qt/qml/Theme.qml; app/ui_qt/qml/Typography.qml; app/ui_qt/qml/components/AppHeader.qml; app/ui_qt/qml/screens/HistoryScreen.qml; app/ui_qt/qml/screens/QuestionScreen.qml; app/ui_qt/qml/screens/QuickAddScreen.qml; app/ui_qt/qml/screens/SettingsScreen.qml; app/ui_qt/qml/screens/TestSetupScreen.qml; app/ui_qt/qml/screens/WifiScreen.qml; schemas/pack.schema.json; pyproject.toml; scripts/kiosk-session.sh.

Cloud contract and setup documentation: docs/CLOUD_CONNECTION.md; docs/DEVICE_CLOUD_CONTRACT.md; docs/DEVICE_MIGRATION_MAP.md; docs/PILOT_ACCEPTANCE.md; docs/PI_SETUP.md; docs/DEVICE_CLOUD_FEATURE_AUDIT.md; docs/DEVICE_CLOUD_INTEGRATION_REPORT.md; docs/DEVICE_QT_UI_VERIFICATION.md; docs/PHYSICAL_PI_ACCEPTANCE.md.

Regression coverage and fixtures: tests/content/test_profile_library.py; tests/content/test_profile_figure.py; tests/fixtures/packs/unsupported_schema_version.json; tests/integration/test_assessment.py; tests/integration/test_custom_subjects.py; tests/integration/test_database.py; tests/integration/test_student_identity.py; tests/test_quick_add.py; tests/test_ui_qt.py; tests/unit/test_pack_validator.py. The Windows-safe backup validation is in tools/restore_local_db.py. The 27 rendered PNGs are under artifacts/pi-ui-verification/.
