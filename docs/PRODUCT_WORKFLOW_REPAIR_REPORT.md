# FULL PRODUCT WORKFLOW AUDIT + REPAIR REPORT

30 October 2026. Local software acceptance; physical and deployed acceptance are separate.
No production migration/deployment, commit, push, destructive cleanup or parent Git repository.
Cloud remains on `master`; Pi remains on `main`.

## AUDIT

Total audit findings: **20**. Blockers: **2**. High: **13**. Medium: **5**. Low: **0**.
Issues fixed through implementation: **16**. Existing workflows verified: **3**.
Issues deferred: **1**, physical Pi acceptance, because no physical device is available.

The complete eleven-column issue matrix, each root cause, fix, test and resolution is in
[PRODUCT_WORKFLOW_AUDIT.md](PRODUCT_WORKFLOW_AUDIT.md). PW01–PW14, PW18 and PW19 are repaired;
PW15–PW17 passed existing-workflow/security regressions; PW20 remains physical acceptance.
No issue is treated as resolved merely because a route or button exists.

## CANONICAL MODEL

Account source of truth: cloud StudentAccount; web uses its own authenticated human session.
StudyProfile source of truth: cloud, at most three active profiles, account-row serialization.
Device relationship: cloud AccountDeviceLink plus valid transport credential; internal profile
links are generated only under that authorization. Browser passwords are never copied to Pi.
Offline cached state: last synchronized account/profile metadata and installed content; cached
identity does not prove a live connection. Confirmed rejection clears routing, not local evidence.
Sync state model: idle / syncing / synced / pending / failed / auth_required; an empty queue is
labelled No pending attempts rather than falsely asserting successful cloud synchronization.
Delivery state model: selected → queued → device_seen → downloading → downloaded → installed;
failed/retry and removed are explicit. See [PRODUCT_STATE_CONTRACT.md](PRODUCT_STATE_CONTRACT.md)
for full states, source-of-truth table, endpoints, freshness rules and compatibility.

## STARTUP-CLOUD

Account UX: signed-in name/email and selected Study Profile banner; context follows scoped routes
and remembered owned-profile selection; changing the Home picker updates shared navigation immediately. Direct Library/History/Institute defaults reconcile.
Profiles: create and rename retained; archive preserves evidence; restore added; active count
shown from Profiles and Account & Devices. Archived profiles free slots. A fourth active profile
is rejected on server; restore at capacity is rejected. No permanent delete route is introduced.

Account & Devices: Account / Study Profiles / Connected Raspberry Pi / Sync Status / Device Actions.
Pairing: Pi code, device-name preview, explicit connection, credential claim; reconnect is available
when ownership exists but transport credentials are revoked/missing. A still-unclaimed approval
is presented as waiting for the Pi, not a completed connection.
Device reconciliation: active account ownership and credential state are distinct. Archived
profile links are revoked on reconciliation; restore creates a fresh link without rewriting history.
Heartbeat: existing safe software, installed-pack, pending-attempt, last-seen/heartbeat and health
fields are exposed to the student account owner; secrets are not included.
Online/offline state: 180-second observation threshold; refresh every 15 seconds while visible;
refresh failures explicitly warn that previous status may be stale. This is not Wi-Fi telemetry.
Sync state: pending attempt/heartbeat/health summary and refresh; per-pack downloads are in Practice.

Library: discovery, Sample Content, selections and My Uploads. Demo sets: four existing labelled
five-MCQ Biology packs, validated using the supported schema. Explicit idempotent development seed:
`python -m backend.tools.seed_demo_library`; remove with `--remove` (archive, retain evidence).
No startup reseeding. Production mode remains refused. Tests exercise all four packs, version-4
update behavior, selection isolation and removal. My Uploads/manual MCQ: JSON upload, question
add/remove/edit, A/B/C/D choice, explanation, preview and private save exercised in the browser;
owner isolation, immutable versions, private practice/delivery and history exercised by API/Pi tests.

Practice & Downloads: selected packs, unfinished browser practice, browser start/continue,
Pi progress, update availability and failed retry. Raw local-profile IDs are removed from cards.
History: completed web/Pi and personal/institute evidence only; unfinished work stays in Practice.

Send to Pi: Sending is shown only for the actual Send action. Queued is cloud intent only.
Device received: explicit Pi acknowledgement after catalogue parsing. Downloading: before fetching.
Downloaded: exact validated bytes, awaiting import. Installed: successful atomic import or matching
installed bytes, shown as Ready on Pi. Failure/retry: failed is distinct; retry requeues; repeated
Send preserves successful progress. Late/out-of-order acknowledgements cannot regress installation;
superseded-version acknowledgements return 409. Row locks serialize progress updates. Web polls
every five seconds while visible, and retains a manual refresh. Restart/lost-ack retries reuse bytes.

Accessibility: visible focus and skip-to-content; form labels; 48px button/control minimums;
textarea sizing; mobile wrapping; loading/success/error messages; profile lifecycle confirmations.
Browser checks assert labelled forms/buttons, button height and mobile overflow; screenshots inspected.
Security: cross-account profiles/restoration/devices/uploads/delivery/practice/history and institute
scope regressions pass. No client-supplied ID bypass or browser database credentials are introduced.

Backend tests: full isolated run **169 passed**; additional product tests **2 passed**.
PostgreSQL/RLS tests: included in full run, including migration matrix, metadata drift, backup/restore,
and restricted runtime role. A focused final delivery/RLS/Pi-client recheck is recorded below.
Frontend tests: **32 passed**. Browser tests: student workflow, practice/history and institute/teacher
flows passed against temporary local servers/databases. Build/lint/typecheck: all passed.
One existing Starlette TestClient deprecation warning remains; it does not fail a check.

Migration: `20261030_01` expands the existing delivery constraint, following `20261029_04`.
Existing PostgreSQL RLS/policies remain; missing runtime SELECT/INSERT/UPDATE grants and
operation-specific delivery policies are installed for an existing restricted role. No new
table or DELETE grant; PUBLIC/anon/authenticated remain blocked. Downgrade refuses new progress
states rather than discarding them. Readiness head updated. Deploy cloud support before updated Pi.
No production migration was applied. Existing pending migration repairs were retained; the user's
untracked migration-repair test only has its expected head advanced for compatibility.

## STARTUP

First-run flow: Connect Raspberry Pi → account verification/profile synchronization → profile picker.
Returning flow: cached picker remains available offline while background verification runs.
Account state: Connected requires fresh successful verification in this UI process; cache alone
shows verification required. Offline shows last verified timestamp; 401/403 records reconnection
required and preserves SQLite/profiles/attempts. Create errors never create anonymous profiles.
Cloud status: fresh API observations are distinct from credential/account state.
Online/offline status: Wi-Fi association and independent NetworkManager connectivity observation
are separate; unavailable measurements show Unknown/unverified. Physical measurement remains pending.
Sync status: persistent selected-profile/pending/attention footer; dedicated last-success screen.
Sync Now verifies/reconciles before the existing bounded background attempt/content/heartbeat work.
A completed background account refresh never reroutes an active assessment to the profile picker.

StudyProfile cache: cloud list is authoritative; add/rename reflected, archive hidden, historical
records retained. No normal local-profile or cloud-profile creation terminology; technical device
IDs/storage internals removed from normal account/device screens. Legacy maintenance remains separate.
Library / Practice & Downloads / History: existing profile eligibility and completed-evidence flows
retained; downloaded work and exact-version unfinished attempts remain independent of network.
Delivery receive: explicit device_seen. Download acknowledgement: downloading then downloaded after
validation. Installed acknowledgement: only after atomic import; lost response is retried after
restart using matching installed content. Cloud progress persists and distinguishes all stages.

Accessibility: 48–64px normal controls, existing long-question/full-text handling, explicit status,
Back actions and visible focus. The preview generator now uses an owned account fixture, rather
than an anonymous profile that normal navigation correctly hides.
800×480: 30 actual logical previews generated. 800×600: matching scaled previews generated and
coordinate mapping tested; account previews visually inspected. Physical display/touch not certified.
Offline assessment / Resume / Sync: real repository/engine restart, pinned version/order,
offline work, idempotent uploads and unified history passed.
Device tests: **306 passed**. Final UI/layout subset: **31 passed**, including background account-refresh assessment continuity. Ruff: passed.

## END-TO-END

Register/login/logout/relogin: browser PASS, account/profile state persists.
Create three/fourth rejected/rename/archive/restore/replacement: browser + server PASS.
Connect Pi/account ownership/profile sync: browser + independent real Pi client PASS.
Offline cached profiles/archived hiding/record retention/revocation: headless/API PASS.
Four demos: discovery/seed/idempotency/remove/version update PASS.
Browser practice/autosave/confidence/review/refresh/resume/failure retry: browser PASS.
Send/queued/received/downloading/downloaded/installed: API/client/browser PASS; browser observes
progress by polling. No server-intent record is presented as installed.
Offline Pi practice/restart-resume/result upload/history: independent real-client PASS.
Student JSON/manual/private isolation: browser/API/client PASS. Cross-account/cross-institute: PASS.

## DEFERRED

PW20: physical Pi boot/reboot/display/touch/GPIO, real NetworkManager privileges and network
transitions, hardware performance and hosted connectivity. Exact reason: no physical Pi was
available. The requested later hardware acceptance must repeat the documented boot → account →
profiles → delivery → offline practice → reboot/resume → result sync flow. No physical PASS claimed.

Production rollout is not deferred repair work: migrations/deployment were explicitly excluded
from automatic execution. The operator must apply the reviewed migration and explicitly seed demo
content in a permitted development environment before expecting demo cards in that environment.

## FINAL STATUS

Local software workflow consolidation passes the recorded checks. This is not a physical-device,
hosted-environment or full WCAG certification. See the audit matrix for each resolution.

Final focused checks: 15 delivery/library/profile/sample/real-client cases passed; the
new stricter RLS test exposed a missing fresh-install runtime policy. After repair, its
actual FK-backed INSERT/SELECT and all progress UPDATEs passed as assessment_backend;
DELETE was denied and anon/authenticated reads were denied. The repaired PostgreSQL test
passed; a fresh SQLite + RLS smoke run also passed (2 tests). Ruff passed after final edits.
The full 169-test run predates only these final focused additions/repairs; it is not
misrepresented as a second full run. Current documentation was checked against
[Supabase RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security).

FULL PRODUCT WORKFLOW CONSOLIDATION: PASS (local software acceptance; physical PW20 pending)

## Local evidence

- Full isolated cloud log: `backend/runtime/product-workflow-pytest.log` (169 passed).
- Final student/browser screenshots: `C:/Users/aksha/AppData/Local/Temp/student-identity-17GmZa/`.
- Practice/history browser screenshots: `C:/Users/aksha/AppData/Local/Temp/practice-history-dwnWxa/`.
- Teacher/institute browser screenshots: `C:/Users/aksha/AppData/Local/Temp/institute-work-3grQOY/`.
- Pi previews: `E:/mainfolder/startup/artifacts/ui-redesign/` (30 logical plus 30 scaled images).
- Final student browser rerun passed Home picker/shared-navigation synchronization, all receipt
  stages via polling, lifecycle/upload/privacy checks, mobile overflow and labelled controls.
- Temporary local PostgreSQL was stopped; diagnostic-only py-spy was removed from the venv.

## Files changed

The following lists are generated at handoff. Pre-existing MIGRATION_RUNBOOK.md/PILOT_ACCEPTANCE.md
changes are preserved and excluded from the implementation list.

### STARTUP-CLOUD

- `backend/alembic/versions/20261030_01_delivery_progress.py`
- `backend/app/api/routes/account_devices.py`
- `backend/app/api/routes/health.py`
- `backend/app/api/routes/library.py`
- `backend/app/api/routes/student.py`
- `backend/app/db/models.py`
- `backend/app/services/library.py`
- `backend/tests/test_library.py`
- `backend/tests/test_migration_repair.py`
- `backend/tests/test_pilot_readiness.py`
- `backend/tests/test_product_reconciliation.py`
- `backend/tests/test_product_samples.py`
- `backend/tests/test_student_workflow.py`
- `backend/tests/test_workflow_e2e.py`
- `backend/tests/test_workflow_permissions.py`
- `docs/DEVICE_CLOUD_CONTRACT.md`
- `docs/PRODUCT_STATE_CONTRACT.md`
- `docs/PRODUCT_WORKFLOW_AUDIT.md`
- `docs/PRODUCT_WORKFLOW_REPAIR_REPORT.md`
- `docs/STUDENT_IDENTITY_CONTRACT.md`
- `docs/STUDENT_LIBRARY_CONTRACT.md`
- `docs/STUDENT_WORKFLOW.md`
- `web/app/globals.css`
- `web/components/account-devices.tsx`
- `web/components/student-history.tsx`
- `web/components/student-home.tsx`
- `web/components/student-institutes.tsx`
- `web/components/student-library.tsx`
- `web/components/student-portal.tsx`
- `web/tests/institutes.test.mjs`
- `web/tests/student.browser.mjs`
- `web/tests/student.test.mjs`

### STARTUP

- `app/auth/account_device.py`
- `app/auth/product_state.py`
- `app/content/profile_library.py`
- `app/content/sync.py`
- `app/sync/service.py`
- `app/system/wifi.py`
- `app/ui/components.py`
- `app/ui/controller.py`
- `app/ui/device.py`
- `app/ui/screens/account.py`
- `app/ui/screens/device_info.py`
- `app/ui/screens/pairing.py`
- `app/ui/screens/sync.py`
- `app/ui/screens/text_entry.py`
- `app/ui/screens/wifi.py`
- `docs/DEVICE_CLOUD_CONTRACT.md`
- `docs/PRODUCT_STATE_CONTRACT.md`
- `docs/PRODUCT_WORKFLOW_AUDIT.md`
- `docs/PRODUCT_WORKFLOW_REPAIR_REPORT.md`
- `docs/STUDENT_IDENTITY_CONTRACT.md`
- `docs/STUDENT_LIBRARY_CONTRACT.md`
- `docs/STUDENT_WORKFLOW.md`
- `tests/content/test_profile_library.py`
- `tests/unit/test_account_device.py`
- `tests/unit/test_student_ui_flow.py`
- `tests/unit/test_ui_layout.py`
- `tools/ui_smoke.py`
