# STUDENT WORKFLOW CONSOLIDATION REPORT

Local implementation and verification completed on 29 October 2026. The two repositories remain independent. No root repository was created, no prior phase work was reset, and no production migration/deployment, commit, push or physical Pi change was performed.

## STARTUP-CLOUD

Account-device model: PASS. Additive AccountDeviceLink separates student ownership from DeviceCredential transport authentication; existing profile links are generated automatically after authorization.
One-account rule: PASS. Partial unique indexes enforce one active owner per installation and one primary installation per account. Conflicting account/device connections require explicit disconnect; legacy foreign profile links also block silent ownership transfer.
Three-profile limit: PASS. Server-side account-row serialization and count checks cover both web and device creation, including concurrent requests. Archived profiles deliberately count toward three; no profiles/history are deleted to free slots.
Profile creation: PASS. Profiles and Account & Devices retain creation below three, show the limit at three, and preserve existing accounts over the limit without deleting data.
Device pairing web flow: PASS. Account & Devices accepts Pi-generated codes, previews device name, requires explicit confirmation, approves the existing claim-secret-protected pairing session, and exposes safe expired/used/conflict messages.
Profile synchronization: PASS. Device-account endpoint authenticates the transport credential, resolves active ownership, returns only that account's active profiles and generates internal links automatically.
Redundant link-flow removal: PASS. Normal student profile pages no longer present per-profile pairing. Legacy API compatibility remains available for operator/migration tooling.

Library: PASS. Browse, My Library and My Uploads distinguish content discovery, selections and private ownership. Private uploads are included only for their owner. Institute content remains in its separate authorized assignment flow.
Practice & Downloads: PASS. Selected content exposes browser start/resume, exact profile-device delivery, queued/downloaded/failed-retry state, and current versions. Discovery cards direct selected items to this page.
History: PASS. Completed attempts only, with immutable content/version evidence, web/Pi and personal/institute context, student-created origin, selected profile and result/review. Unfinished drafts remain Continue Practice.

Student upload: PASS. Private question-set creation, owner-only read/edit/archive, append-only versions and retained history.
JSON validation: PASS. Existing strict schema/semantic validator, bounded body/file size, JSON content type, server-generated IDs/storage keys, private object storage. Malformed JSON/schema/correct keys/unsupported formats and foreign account access are rejected.
Manual MCQ builder: PASS. Title/subject/chapter, A/B/C/D single-correct questions, explanation, add/remove/edit, preview and private save. Browser acceptance exercises both manual creation and JSON upload.
PDF/resource handling: DEFERRED as permitted. The current question-pack, ContentVersion, scoring and Pi delivery contracts represent JSON assessments. Reference resources require their own type, authorization/viewer/delivery contract. No automatic PDF conversion is claimed.
Private ownership: PASS. QuestionSet owns a nullable StudentAccount reference; only owner account profiles can discover/select/practice/download private sets. Staff content/catalogue/assignment endpoints and the legacy all-device catalogue exclude private uploads. Shared taxonomy uses neutral private-content labels rather than disclosing private topic metadata.
Pi delivery: PASS. Existing private storage, size/hash/schema checks, atomic import, profile visibility and acknowledgement pipeline is reused.

Sample Set 1: demo-sample-1, five Biology MCQs, Sample / Demo Content, validated and usable.
Sample Set 2: demo-sample-2, five Biology MCQs, Sample / Demo Content, validated and usable; browser JSON-upload preview/save exercised.
Sample Set 3: demo-sample-3, five Biology MCQs, Sample / Demo Content, validated and usable.
Sample Set 4: demo-sample-4, five Biology MCQs, Sample / Demo Content, validated and usable.
Seeding: Explicit idempotent development command `python -m backend.tools.seed_demo_library`; never called at startup. `--remove` archives demo discovery without destroying evidence. Production mode is rejected.

RLS: PASS locally. New ownership table has RLS enabled and PUBLIC/anon/authenticated blocked; backend policies are operation-specific SELECT/INSERT/UPDATE.
Permissions: PASS locally. Restricted NOSUPERUSER/NOBYPASSRLS assessment_backend role performed real insert/select/update operations and the account updated_at operation; DELETE was not granted. Real anon/authenticated SELECT attempts were denied. Temporary isolated PostgreSQL databases were used.
Cross-account isolation: PASS. Foreign profiles/devices/ownership claims/uploads/catalogue/version reads/mutations/private downloads/history are rejected. Institute and legacy transport catalogues cannot publish private student content.
Migration: 20261029_04 follows 20261029_03; additive structures only. Readiness and migration matrix expect the new head. Downgrade refuses to remove retained ownership/content/history.

Backend tests: PASS. Full regression suite: 154 passed. Final focused suite: 14 passed, including six new API cases on BOTH SQLite and isolated PostgreSQL, the real device-client end-to-end flow, and restricted-role RLS/permission checks. The focused run includes eight new parameterized cases added after the full-run collection; counts overlap and should not be added as unique tests.
Frontend tests: PASS, 32 tests.
Browser tests: PASS, all three Playwright suites (student setup/uploads, browser practice/history with real Pi client, institute workflows), rerun against final production build.
Build/lint/typecheck: PASS. Next production build, ESLint, TypeScript and repository-wide Ruff. Both Git whitespace checks pass. A pre-existing documentation-builder import/style lint issue was corrected without changing its behavior.
Warnings: Existing Starlette/httpx TestClient deprecation warning only; no test failures.

Files changed:
- `docs/STUDENT_WORKFLOW_CONSOLIDATION_REPORT.md`
- `backend/alembic/versions/20261029_04_student_workflow.py`
- `backend/app/api/routes/account_devices.py`
- `backend/app/api/routes/uploads.py`
- `backend/tests/test_student_workflow.py`
- `backend/tests/test_workflow_e2e.py`
- `backend/tests/test_workflow_permissions.py`
- `backend/tools/seed_demo_library.py`
- `content/sample_set_1.json`
- `content/sample_set_2.json`
- `content/sample_set_3.json`
- `content/sample_set_4.json`
- `docs/STUDENT_WORKFLOW.md`
- `web/components/account-devices.tsx`
- `web/components/student-home.tsx`
- `web/components/student-uploads.tsx`
- `backend/app/api/routes/admin.py`
- `backend/app/api/routes/health.py`
- `backend/app/api/routes/institutes.py`
- `backend/app/api/routes/library.py`
- `backend/app/api/routes/practice.py`
- `backend/app/api/routes/profile_links.py`
- `backend/app/api/routes/student.py`
- `backend/app/db/models.py`
- `backend/app/main.py`
- `backend/app/services/access.py`
- `backend/app/services/institutes.py`
- `backend/app/services/library.py`
- `backend/app/services/practice.py`
- `backend/tests/test_pilot_readiness.py`
- `docs/PRODUCTION_BACKEND_ACCESS.sql`
- `docs/build_product_handoff.py`
- `web/components/student-history.tsx`
- `web/components/student-institutes.tsx`
- `web/components/student-library.tsx`
- `web/components/student-portal.tsx`
- `web/lib/practice.ts`
- `web/lib/student-api.ts`
- `web/tests/library.test.mjs`
- `web/tests/practice.browser.mjs`
- `web/tests/student.browser.mjs`
- `web/tests/student.test.mjs`

## STARTUP

Startup workflow: PASS. Startup checks lead to Connect Your Device for an unconnected account, or the cached cloud Study Profile picker for returning/offline use. Account refresh runs in the background.
Development option: PASS, absent from normal student startup. Operator functionality requires explicit maintenance mode.
Local profile option: PASS, absent from normal student UI. Legacy records are preserved; maintenance mode exposes Legacy Profiles / Import and legacy linking.
Device connection: PASS. Existing PairingClient/CredentialStore request/poll/claim flow is paired with student web confirmation and automatic account sync. Wi-Fi is accessible from connection setup.
Profile picker: PASS. Active account-owned cached profiles only; no anonymous creation, no normal account switching, no Development/Student choice.
Profile sync: PASS. Persists cloud account/profile IDs, profile names and exam context in the cached account payload; keeps per-profile link/sync state. Cloud renames refresh local display names. Ownership collisions are rejected rather than reassigned.
Create profile: PASS. Creates on the cloud account first, then synchronizes locally, subject to the same server limit. No anonymous local fallback. Offline creation shows a network message and preserves existing cached profiles.
Settings redesign: PASS. Account & Profiles, Wi-Fi, Sync, Content & Downloads, Software Update, Device, Diagnostics, About. Account settings expose cloud creation, Sync Profiles and confirmed Disconnect Device.

Library: Web discovery and account ownership feed the existing profile-scoped Pi catalogue. No new weaker global/private download path was added.
Practice & Downloads: PASS. Profile-visible delivered sets run through existing device assessment/download/version logic.
History: PASS. Completed local attempts remain profile-scoped and upload through the existing immutable/idempotent synchronization protocol.
Student-uploaded content: PASS. Real end-to-end test downloads, validates, imports, practices, resumes and syncs a private upload through existing clients.
Sample content: PASS. A seeded official sample is downloaded, practiced offline, resumed, completed and appears in unified history. All four fixture packs validate through the seed path.

Offline regression: PASS.
Resume regression: PASS, answers/order/version retained through pause/reopen.
Sync regression: PASS, existing retry/idempotency and cross-repository suites remain green.
Profile isolation: PASS, cached account filtering and per-profile content authorization retained; unrelated profiles cannot see selected packs.

Device tests: PASS, 303 tests in the full final device run; a further 29 focused account/UI checks pass after final UI refinements.
Ruff: PASS, repository-wide.
UI previews: Local 800x480 renderer previews generated under artifacts/workflow-ui. Real display/touch/GPIO/network hardware was not accessed.

Files changed:
- `docs/STUDENT_WORKFLOW_CONSOLIDATION_REPORT.md`
- `app/auth/account_device.py`
- `docs/STUDENT_WORKFLOW.md`
- `tests/unit/test_account_device.py`
- `app/data/repo.py`
- `app/ui/controller.py`
- `app/ui/device.py`
- `app/ui/router.py`
- `app/ui/screens/account.py`
- `app/ui/screens/pairing.py`
- `app/ui/screens/profile.py`
- `app/ui/screens/text_entry.py`
- `docs/UI_FLOW.md`
- `tests/content/test_profile_library.py`
- `tests/unit/test_profile_links.py`
- `tests/unit/test_student_ui_flow.py`

## END-TO-END

New account: PASS.
Profile 1: PASS.
Profile 2: PASS.
Profile 3: PASS.
Fourth-profile rejection: PASS, including six concurrent creation requests and archived-count policy.

Pi pairing-code generation: PASS, real PairingClient.
Web pairing-code entry: PASS, actual browser Account & Devices page.
Device connection: PASS, preview/confirm/credential claim and ownership row.
Profile synchronization: PASS, automatic internal links and device account cache.
Restart persistence: PASS, reopened local database/controller goes to cached profile picker without pairing; no network client is required for offline practice.

Official sample browser practice: PASS.
Official sample Pi practice: PASS, download validation, offline practice/resume/result and sync.
Student JSON upload: PASS, validation/preview/private save/browser practice/Pi practice/history.
Student manual MCQ: PASS, actual browser builder/preview/private save using the same upload schema/engine.
Private-content isolation: PASS, foreign account and device/profile access rejected.
History: PASS, completed web/device and student-created attempts, plus institute assignment regressions. Unfinished browser drafts are excluded from completed history.

Legacy-profile preservation: PASS. Legacy data remains unclaimed and outside the ordinary cloud picker; maintenance flow retains access. No automatic historical ownership inference or deletion.
Physical Pi verification: NOT PERFORMED as instructed. Local real-client integration, file-backed offline assessment, renderer and headless UI tests are the acceptance evidence; hardware acceptance remains separate.

## KNOWN DEFERRED ITEMS

- PDF reference-resource upload/viewing/delivery, requiring an explicit non-assessment resource contract.
- Physical Pi display/touch/GPIO/Wi-Fi verification; no physical device changes were authorized.

## FINAL STATUS

All locally authorized implementation and acceptance checks pass. Production rollout remains explicitly unperformed. Archived profiles count toward the limit; retain the documented migration/grant preconditions for deployment.

STUDENT WORKFLOW CONSOLIDATION: PASS

Local test housekeeping: the temporary PostgreSQL cluster was stopped. Automatic approval review blocked recursive deletion of `tmp/workflow-postgres`; no more specific reason was provided. Its files remain local and are excluded through this checkout's Git info/exclude. They are not application or production data.
