# PROFILE AUTH + UNIFIED SYNC REPAIR REPORT

Implementation completed locally; deployment and physical acceptance remain outstanding.
See [the complete flow audit and Pi commands](END_TO_END_SYNC_AUDIT.md).

## ROOT CAUSE

Failing server StudyProfile: `90d6b703-a037-4d7f-ba4b-360e7e4710f6`, inferred
from the canonical local cloud ID. The supplied `bc929292-f3c3-47a7-92a4-00c11091dd4b`
is the route's **ProfileDeviceLink ID**, not a StudyProfile ID.

Failing local StudyProfile: `cloud-90d6b703-a037-4d7f-ba4b-360e7e4710f6`.

Why 403 occurred: the exact active account/profile/device/local-ID/link guard rejected
that relationship. Device-account/heartbeat success and other profiles' 200 responses
rule out a device-wide authentication outage in the supplied physical evidence.

Was profile archived/revoked/stale/mismatched: **stale local authorization is a proven
code defect**. Successful account sync previously hid omitted profiles in the picker
but left their local `link_state='linked'`; content and institute workers continued
iterating those historical rows. The supplied observations are consistent with an
archived/revoked or mismatched relationship. The exact production row's archival
status cannot be verified without its physical cache/authorized production records.

Secondary defects: nonexistent AccountSyncError import could strand a worker Future;
no browser-history down-sync path; installation ACK failures were swallowed; scheduler
backoff relied on HTTP reachability; update no-release 404 emitted warning logs;
Qt's synced flag compared against the wrong enum case.

## PROFILE RECONCILIATION

Authoritative server list: `/api/v1/device-account` returns active owned StudyProfiles
and their canonical cloud-local/link IDs. Reconciliation precedes content work.

Local cache behavior: validate identities first, then retire omitted cloud profiles.
Recognized profile authorization denials retire only that link. A denied link is
quarantined across refreshes so the same relationship is not immediately resurrected.
Changed links or authoritative omission/restoration permit recovery.

Archived/revoked handling: local relationship becomes unlinked; profile/institute
grants are invalidated; unfinished sessions cannot resume unauthorized content;
other profiles continue. Restoration respects the server's active-profile limit.

History preservation: completed native attempts, downloaded read-only result
snapshots, historical ownership records and shared pack bytes are retained.

## SYNC AGGREGATION

Before: one stale profile made content sync false/Failed; institute failures vanished;
upload backlog counts could be zero despite a failed full reconciliation.

After: scoped relationship retirement completes normally; transient content/history
failures persist Partially synced; global device/account authorization remains
Authentication required. Full-cycle diagnostics are separate from upload counts.

Profile-level failures: recognized safe profile-unavailable codes retire one mapping;
unknown denials are not blindly assumed to mean archival. Account 401/403 remains
global. Retried cycles release their OS lock even on exceptions.

Optional stage failures: institute/update errors are separately reported. Update
failures do not prevent content/history work. Heartbeat is separately diagnosed;
its success does not establish successful full synchronization.

## CONTENT

New content web → Pi: authenticated integration verifies selection and delivery,
pending operations/catalogue, hash-validated download, durable install, visibility,
and installed ACK observed through the student's cloud library API.

Removal web → Pi: integration verifies persisted removal, local visibility revoked,
ACK completing the web operation, completed history and shared bytes retained.

Acknowledgements: failed ACKs now surface as incomplete synchronization; retry uses
already verified installed bytes and repeats ACK without redownload.

Qt refresh: the existing SQLite revision polling now emits historyChanged alongside
other model refreshes. No frontend redesign or web source changes.

## HISTORY

Browser → Pi: new authenticated `/api/v1/profile-content/{link_id}/history` returns
paginated owned completed summaries with stable attempt ID, profile ID, source,
title/subject, score/maximum, question count and completion timestamp. The appliance
downloads and validates the complete snapshot before one atomic local setting write.
Browser results are never fabricated as native assessment sessions.

Pi → Browser: real device assessment completion uploads through the existing
idempotent attempts API and appears in the student's unified cloud History.

Deduplication: ten complete cycles preserve one entry per stable attempt ID. Native
Pi attempts returned by the download endpoint are suppressed in the combined display
when that native attempt is already local. Profile isolation is enforced server-side
and validated again before local snapshot persistence.

Limits: current Qt History displays the newest 20 combined summaries. Downloads
cap a complete snapshot at 10,000 entries and retain the previous snapshot on
incomplete/oversized/invalid responses. Existing Qt review behavior is unchanged.

## SOFTWARE UPDATE 404

Root cause: the route exists; the backend returns 404 when no release/catalogue is
published. This is distinct from the profile authorization failure.

New behavior: None / No update available, no warning from UpdateClient; content and
history reconciliation continue. No-release behavior is covered independently.

## DIAGNOSTICS

New status semantics: last full-cycle attempt/result and last successful full sync;
profile availability/retirement/skips; content/history counts; attempt uploads;
heartbeat and optional checks. Available through `tools.diagnose --json`, human CLI
output and the existing Qt Diagnostics screen. Pairing alone reports unverified
authentication rather than OK. Upload logs explicitly say pending_attempts_selected.

Production health was checked during investigation: `/health` 200; `/ready` 200,
database OK, migration current. The local workstation credential is an unowned
device and must not be confused with the physical Pi credential.

## TESTS

| Requested coverage | Result |
|---|---|
| Stale profile 403 | PASS: relationship retired, no repeat requests after next cycle |
| Archived profile | PASS: three active profiles plus old fourth cache row reconciled; archive/restore |
| Valid profiles continue | PASS: another profile installs while one link is denied |
| New content | PASS: actual cloud routes + device SQLite + installed ACK |
| Removal | PASS: local visibility revoked, server operation completed |
| Browser history down-sync | PASS: actual browser completion retrieved into read-only cache |
| Pi history up-sync | PASS: actual device completion appears in cloud History |
| Deduplication/profile isolation | PASS: ten cycles; no cross-profile history/content |
| 404 update check | PASS: benign return, no warning, content/history continue |
| Manual sync | PASS: same core runs with automatic sync disabled |
| Auto-sync | PASS: scheduler installs content and downloads browser history |
| 401/403/503 and recovery | PASS: global/scoped distinction, worker Future completes, lock reusable |
| History timeout/invalid snapshot | PASS: prior complete cache retained; retry succeeds |
| Qt refresh | PASS: separate SQLite commit updates rendered History model without restart |
| Full device regression | 380 passed |
| Backend regression | 145 passed, 18 skipped |
| Device/cloud integration | 5 passed separately with DEVICE_REPO_PATH enabled |
| Top-level cloud regression | 24 passed, 1 skipped |
| Ruff | PASS: device app/tools/tests and changed cloud files |

Skipped backend coverage includes unavailable optional PostgreSQL/role-based tests
and device-integration modules in the default run; device integration was enabled
and run separately. Production backend-role/RLS row visibility and physical hardware
were not verified. TestClient emitted one upstream deprecation warning. Native Qt
render tests load an installed Windows font for the offscreen rendering environment.

## FILES CHANGED

startup:

- app/auth/account_device.py
- app/connectivity.py
- app/content/client.py
- app/content/institute_work.py
- app/content/profile_library.py
- app/content/sync.py
- app/data/repo.py
- app/data/scheduler_state.py
- app/diagnostics.py
- app/sync/history.py
- app/sync/scheduler.py
- app/sync/service.py
- app/sync/worker.py
- app/ui/controller.py
- app/ui/device.py
- app/ui_qt/controllers/app_controller.py
- app/ui_qt/controllers/assessment_controller.py
- app/ui_qt/controllers/settings_controller.py
- app/update/client.py
- tools/diagnose.py
- tests/content/test_profile_library.py
- tests/integration/test_cloud_readiness.py
- tests/test_ui_qt.py
- tests/unit/test_auto_sync.py
- tests/unit/test_sync_history.py
- tests/update/test_updates.py
- docs/END_TO_END_SYNC_AUDIT.md
- docs/PROFILE_AUTH_UNIFIED_SYNC_REPAIR_REPORT.md

startup-cloud:

- backend/app/api/routes/library.py
- backend/tests/test_unified_device_sync.py

## DATABASE MIGRATION: NO

No schema, RLS, grant or credential changes. No production migration was run.
The existing local settings store holds validated read-only result snapshots.

## PHYSICAL PI VALIDATION: NOT YET VERIFIED

Deploy cloud first, then device. The new history route must be deployed before the
Pi can download browser history. Until then that stage correctly reports partial
sync. Run the exact diagnostic/manual/log commands in the linked audit, then verify
web add/remove, auto/manual behavior and both history directions on the running Pi.
Do not reset its database or re-pair to apply this repair.

## FINAL STATUS

Local repair and integration validation completed. Production deployment, exact
classification of the cited production relationship, and the user's physical-Pi
acceptance sequence remain unverified. A physical end-to-end PASS is not claimed.

PROFILE AUTH + UNIFIED SYNC REPAIR: FAIL
