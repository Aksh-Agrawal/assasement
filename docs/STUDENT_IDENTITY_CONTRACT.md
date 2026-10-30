> Current product behavior: [Product state and reconciliation contract](PRODUCT_STATE_CONTRACT.md). This phase contract retains legacy protocol details; the current contract supersedes conflicting student workflow, capacity and delivery wording.

# Student identity and self-service profile linking contract (Phases 2-3)

## Identity boundaries
StudentAccount is the human owner; StudyProfile.account_id is a required server-owned
foreign key. Device.device_id is the existing device-generated installation UUID.
DeviceCredential proves technical device trust and never grants access to every student.
LocalProfile.id / local_profile_id stays device-local. Legacy server_user_id is unverified.

## Website-generated intent
An authenticated student POSTs /api/v1/student/profiles/{profile_id}/link-sessions.
The server verifies the owned active profile and creates ProfileLinkSession with a random
10-character code (50 bits from an unambiguous alphabet), domain-separated HMAC code_hash,
account/profile IDs, pending status, creation and expiry timestamps. The raw code is returned
once and kept only in transient UI state. PROFILE_LINK_TTL_SECONDS defaults to 600 seconds
and is bounded to 1-3600 seconds. Stable ADMIN_AUTH_SECRET is required across workers.

GET .../link-sessions/{id} returns status and expiry without the code.
POST .../link-sessions/{id}/cancel cancels a pending intent.
New codes supersede previous pending intents for that same profile. Statuses:
pending, consumed, expired, cancelled. Student access is always account-scoped.
The website polls status/links every three seconds while the profile view is open,
shows a countdown, removes terminal codes, and supports explicit cancellation.

## Device claim and persistent relationship
POST /api/v1/profile-links/claim accepts only {code, local_profile_id} using the existing
device bearer credential. Account, study-profile and device IDs cannot be asserted by the
body. The server derives device identity from credentials and account/profile from the intent.
Missing/invalid credentials fail 401; invalid, expired, consumed and cancelled codes have
safe LINK_* errors. Input owner fields are rejected.

Device and intent row locks plus a conditional pending-to-consumed update and one transaction
make consumption and ProfileDeviceLink creation atomic. A partial unique index allows only
one active relationship for each device/local-profile pair. Composite foreign keys enforce
the study-profile/account relationship. Database or conflict failures roll back consumption.
Claims are rate-limited per IP by the existing process-local limiter; multiworker production
requires shared ingress rate limits as with existing authentication.

ProfileDeviceLink retains id, account/profile, device registry ID, exact local_profile_id,
active/revoked status, creation/update/revocation timestamps. A conflicting active mapping
returns LINK_PROFILE_CONFLICT. A revoked mapping may relink only to the same cloud profile
with a fresh code/new link ID. Profile/account transfers are not implemented.

The response includes status, link_id, student_account_id, study_profile_id,
study_profile_name, account_display_name, local_profile_id, device_name and link timestamps.
No password hash, student session token or device credential is returned.

GET /api/v1/profile-links/current?local_profile_id=... is scoped to the authenticated device.
It supports explicit refresh/recovery after a lost claim acknowledgement.
GET /api/v1/student/profiles/{profile_id}/links lists only the owner's links.
DELETE .../links/{link_id} revokes only that owner's relationship.
POST /api/v1/profile-links/unlink accepts {local_profile_id, link_id}, checks the exact device
relationship, and revokes it. Revocation never deletes attempts, profiles, local SQLite,
installation identity or device credentials. Remote revocation reaches the Pi on explicit
Refresh link status; until then its local label is a cache, never server authority.

## Pi flow and persistence
Settings -> Account / Profiles -> Link Study Profile -> enter website code ->
confirm the explicit local profile -> asynchronous submission -> linked account/profile display.
Touch, keyboard and canonical input actions share the same route. Back before confirmation
clears the code without submitting. Once confirmed, leaving the screen does not undo a server
claim; the worker persists the result to the selected profile. Refresh link status recovers a
server success if the response/persistence was interrupted. Codes are not stored in SQLite.

Phase 2 fields profiles.cloud_account_id/cloud_profile_id and ownership_state/link_state
are reused. Successful explicit claim sets owned/linked on only the selected local profile.
SQLite 0004 adds profile_link_context (link ID and display labels) and attempt_ownership
(an immutable creation-time link/profile snapshot); these are needed beyond Phase 2's fields.
Unlink retains the known owner and sets link_state=unlinked. It does not make the profile
available for transfer to another account. Existing local profile IDs never change.

Network operations use bounded timeouts on the existing background service. Ready, submitting,
success, invalid/expired/used/conflict, authentication and safe network/server failures are
displayed without raw HTTP exceptions. Startup and offline assessment do not depend on linking.

## Attempt ownership extension
Existing v1 payloads remain accepted unchanged. For a newly started linked assessment,
the device includes optional top-level ownership = {study_profile_id, link_id}, captured
from the exact local profile when create_attempt commits. The serializer never reads today's
profile mapping to infer ownership for an older attempt. Legacy/in-progress attempts without
a snapshot omit ownership forever, even after an explicit profile link.

Cloud ingestion verifies link ID + authenticated installation + local_profile_id +
study_profile_id + active owner/profile status. It also rejects a started_at before link
creation. This is device-reported timing, not an anti-cheating or attestation guarantee.
Only then does it store study_profile_id, source=device and ownership_state=owned.
Legacy requests retain null study_profile_id and legacy_unclaimed state.

Ownership is part of the stable payload fingerprint when present. Its absence produces
the original v1 fingerprint. An existing identical durable attempt is acknowledged even
after revocation; a new upload against a revoked/mismatched relationship is rejected and
local work is retained. Historical ownership, answers, scores and content versions never
change when a link is revoked. Deploy the new cloud before enabling device ownership uploads;
older cloud builds do not understand the optional extension.

## Migrations and pending work
Cloud 20261028_02 follows 20261028_01, adds link tables and owner/active-link constraints,
and protects them with PostgreSQL RLS/no public access. Roll back code while retaining schema
when link/session data exists; downgrade refuses destructive removal of such records.
SQLite migrations are forward-only and transactional. Never reset a deployed database.

Deferred: legacy attempt claiming, account/profile transfer, institute workflows, analytics metrics, account recovery/provider decisions,
offline student-auth duration and physical Pi acceptance. Cached account hints still require
verification; linking does not create an offline student login policy.


## Phase 4 student content

Independent student discovery, personal selections and exact linked-profile delivery are now
implemented. See [student library contract](STUDENT_LIBRARY_CONTRACT.md) for routes, eligibility,
offline refresh/removal behavior, legacy shared content and additive migrations.


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
