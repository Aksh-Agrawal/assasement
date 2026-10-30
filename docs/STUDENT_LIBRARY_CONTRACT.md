> Current product behavior: [Product state and reconciliation contract](PRODUCT_STATE_CONTRACT.md). This phase contract retains legacy protocol details; the current contract supersedes conflicting student workflow, capacity and delivery wording.

# Phase 4 student library and profile-content contract

## Separate responsibilities
Published immutable QuestionPack/ContentVersion records retain the existing pack format.
StudentLibraryPublication is an explicit staff opt-in for discovery of one published version.
Existing packs default to NOT discoverable; no assignment or publication is silently made public.
LibrarySelection expresses an authenticated student's owned study profile choosing a set.
Assignment retains the old staff/device distribution contract and is not a personal selection.
ProfileContentDelivery targets one selection and one active ProfileDeviceLink.
Local question_sets/questions store verified physical content; per-profile eligibility is separate.

## Discovery and versions
Staff use Show/Hide in student library on a published version, or
PUT /api/v1/admin/content/versions/{version_id}/student-library with {enabled: true|false}.
This changes a discovery record, not immutable pack bytes or published metadata.
Only active packs with PUBLISHED ContentVersion and enabled discovery appear.
Drafts, archived/internal packs, storage keys and auth secrets never appear in the student library.

GET /api/v1/student/library accepts optional owned profile_id, subject, chapter, title search,
selected, offset and limit (maximum 100). It returns latest available versions, safe metadata,
selection IDs only for the requested owned profile, and next_offset.
GET /api/v1/student/library/{set_id} returns current safe details;
GET .../{set_id}/versions returns discoverable immutable versions.
Current taxonomy uses actual subject/chapter/set metadata; there is no invented collection,
complete exam taxonomy or exam-engine capability.

Selections use version_policy=latest_available: the latest student-discoverable published
version is eligible. This is visible in the UI. A version must be explicitly exposed before
it becomes an update. Current attempts never change version. Installed older versions of a
still-selected set remain locally available until removal; all physical versions remain for
resume/review. Browser assessment is implemented in Phase 5.

## Personal selection and delivery
GET/POST /api/v1/student/profiles/{profile_id}/library lists/adds selections.
POST accepts only {set_id}; account and profile ownership come from the authenticated actor.
DELETE .../library/{selection_id} marks the selection removed and its deliveries removed.
Re-adding reactivates the selection but does not silently restore old removed deliveries.

POST .../library/{selection_id}/deliveries accepts {link_id}.
The server validates selection owner, owned active profile, same-account/same-profile active
ProfileDeviceLink, and content availability before queuing delivery. It never targets all
devices or all local profiles. Multiple explicit links can each receive a delivery.
Student views show Ready to send, Queued, Downloaded, Failed - retry, Link revoked or Unavailable.
Downloaded is a device-reported acknowledgement for a specific immutable version; it does
not claim realtime online connectivity or prove physical storage beyond that report.
A newly published version returns delivery status to Queued until that version is acknowledged.

## Profile-scoped device contract
Old /api/v1/content/catalog and /packs/{set_id}/{version} retain assignment-only semantics.
New clients use:
- GET /api/v1/profile-content/{link_id}/catalog?local_profile_id=...&offset=...&limit=...
- GET /api/v1/profile-content/{link_id}/packs/{set_id}/{version}?local_profile_id=...
- POST /api/v1/profile-content/{link_id}/status
  {local_profile_id, set_id, version, status: downloaded|failed}

All requests authenticate the technical device credential AND validate the exact active link,
local profile ID, study profile and owner. An unlinked/unrelated device cannot obtain these bytes.
A profile catalogue includes only active selections explicitly delivered to that link, with
enabled/published versions. Download and acknowledgement revalidate eligibility. Revoked links,
removed selections and hidden/archive-only content fail closed. Catalogue pagination is bounded
at 100 records per page; the Pi fetches at most 1000 records and preserves its old complete cache
if the response is incomplete/too large. No partial refresh removes grants.
Pack metadata uses the established schema_version=1 exact-byte fields plus catalogue next_offset;
the legacy catalogue is not changed. Content storage remains private and serves through FastAPI.

## Device storage and visibility
SQLite 0005 adds private_pack_versions and profile_library; full question metadata/bytes remain
deduplicated in the existing immutable tables. New profile-scoped imports mark the exact physical
version private in the SAME transaction as question/pack insertion. A second authorized local
profile reuses verified bytes without copying them. Its eligibility is still separately required.
The existing importer, size/hash/schema validator, downloader and atomic transaction are reused.

Legacy/current local imports and assignment downloads remain shared compatibility content.
Pre-Phase-4 installed packs remain shared rather than disappearing after migration. Private
student-delivered versions are excluded from unrelated legacy and linked profiles, including when
they are physically present. Linking an existing profile does not silently change the historical
shared-content policy. A local operator importing packs through the old explicit CLI remains a
shared-content workflow; it is not a profile-scoped authorization channel.

The UI derives subjects, chapters, downloaded packs and available downloads from the selected
local profile. It reads only that profile's durable eligibility and cached safe catalogue.
Switching profiles refreshes the library and download context. AssessmentApplication checks
eligibility before starting a NEW private-pack attempt; resume and historical review use their
existing pinned references even after removal. Low-level repository storage remains a trusted
local persistence layer, not a substitute for cloud authentication or OS access control.

## Offline, refresh, removal and updates
Successful complete profile catalogue refresh updates local eligibility. Removed sets lose
future visibility for that profile; their physical versions, active attempts and results stay.
A network/timeout/server failure leaves the last complete authorized cache intact, allowing
downloaded content offline. An explicit authorization rejection clears that profile's cached
eligibility. Unlink also disables access through the existing link-state check.

The device cannot learn about a remote removal while offline. Revocation/removal applies
locally on the next successful refresh (or an authorization rejection); immediate offline
revocation is not claimed. Background network jobs never gate GUI startup or local practice.
The sync service refresh cycle performs bounded selected-profile deliveries; GUI Content Updates
offers explicit refresh/download. CLI: tools.sync_content --profile LOCAL_PROFILE_ID. Plain
sync_content retains legacy assignment semantics. Deploy updated cloud before newer clients.

After importing a newer version, the UI offers it separately. No active attempt question order,
answers/confidence, score or set_version is updated. Removal performs no byte deletion. Cached
bytes retained for other profiles and historical review are never exposed as a grant by themselves.
Physical cleanup/garbage collection is deferred.

## Schema/ownership and rollback
Cloud migration 20261029_01 follows 20261028_02 and adds only discovery, selection and delivery
tables. Composite study-profile/account FK and unique profile/set and selection/link constraints
protect identity and deduplication. RLS and revoked anon/authenticated grants keep new tables
private to backend authorization. No Supabase keys are sent to clients.
Roll back code retaining additive schema when library data exists; downgrade refuses to remove
populated library tables. Empty-schema rollback is tested only on disposable databases.
SQLite uses the existing forward-only transactional migration runner. No deployed DB is reset.

## Deferred
Collections/licensing taxonomy, institute recipient
redesign, metrics/recommendations, physical byte cleanup, deployed physical Pi acceptance.
Analytics remains the existing neutral placeholder. Student discovery does not imply content
licensing or production educational approval; the shipped sample remains a development fixture.


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
