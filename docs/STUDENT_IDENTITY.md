# Phase 2 local identity preparation

Migration 0003 adds nullable cloud account/profile identifiers and explicit unclaimed/
unlinked defaults to profiles, plus a cached account-context table. The numbered
transactional migration runner applies it once; repeat startup is a no-op. Existing
attempt/response/content tables and sync payloads are untouched. Profile constraints
reject incomplete ownership metadata. A mapping stored locally is not proof accepted
by the cloud, and Phase 3 adds the explicit server-verified claim flow described below.

StartupSession.student_context exposes a local-only StudentRoutingContext after
migration. Cached hints always require verification and do not grant offline login
or creation permission. Current legacy profile selection and creation remain available
as the explicitly retained migration/testing flow. No new account login network
request runs at startup. No password or auth session token is stored locally.

Use the existing database backup procedure before deploying. Schema 2 upgrades to 3
without rebuilding SQLite. Roll back application code and keep the added columns/table;
do not downgrade/recreate an existing Pi database. The account-context cache can be
cleared without touching profiles, attempts or sync state.

Verify with pytest, ruff and the existing headless UI tests. The migration tests include
old profile IDs and arbitrary server_user_id values; assessment preservation tests
retain answers, confidence, pinned versions and pending sync through upgrade. Physical
Pi display/GPIO performance and real hosted connectivity remain deployment acceptance.

See STUDENT_IDENTITY_CONTRACT.md for every field and deferred policy.


## Phase 3 - self-service profile linking

The website generates a short-lived code for one owned study profile. The Pi enters it
under Settings -> Account / Profiles, confirms the selected local profile, and claims it
with its existing technical device credential. There is no staff approval for profile
linking. Technical device pairing remains the separate existing trust/bootstrap flow.

See STUDENT_IDENTITY_CONTRACT.md for the exact endpoints, secret lifecycle, field owners,
safe errors, concurrency/replay protection, unlink semantics and attempt ownership extension.

Cloud migration 20261028_02 is additive to Phase 2. It creates ProfileLinkSession and
ProfileDeviceLink, a composite owner foreign key, and an active device/local-profile
unique index. Fresh and Phase-2 upgrades and repeat no-ops are tested on SQLite/PostgreSQL.
The rollback guard retains populated link structures; prefer code rollback with the schema.

Device migration 0004 is necessary for durable link ID/display labels and immutable
attempt-start ownership snapshots, which Phase 2 did not store. Existing SQLite rows are
retained. Legacy attempts are not backfilled. A local profile can be claimed only by the
explicit user flow; no other local profile is modified. Linked identity survives restart.

Unlink revokes future profile authorization and retains historical ownership, SQLite data,
student profiles and technical credentials. The Pi offers an explicit link-status refresh
for remote revocation or lost acknowledgements. Relinking to a different owner/profile is
rejected; transfer/merge policy remains deferred.

Regression coverage includes deterministic expiry, code cancellation/replay, concurrent
same/different-device claims, foreign-account enumeration/mutation denial, migration data
preservation, real cross-repository HTTP pairing/link/restart/assessment/sync, and real web
browser code generation/cancel/claim/device-list/unlink. Device tests cover keyboard/touch
routing, safe errors, selected-profile persistence, restart and attempt-start snapshots.
Physical Pi hardware validation remains pending.

Verification: run the root README commands, set DEVICE_REPO_PATH for cloud/device integration,
and use only the disposable TEST_DATABASE_URL for PostgreSQL tests. Optional web browser smoke:
build web/, then run node tests/student.browser.mjs with Playwright available. It uses its own
temporary database and local servers; no production records are touched.


## Phase 4 - independent student library

Cloud head 20261029_01 adds student_library_publications, library_selections and
profile_content_deliveries. Device SQLite 0005 adds profile-only storage scope and durable
profile_library eligibility. Existing immutable packs, attempts, links, assignments and
credentials are preserved; no production migration or deployment was performed.

Staff explicitly expose published versions through Show in student library. Students browse
General Library, choose an owned profile, Add to My Library and Send to Pi for one linked local
profile. No teacher assignment, institute membership or device-wide assignment is required.
Existing assignment/publishing APIs remain operational. Analytics is unchanged.

Device Settings -> Content Updates refreshes the selected profile's catalogue and downloads
eligible packs. The existing sync service's refresh cycle handles bounded queued deliveries
in the background. tools.sync_content --profile LOCAL_PROFILE_ID supports the same flow.
Downloaded eligible content works offline; profile switching updates visibility. Old shared
content retains its compatibility policy. Private packs remain hidden from unrelated profiles.
Removing selections updates eligibility on successful refresh, retaining bytes and all history.
Newly published/exposed versions are offered separately and do not change active attempts.

See STUDENT_LIBRARY_CONTRACT.md for exact security boundaries, version policy, migration and
rollback instructions. Complete testing requires the disposable PostgreSQL test database and
DEVICE_REPO_PATH for the real independent device checkout. Physical Pi verification remains
pending. Browser practice and unified history are implemented by the Phase 5 extension below.


## Phase 5 - browser practice and unified history

Browser practice now starts from an owned profile's selected library, persists a stable UUID,
pins content/order, saves progress with revision checks and resumes after refresh/re-login.
The server scores web submissions and inserts completed results into the common Attempt domain.
Personal StudyProfile History includes both web and correctly linked Pi attempts, with source
labels and account-scoped results/review. No legacy work is claimed, and removing content or
unlinking a device does not erase history. Analytics remains a placeholder.

See [practice/history contract](STUDENT_PRACTICE_HISTORY_CONTRACT.md) for exact lifecycle,
routes, server/device scoring trust, retry/concurrency semantics, migration 20261029_02 and
retention behavior. Browser practice requires a connection; no offline browser support is
claimed. The Pi's existing upload/schema/UI remain unchanged in Phase 5. Physical Pi acceptance
is pending.


## Phase 6 institute work
Optional consent-based profile membership, scoped teaching, group assignments, web/Pi delivery
and assignment-only result access are now implemented. Personal ownership remains unchanged.
See [institute assignment contract](INSTITUTE_ASSIGNMENT_CONTRACT.md) for current behavior,
removal/retention rules, compatibility and deferred policies.
