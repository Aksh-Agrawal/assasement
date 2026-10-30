# Product workflow audit and repair

Audit started 2026-10-30. Cloud branch `master`; device branch `main`.
Existing cloud modifications to MIGRATION_RUNBOOK.md, PILOT_ACCEPTANCE.md and
untracked test_migration_repair.py are preserved. Device began clean. No parent
repository, production migration, deployment or physical-device change is authorized.

## Evidence and scope

Inspected both README/documentation inventories, identity/library/practice/history,
institute/analytics/workflow/migration/device contracts and current implementations:
cloud student/account_devices/library/heartbeat routes, library service, delivery
model and migration, student portal/library/account components; device account cache,
controller, account/sync/Wi-Fi/home chrome, content client/import/sync and workflow tests.
Existing reports are historical evidence, not acceptance of this revision.

Statuses distinguish confirmed defects, existing implementation awaiting regression,
and acceptance gaps. A route's existence never constitutes an end-to-end PASS.

| ID | Area | Current behavior | Expected behavior | Root cause | Cloud impact | Pi impact | Severity | Fix | Test | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PW01 | Profile limit | Archived profiles consume slots | At most 3 active profiles; replacement after archive | Count query includes all states | Account becomes permanently full | Create disabled | HIGH | Count active profiles under account lock in every create/restore path | Fourth rejected; archive/replacement; restore conflict; concurrency | Fixed; active-limit, archive/replacement, restore and concurrency tests pass |
| PW02 | Restore | No restore route/control | Restore archived profile when capacity allows | Lifecycle incomplete | No recovery control | Profile cannot return | MEDIUM | Owned, serialized restore; preserve original identity/history | Owner isolation and full-capacity rejection | Fixed; restore identity/capacity/foreign-owner tests pass |
| PW03 | Account verification | Cached account + credential renders Connected | Explicit verifying/offline-last-verified/revoked states | UI equates cache with authority | Conflicting product state | False Connected | HIGH | Persist verification outcome; derive safe account label from outcome/freshness | Offline/restart/revocation | Fixed; fresh verification required; restart/offline/expiry tests pass |
| PW04 | Revocation | Clear routing context, no durable reason | Explain reconnection; preserve assessments | Rejection reason not persisted | Revocation valid server-side | Generic first-run screen | HIGH | Persist revoked state on 401/403 across create/verify | Cached data retained; no active routing after rejection | Fixed; rejection clears routing and preserves data; web detects revoked credential |
| PW05 | Profile reconciliation | Active list filtered in picker; stale active links remain server-side | Archived profiles hidden and inactive links revoked | sync_links only adds | Stale relationship records | Background loops may use archived links | HIGH | Revoke archived-profile links, retain historical evidence | Rename/archive/restore reconciliation | Fixed; rename/archive/restore and retained-cache regression passes |
| PW06 | Delivery lifecycle | Only queued/downloaded/failed | Received, downloading, downloaded, installed distinguishable | Enum/API/client omit stages | No receipt evidence | Installation collapsed into downloaded | BLOCKER | Add compatible stages and guarded version-specific acknowledgements | Real-client lifecycle and isolation | Fixed; explicit receipt/download/install stages; real-client integration and browser polling pass |
| PW07 | Retry/restart | Repeated Send always resets queued | Installed evidence persists for same bytes | Unconditional send update | False queued after repeated send | Repeated work | HIGH | Preserve terminal progress; retry failed/new version explicitly | Re-send and restart persistence | Fixed; repeated Send retains installed status; lost-ack restart test passes |
| PW08 | Delivery ordering | Any ack overwrites state | Late receipt cannot overwrite installed | No transition/version guard | Progress can regress | Retry ambiguity | HIGH | Lock delivery, bind progress to exact latest pack, monotonic progress | Out-of-order and stale-version requests | Fixed; version guard, row locks and monotonic transitions; stale-version tests pass |
| PW09 | Delivery observation | Manual refresh only | Bounded polling while viewing status | No polling timer | Receipt not visible promptly | None | MEDIUM | Poll active page; offline queue explanation | Browser queue/receipt/install | Fixed; visible-page polling and offline wording; browser stages pass without manual refresh |
| PW10 | Account & Devices | Counts all profiles; no sync summary; static device state | Active count, signed-in identity, heartbeat/sync state | Incomplete presentation | Confusing account page | None | MEDIUM | Active/archived sections, safe heartbeat summary, refresh | Browser profile lifecycle/device status | Fixed; active count, identity, reconnect state, heartbeat/pending summary and refresh |
| PW11 | Pi status | One network label; account screen omits verification time | Separate cloud/account/sync information | Insufficient state presentation | None | Misleading status | HIGH | Shared pure status derivation; account screen and persistent chrome | Headless states + render inspection | Fixed; separate measured connectivity/account/sync labels; technical IDs removed from normal screens |
| PW12 | Sync Now | Account refresh separate from attempt/content cycle | Verify account then reconcile profiles/content/attempts/heartbeat | Separate service entry points | Inconsistent profile freshness | Needs multiple actions | HIGH | Compose existing bounded worker operations | Revocation and offline safety; no UI blocking | Fixed; account reconciliation precedes bounded background sync; completed background account refresh does not reroute an active assessment |
| PW13 | Selected profile | Route scoping exists; no global identity/profile banner | Signed-in and selected-profile context clear | Shell only shows generic header | Context unclear on several pages | Existing selected profile | MEDIUM | Shared shell context; preserve route scoping | Switch library/practice/history/institute/analytics | Fixed; identity/profile banner and remembered owned-profile default; institute switch updates route |
| PW14 | Demo discovery | Four 5-MCQ fixtures and explicit seed exist; no Sample Content filter | Easy demo discovery, idempotent seed/remove | Browse tab generic | New user may see empty library until seed | Cannot test delivery until seeded | MEDIUM | Sample Content entry; verify explicit seed/remove; never auto-seed | Seed twice, browse and remove | Fixed; Sample Content entry; all four fixtures, idempotency/removal and version-4 test pass |
| PW15 | Uploads/manual builder | Existing private uploads + builder | JSON/build/preview/practice/send usable and isolated | Acceptance needed | Private-content security boundary | Same pack pipeline | HIGH | Regress current implementation; repair failures found | API isolation and browser builder | Verified existing behavior; private API isolation and real browser JSON/manual builder pass |
| PW16 | History/offline/resume | Existing pinned drafts/completed evidence and offline engine | Preserve scope/version/history through changes | Acceptance needed | Evidence retention | Offline independence | HIGH | Regress existing engine and cross-repo flow | Complete web/Pi, offline restart/resume, upload retry | Verified existing behavior; real-client offline/restart/resume/history and browser retry tests pass |
| PW17 | Authorization | Existing owned-profile/link/upload/institute checks | Cross-account/institute IDs denied | Acceptance needed | Security boundary | Device isolation | HIGH | Run existing and new security regressions | Foreign IDs and restricted role PostgreSQL | Verified existing behavior; PostgreSQL/SQLite isolation, institute and restricted-role tests pass |
| PW18 | Accessibility | Existing focus/styles/touch bounds; incomplete current visual proof | HIGH/MEDIUM defects resolved at web/mobile and 800x480/600 | Acceptance needed | Forms/focus/loading | Clipping/controls | HIGH | Inspect current screenshots and interactions; fix discovered defects | Browser keyboard; headless render; physical later | Fixed discovered focus/target/mobile/terminology issues; labels/buttons/mobile and Pi layout/render checks pass |
| PW19 | Database | Delivery enum has check constraint; fresh migrations lack runtime delivery policies | Additive migration retains operation-specific RLS/minimum grants | New stages require DDL; fresh runtime role cannot deliver | Migration/security repair required | Deploy cloud first | BLOCKER | Expand existing constraint; add missing minimal backend grants and per-operation policies; keep browser/public blocked | Disposable PostgreSQL upgrade/check/permissions | Fixed; additive constraint and runtime-policy repair; real restricted-role delivery read/insert/update pass; delete and browser reads denied |
| PW20 | Hardware acceptance | No physical Pi attached to this task | Real boot/display/touch/Wi-Fi/resume validation later | Hardware unavailable | None | Physical behavior unverified | HIGH | Keep separate pending physical checklist | Physical Pi acceptance | Deferred: no physical Pi available; physical boot/display/touch/GPIO/NetworkManager acceptance remains pending |

## Canonical state and authority

Account: `signed_out`, `signed_in` (web session). Pi uses a device credential and
an account relationship, never the student's password or browser session.

Device/account: `not_connected`, `pairing`, `connected`, `offline_cached`,
`verification_required`, `revoked`, `error`. A cached name alone never proves connection.
Connected requires successful verification within 180 seconds; restart/expired verification
requires verification, while network failure retains offline practice and last verified time.

Cloud availability: `offline`, `wifi_only`, `internet_available`, `cloud_unreachable`,
`cloud_available`. Unknown measurements must stay unknown; Wi-Fi is not cloud authentication.
Sync: `idle`, `syncing`, `synced`, `pending`, `failed`, `auth_required`.
Delivery: `not_selected`, `selected`, `queued`, `device_seen`, `downloading`,
`downloaded`, `installed`, `failed`, `removed`. Existing `downloaded` clients remain
compatible but only new `installed` acknowledgement means Ready on Pi.

| Data | Authority | Reconciliation |
| --- | --- | --- |
| StudentAccount | Cloud | Verify active account relationship; retain safe offline labels |
| StudyProfile and active count | Cloud | Add/rename cache; hide archived; never reassign old attempts |
| AccountDeviceLink / ProfileDeviceLink | Cloud | Explicit pairing; revoke on disconnect/archive |
| DeviceCredential | Cloud, secret cached on device | Credential alone never establishes account ownership |
| Library selection | Cloud per profile | Catalogue replaces eligibility cache; bytes/history retained |
| Installed bytes | Pi | Hash/size/schema validation and atomic import before installed ack |
| Delivery progress | Pi reports, cloud persists | Exact authorized version; ordered progress; explicit retry |
| Completed attempts | Pi queue / cloud durable acknowledgement | Immutable start-time scope and UUID idempotency |
| Online status | Cloud observation | Seen within 180 seconds; never implies hardware Wi-Fi state |
| Sync freshness | Reporting client | Show last successful sync and pending/failed counts separately |

## Acceptance ledger

TOTAL AUDIT FINDINGS: 20 — BLOCKER: 2; HIGH: 13; MEDIUM: 5; LOW: 0.
Implementation/UX findings fixed: 16. Existing workflows verified through regression: 3.
Deferred: 1 (PW20, physical Pi unavailable; explicitly separate from local software acceptance).

Cloud full suite: 169 passed, including disposable PostgreSQL, migrations/backup restore,
restricted-role checks and independent Pi-client integrations. Two additional new product
regressions passed (profile/credential reconciliation and four demo roles). Pi full suite:
306 passed; final UI/layout subset: 30 passed. Web: 32 tests, typecheck, ESLint and production
build passed. Student, practice/history and teacher/institute browser suites passed.
The student suite observes all delivery stages through polling, checks restore/replacement,
JSON/manual uploads, labels, button heights and mobile overflow. Thirty Pi logical previews
and matching 800×600 scaled previews were generated; account screens visually inspected.
These checks do not constitute a full WCAG certification or physical-device acceptance.

A first pair of cloud runs collided because they inherited one shared disposable test DB.
Their results were discarded. The successful full run used an explicitly isolated local
PostgreSQL cluster/database; no production database or migration was touched.
See PRODUCT_STATE_CONTRACT.md and PRODUCT_WORKFLOW_REPAIR_REPORT.md for current contract,
validation details and handoff. Earlier phase reports remain historical evidence.

Final stricter delivery-RLS assertion initially failed on a fresh database. The migration now installs the missing runtime SELECT/INSERT/UPDATE policies/grants (matching baseline provisioning). A real FK-backed queued → received → downloading → downloaded → installed row was inserted/read/updated as assessment_backend; DELETE and anon/authenticated reads were denied. The repaired test passed. Final delivery/client/profile/sample subset: 15 passed; final restricted-role recheck: 1 passed; fresh SQLite/RLS smoke: 2 passed.

Final Home profile change now updates the shared banner/navigation immediately. A returning-account refresh is prevented from routing an in-progress assessment to the profile picker; its regression preserves the active question and stored attempt.
