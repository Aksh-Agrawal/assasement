# End-to-end synchronization audit

Investigation date: 2026-10-30. No production migrations or credential changes run.

## Evidence and scope

Production `/health` and `/ready` returned HTTP 200; readiness reports database OK,
migration current. The supplied physical-Pi observations report account and heartbeat
200, valid profiles 200, one cached profile's content and institute requests 403.
The workspace log has older successful uploads/heartbeat but no current physical
failure. The workstation credential is a different, unowned device: account 403,
global catalogue 200. It must not be used to diagnose the physical Pi's ownership.

**Important identity distinction:** `bc929292-f3c3-47a7-92a4-00c11091dd4b`
in `/profile-content/{link_id}` and `/institute-content/{link_id}` is a
ProfileDeviceLink ID, not a StudyProfile ID. The local cloud profile ID implies
StudyProfile `90d6b703-a037-4d7f-ba4b-360e7e4710f6`. Without the physical
cache/server rows we cannot distinguish archival, revocation, or mapping mismatch.
All are rejected by the same ownership guard. No authorization bypass is appropriate.

## Flow map (before repair)

All device HTTP requests use TLS-verified Bearer DeviceCredential. Backend
`authenticate_device` verifies active credential/device and secret hash. Student
browser routes use account sessions and ownership checks. SQLAlchemy backend-role
queries, not browser direct database queries, serve these routes.

| FLOW | CLIENT FUNCTION | API ENDPOINT | AUTH MECHANISM | DATABASE TABLE | PROFILE/DEVICE FILTER | ACKNOWLEDGEMENT | LOCAL WRITE | UI REFRESH | CURRENT FAILURE |
|---|---|---|---|---|---|---|---|---|---|
| device account sync | auth.account_device.sync_account | GET /api/v1/device-account | device bearer + active account-device owner | account_device_links, student_accounts | authenticated database device ID + active account | HTTP 200 complete snapshot | student_account_context, settings.account_profiles | profile picker and Qt tick | omitted cached profiles stay linked |
| profiles | account_device._sync_account / server sync_links | same endpoint | same | study_profiles, profile_device_links | active StudyProfile/account; cloud-{profile UUID} local mapping | link IDs returned | profiles, profile_link_context | refresh_catalog | UI hides omitted profile but sync still iterates it |
| catalogue/library | profile_library.refresh_library | GET /api/v1/profile-content/{link}/catalog | device bearer + require_device_profile_link | library_selections, question_packs, profile_content_deliveries | link/device/local ID/account/active profile | device_seen | profile_library authoritative eligible grants | Library | stale link repeatedly 403 |
| practice selections | browser add/send | POST /api/v1/student/profiles/{id}/library, /{selection}/deliveries | student session | library_selections, profile_content_deliveries | owned profile + active recipient link | delivery persisted | grant cache after device fetch | Practice/library | depends on valid profile reconciliation |
| device deliveries | sync_profile_deliveries / fetch_changes | GET /api/v1/profile-content/{link}/operations | scoped device | profile_content_deliveries, library_selections | link, account, profile; snapshot token and current pack | receipt/downloading/downloaded/installed | verified pack + profile grant | data_version Qt tick | one stale 403 contributes global failure; ACK errors swallowed |
| removals | sync_profile_deliveries | POST /profile-content/{link}/operations/{id}/status | scoped device | profile_content_deliveries revision/operation | exact link + revision | removed only after local grant reconciliation | eligible=0; stale drafts abandoned; shared bytes retained | data_version Qt tick | stale profile must retire via account snapshot |
| question-pack downloads | download_for_profile -> _install_one | GET /profile-content/{link}/packs/{set}/{version} | scoped device + current eligible delivery | question_packs, content_versions | account/private-content eligibility, exact version/hash | installed after durable import | question_sets/questions, SHA256 validation | Library/Practice | no new download defect established |
| browser-completed history | browser practice.submit -> history_view | student history only | student session only | attempts, practice_sessions, attempt_responses | owned StudyProfile | browser submit idempotency | none on Pi | web History only | device endpoint/client/cache missing |
| Pi attempts upload | SyncWorker.run_sync_once | PUT /api/v1/attempts/{attempt UUID} | device bearer + attempt ownership | attempts, attempt_responses | authenticated device and captured profile link | idempotency key; local synced after response | attempts sync_status | local History/web History | selected=0 means upload queue, not content |
| heartbeat | service._run_cycle -> HeartbeatClient.send | POST /api/v1/devices/heartbeat | device bearer | devices | authenticated device | HTTP 200 | last_heartbeat_state | settings/status | succeeds on supplied physical evidence; not proof of full sync |
| institute content | sync_institute_work | GET /api/v1/institute-content/{link}/catalog | same profile guard plus institute membership | institute assignments/memberships | active owned profile/link/device | read catalogue | institute_work grants | Qt Library | retries same stale profile; exceptions silently ignored |
| software update | UpdateClient.check_for_update | GET /api/v1/device-updates/latest | device bearer | software_releases / fallback catalogue files | current published release | 404 when no release | optional check state | settings | benign no-release 404 logged as warning |

## Invocation, concurrency, and stage policy

Settings QML -> SettingsController -> DeviceConsole.start('sync') -> background
thread -> run_cycle(refresh=True). AutoSyncScheduler uses the same run_cycle.
Scheduler starts due immediately, checks enablement, network-return wakeup and
bounded backoff. OS file locks serialize scheduler/cycle and release via context
manager on exceptions. Existing defect: worker exception handling imports a
nonexistent AccountSyncError before completing its Future, leaving the UI busy.

Account reconciliation is critical before profile content. Missing account cache
previously skipped reconciliation altogether. A successful authoritative snapshot
must retire omitted account-derived links, invalidate grants/selections, preserve
completed attempts and bytes, and permit restoration. Legacy explicitly linked
profiles remain independently guarded. A scoped 403 retires that mapping; a 401
remains device authentication failure. Account endpoint 401/403 is global.
Transient profile failures retain cached work and report partial sync. History and
delivery failures must not be reported as Up to date. Institute/update checks are
optional and separately diagnosed. Heartbeat success is reachability, not sync success.

## Database/security verification limits

Reviewed profile ownership predicates and migration RLS/grant definitions. Backend
authorization requires active account/profile/link and exact authenticated device,
local profile and server profile identities. Existing migrations enable RLS and
grant backend-specific access. No production SQL-role session or physical-device
credential was provided, so live role-level row visibility is not verified. Tests
must exercise authenticated real routes; no broad grants or policy changes.

## Acceptance boundary

Local integration can prove cloud routes, device SQLite, reconciliation and ACKs
together. It cannot certify physical hardware deployment, network, or running Qt
state. Final physical acceptance requires active-profile add/remove, both history
directions, and absence of repeated stale-link requests without restarting/resetting.

## Implemented reconciliation

- Account payload identities/names are validated before retiring omitted cloud cache
  rows. Retirement atomically unlinks the local profile, revokes library/institute
  grants, repairs unfinished sessions, and retains completed attempts and shared bytes.
- A recognized scoped denial (`LINK_OWNERSHIP_MISMATCH`, `LINK_REVOKED`, or
  `profile_not_available`) retires only that relationship. Its link ID is quarantined
  so a repeated account refresh does not resurrect the same denied mapping. An
  authoritative omission/restoration or changed server link permits recovery.
- Device-account 401/403 and device-authentication errors remain global failures.
  Unknown 403s are not silently reinterpreted as archival. No ownership/RLS checks
  were removed. Active profiles continue independently after scoped retirement.
- `GET /api/v1/profile-content/{link_id}/history` uses the existing exact ownership
  guard and returns paginated completed summaries, including source and question
  count. `sync_history` fetches/validates the complete snapshot before writing a
  single `settings.completed_results:{local profile}` JSON value. No native attempt
  rows are synthesized. Stable attempt IDs deduplicate both repeated downloads and
  results already present as native attempts. The current appliance History view
  displays the most recent 20 combined summaries; review behavior is unchanged.
- The history downloader caps snapshots at 10,000 entries. An incomplete, invalid,
  unauthorized or oversized snapshot never replaces previously cached history.
- History/content failures persist `Partially synced`; optional institute/update
  failures have separate diagnostics. Lost installation ACKs retain installed bytes
  but propagate failure until the next cycle re-ACKs without downloading again.
- Scheduler state reads now include internet and reconciliation status. Online
  contact cannot clear a partial-sync backoff. Manual/automatic work still shares
  the same OS-locked core. Exception paths always complete the console Future.
- No-release update 404 returns None and emits no warning. Optional update failure
  does not prevent content/history work. Upload logs now explicitly name the pending
  attempt queue; a zero queue never suppresses content or history stages.
- Qt polls SQLite data revisions and emits historyChanged after worker commits.
  The synced indicator uses the actual lowercase enum value. Existing diagnostics
  expose full-cycle result/stages/profile counts separately from upload backlog.

## Physical validation commands

Deploy the cloud change before the device change so the new authenticated history
route is available. No production migration, re-pairing, or database reset is needed.
Until cloud deployment, the new device history stage will correctly report partial
sync on a missing route while content reconciliation continues.

```bash
cd ~/assasement
source .venv/bin/activate
export ASSESS_API_URL="https://startup-cloud.onrender.com"
python -m tools.diagnose
python -m tools.diagnose --network
curl --fail --silent --show-error "$ASSESS_API_URL/health"
curl --fail --silent --show-error "$ASSESS_API_URL/ready"

# One complete manual reconciliation (tools.sync_once uploads attempts only).
python - <<'PY'
from app.config import AppConfig
from app.sync.service import run_cycle
print(run_cycle(AppConfig(), refresh=True))
PY
python -m tools.diagnose --json

tail -n 250 var/log/assessment-device.log
grep -E 'profile relationship retired|reconciliation failed|pending_attempts_selected|profile-content|institute-content|device-account|heartbeat|/history' var/log/assessment-device.log | tail -n 150
journalctl -u assessdev-sync.service --since '20 minutes ago' --no-pager
```

If the log directory/database differs, use the configured ASSESS_LOG_DIR and
ASSESS_SQLITE_PATH. Do not paste credential files or authorization headers.
Use Settings -> Sync Now as well to validate the actual Qt invocation. With auto
sync on, add/remove content through the website for an active profile and wait for
delivery ACKs and immediate Qt model refresh. Complete one browser and one Pi
assessment, then verify both History views after sync. Confirm the retired link
does not appear in repeated content/institute requests. Restore an archived profile
within the existing three-active-profile limit and verify it becomes available.
