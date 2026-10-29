# Phase 6 — institutes, enrollment and assignment scope

## Ownership and authorization
Institutes are optional organizations. StudentAccount, StudyProfile, personal selections and
all student history remain student-owned. Membership targets exactly one owned StudyProfile;
a student may join multiple institutes. No device, account-wide profile enrollment or legacy claiming occurs.
Existing AdminUser authentication is reused. Platform admins create institutes and become their
owner; owner/admin may add an existing staff account as admin/teacher. Every institute action
requires active staff membership. Teachers manage their institute's consenting members, groups
and assignments. They cannot query personal history or other profiles. Platform-global device,
assignment, result, dashboard and settings APIs require the platform admin role. Existing content
editing tools retain their content-staff compatibility scope. The /teaching shell exposes institute
work only; /staff remains the platform operations portal.

## Consent and enrollment
Staff enter an exact student account email and exact profile name supplied by the student;
ambiguous/missing profiles fail without listing alternatives. A membership starts invited.
A dedicated ENR- token has 96 random bits, expires after 24 hours, is stored only as SHA-256,
and is returned once to the creating staff member. It is separate from PIN, password, pairing
and profile-link codes. Staff share it explicitly; no messaging integration is used.
Student preview displays institute, exact profile and assigned-result sharing scope. Preview/Cancel
does not enroll. Accept requires the authenticated target account and atomically consumes the
pending token. Wrong account, expired, replaced, rejected or replayed codes fail. Reject records
left status. Endpoints are under /api/v1/student/institute-invitations/{preview,accept,reject};
origin checks, no-store and bounded invitation-request rate limiting apply. Raw codes must not
be logged; validation errors omit rejected enrollment input.

## Groups and assignments
Groups are flat institute-scoped classes. Active memberships may join multiple groups.
Assignment creation resolves explicit membership IDs and group members into unique profile
recipients, max 1000. A group snapshot is taken at creation; later group additions do not silently
receive earlier work. Invalid, foreign or inactive members/groups reject the whole assignment.
Assignments select one exact immutable published QuestionPack version at creation. No automatic
latest-version update occurs. Title/instructions/available_from/due_at are retained. Due dates are
informational, not a hard offline cutoff. Available-from is enforced for new online actions.
Existing legacy hardware/global Assignment records keep their original semantics.

## Practice and history
The Phase 5 web runner handles assignment setup/save/resume/server scoring/submit unchanged,
with optional institute_assignment_id validated through the active profile recipient relationship.
Draft and completed shared Attempt rows retain this UUID; personal attempts have null context.
Stable UUID/revision/idempotency behavior remains. Device payload v1 accepts the optional
institute_assignment_id only alongside verified profile ownership and exact assigned set/version.
Omitting this extension preserves old personal/device fingerprint bytes. Existing accepted retries
acknowledge immutable evidence even after membership removal; a new upload requires active scope.
Student unified History includes all owned attempts with Personal Practice / Institute Assignment,
institute name and assignment title. Teachers see only active recipients' attempts for the exact
institute assignment; neither ordinary personal attempts nor unrelated profiles are included.

## Pi delivery and offline state
/api/v1/institute-content/{link_id}/catalog and /packs/{assignment_id} authenticate the paired
device and exact local_profile_id/ProfileDeviceLink, active membership and profile recipient.
No assignment is broadcast to other profiles on a shared Pi. Institute Work has its own UI/cache,
separate from My Library. Download revalidates current authorization and reuses existing exact-byte
size/hash/schema checks and atomic profile-only content import. Existing immutable bytes are
reused only after hash comparison; bytes alone never create a personal grant.
SQLite 0006 adds institute_work eligibility/cache and attempt_institute_context snapshots.
Assignment context and attempt ownership/order are created in the same local transaction.
After download, the existing assessment engine works offline, including confidence/review/resume
and pinned version. Sync refresh can fetch bounded downloads; the screen also offers explicit
refresh/download. Temporary connection failures preserve the last complete catalogue and content.

## Leaving, removal and re-enrollment
Membership status is invited/active/left/revoked. Student leave or staff removal preserves accounts,
profiles, selections, content bytes, drafts, pending local uploads and completed historical evidence.
New online institute starts/saves/submits/downloads/new uploads stop immediately. Student-owned
historical result reads remain available. Teacher member/results access stops; no historical staff
exception is granted. A cached Pi cannot detect removal while disconnected; on next complete
refresh or explicit authorization rejection, future local assignment eligibility stops. Existing
in-progress local work can resume and finish; pending uploads remain local when authorization is
denied and require operator resolution/reactivation policy. No remote deletion is implemented.
Re-enrollment requires fresh consent. Old recipient snapshots predate the new joined_at and do
not silently reactivate. New assignments must explicitly target the renewed membership.

## Migration and deployment
Cloud Alembic 20261029_03 follows Phase 5, adds eight organization/relationship tables and nullable
assignment FKs/indexes to drafts and completed attempts. Existing rows retain null context.
SQLite adds nullable columns without rebuilding historical evidence. New Postgres tables enable
RLS and revoke anon/authenticated access; the backend enforces actor authorization. No public
Data API policy, client secret or Supabase identity migration is added. Downgrade refuses populated
institute data, library selections or browser drafts; roll back application code retaining schema. Empty additive-schema
rollback and repeat upgrade are tested on disposable SQLite/PostgreSQL only. Device migrations
remain forward-only transactional. Deploy cloud before enabling assignment-aware device clients.
No production migration, deployment, commit or push is part of this implementation.

## Deferred
Physical Raspberry Pi hardware acceptance. Browser offline practice. Analytics metrics, ranking,
billing, messaging and broader staff historical retention/access policies. Automatic recovery of
new offline uploads rejected after membership removal requires a future explicit policy; evidence
is preserved and never relabeled as personal practice.


## Phase 8 retained late-upload policy

An offline completion first uploaded after membership removal is rejected by existing
recipient authorization. The device retains the exact UUID, ownership, assignment,
score and responses; sync status becomes failed/permanent and is excluded from automatic
retry. Home/Sync expose Sync attention required, including after restart. No evidence
is deleted or relabeled as personal. A previously accepted identical retry remains
acknowledged. Operator review may explicitly requeue the same UUID after authorization
is resolved; requeue itself grants nothing, and fresh enrollment does not reactivate
old recipients. The safe policy is retention plus attention, not automatic reassignment.
The real cross-repository local HTTP test covers this entire rejection/preservation path;
physical-Pi/hosted validation remains pending. See ROLLBACK.md for exact recovery commands.
