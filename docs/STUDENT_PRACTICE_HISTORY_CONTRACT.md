# Phase 5 browser practice and unified StudyProfile history

## Completed attempts are one domain
The cloud's existing Attempt and AttemptResponse tables retain device rows and now also store
completed browser work. Explicit source is web or device; ownership remains a verified
study_profile_id. The legacy column device_attempt_id is the stable external attempt UUID
for both sources, with the existing global unique constraint. It is never inferred from
device_id or reused as an account/profile identity. Browser device fields are null and the
required legacy profile_id context is the non-authorizing sentinel web. Authorization always
uses the separate study_profile_id relationship.

PracticeSession stores only the browser lifecycle/draft: stable UUID, account/profile,
pack foreign key, full server-only content snapshot, saved question order, progress, revision,
save deduplication fields and an optional completed_attempt_id. Completing one inserts one
common Attempt plus response rows in the same transaction as the completed draft state.
Drafts are not completed history. Different UUIDs remain distinct even with identical packs,
dates, scores or response state.

## Browser lifecycle and routes
My Library -> Practice on Web -> Test Setup -> Start Practice -> Question -> Confidence ->
Previous/Next/Review -> Submit confirmation -> Result/Review -> History.
Routes: /web-practice/setup/{profile_id}/{set_id}, /web-practice/{attempt_uuid},
/history, /history/profile/{profile_id}, /history/{attempt_uuid}.

A client UUID is generated at Start Practice and retained as an idempotent start key in
sessionStorage until acknowledged. It is an attempt identity, not a session credential.
Starting again with the same UUID/profile/set returns the existing attempt without repinning.
Independent fresh starts use new UUIDs. Device ingestion rejects UUIDs reserved by web drafts.

POST /api/v1/student/profiles/{profile_id}/practice/start accepts {attempt_id,set_id}.
The server validates the current student, owned active profile, active personal selection and
latest student-discoverable published content. Storage bytes must pass existing hash, size,
schema and semantic validation before the complete pinned snapshot is stored.
No device credential, teacher assignment, institute or staff approval is needed.

GET /api/v1/student/profiles/{profile_id}/practice lists up to 100 unfinished attempts.
GET /api/v1/student/practice/{attempt_uuid} returns the owned draft and sanitized questions.
Correct keys/explanations are not included before completion. Question order is the pack's
(position,id) order stored once at start. New publication never changes a draft's exact version.
Already-authorized drafts can resume/finish after selection removal or pack archival; their
pinned snapshot is retained. New starts revalidate current eligibility.

## Autosave, concurrency and interruption
PATCH /api/v1/student/practice/{attempt_uuid} accepts:
{revision, mutation_id, progress: {current_index, phase, responses}}.
phase is question, confidence or submit_confirm. Each response has question_id,
selected_key (A-D or null), confidence (sure/not_sure/guessing/unrated or null),
marked_review and cumulative response_time_ms. Skips have no confidence. Selecting an answer
persists unrated confidence immediately while the confidence step awaits the student's choice.

The server rejects changed/missing/duplicate question identities, out-of-range progress,
client score/correctness fields, and invalid answer/confidence combinations. A conditional
revision update prevents lost updates from multiple tabs. An identical last mutation_id and
payload returns its confirmed acknowledgement; reusing it with changed data conflicts.
Older/stale revisions receive 409 and require reloading confirmed progress.

The browser saves on answer/confidence/review/navigation changes and every 15 seconds while
visible. Timing is bounded client-reported active interaction time, not certified telemetry.
The timer does not count failed-request waiting time as confirmed work. Server timestamps
record start, update and completion; API timestamps are normalized to UTC. Responses use
server-known start/completion timing rather than claiming exact browser event timestamps.

Failed saves retain an explicit pending request and show:
Connection interrupted. Your last confirmed progress is saved. Retry when connected.
Retry repeats the exact mutation UUID/revision/payload. Reload uses the last confirmed server
state; unconfirmed local edits may be discarded only with an explicit reload confirmation.
Re-login can resume server-confirmed drafts from Continue Practice.
No offline browser/PWA behavior is claimed. The Pi remains offline-first.

## Confirmation, scoring and idempotent completion
The browser shows answered/unanswered/review counts and explicit Continue Practice and
Submit Assessment choices. POST /api/v1/student/practice/{attempt_uuid}/submit accepts only
{revision}; it requires saved submit_confirm state and matching revision.

Web score/correctness are computed on the server from the pinned content using the existing
pure scoring semantics. shared/scoring.py is the cloud-owned independent copy of the Pi's
pure scorer, using the existing cloud shared/models.py; there is no runtime dependency on
the device checkout. Correct/wrong/skip marks, skipped-response behavior, confidence buckets
and accuracy (correct/answered, zero when no answers) match the Pi contract.

The server stores an immutable result_snapshot on the common completed Attempt:
score, maximum_score, correct/wrong/skipped counts, accuracy, duration and confidence counts.
It ignores no arbitrary client result: score/correctness fields are rejected by strict input.
Row locking and a revision compare-and-set make submission atomic on PostgreSQL and SQLite.
The original submitted revision is retained. Identical retry returns the same completed
result; another revision conflicts. Completed progress cannot be edited. A lost response
therefore never creates a second completed attempt.

Device ingestion remains unchanged in trust: source=device is explicit; scores and correctness
remain device-uploaded snapshots, not server regrading or an anti-cheating claim. Existing
UUID, fingerprint and durable acknowledgement behavior is preserved. Legacy/unclaimed work
is not automatically assigned to a student.

## Unified history and review
GET /api/v1/student/profiles/{profile_id}/history returns paginated completed attempts,
with optional source=web|device filter. GET /api/v1/student/history/{attempt_uuid} returns detail.
Both join Attempt.study_profile_id to the authenticated student's StudyProfile and exclude
legacy_unclaimed rows. A UUID from another account returns 404. Draft get/save/submit and
draft list endpoints enforce the same owner boundary. A profile switch changes library,
draft and history context, never ownership labels.

Ordinary student responses show source, content/version, timestamps, result and review,
without device UUID, local-profile context, credential, network metadata or staff data.
Web and Raspberry Pi are clear source labels. Duplicate upload retries cannot add entries.
Removing a library selection or revoking a link never deletes completed history.

Browser review uses the draft's retained pinned snapshot. Device review uses retained
ContentVersion bytes for that exact set/version, regardless of current library visibility.
Device score/correctness are still the uploaded historical snapshot. If older device content
was never retained by this server, uploaded responses remain visible with an honest unavailable
question-text/correct-key/maximum-score state; no newer version substitutes for it.

Analytics remains a neutral placeholder. These are per-attempt results only, not performance
trends, predictions, rankings or recommendations. Institutes remain unimplemented.

## Schema and operations
Cloud migration 20261029_02 follows 20261029_01. It adds nullable attempts.result_snapshot
(with no legacy data rewrite) and the practice_sessions table, restricted foreign keys,
revision/state consistency checks, a unique completion FK and owner/status index.
RLS is enabled and anon/authenticated grants revoked. Students use backend authorization,
never Supabase keys or direct database access.

Run Alembic via the existing privileged migration process after recording current revision
and verifying operator backups. Production was not migrated by implementation/testing.
Fresh/Phase-4 upgrades, repeats, PostgreSQL metadata checks, legacy preservation and empty
rollback are tested on disposable databases. Downgrade refuses populated practice data or
result snapshots; roll back application code retaining the additive schema.

No device schema, upload format, UI or scoring behavior changes are needed in Phase 5.
The existing source=device and explicit ownership snapshot already satisfy unified history.
Device code remains independent. Both repositories retain matching copies of this contract.

## Verification and pending acceptance
Run both root README test commands; set DEVICE_REPO_PATH for real cross-repository tests.
Only disposable TEST_DATABASE_URL databases may run destructive test fixtures.
web/tests/practice.browser.mjs starts isolated local servers and a temporary SQLite database,
exercises browser save/refresh/network/retry/result and uses the real Pi client to prove
unified history. It supports PLAYWRIGHT_MODULE and BROWSER_CHANNEL like the prior smoke.
Existing web/tests/student.browser.mjs remains the identity/linking/library regression.

Physical Pi verification remains pending. Browser offline practice, institute workflows,
analytics metrics, profile/account transfer and legacy claiming remain deferred.


## Phase 6 institute work
Optional consent-based profile membership, scoped teaching, group assignments, web/Pi delivery
and assignment-only result access are now implemented. Personal ownership remains unchanged.
See [institute assignment contract](INSTITUTE_ASSIGNMENT_CONTRACT.md) for current behavior,
removal/retention rules, compatibility and deferred policies.
