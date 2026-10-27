# Architecture Decision Log

Status: Phase 0 decisions. A decision marked accepted is frozen for the first prototype unless superseded by a later recorded ADR.

## ADR-001 — Python for the prototype

**Status:** Accepted

The device application will use Python 3.11 or later for the prototype. This does not select a GUI framework.

## ADR-002 — SQLite is the offline source of truth

**Status:** Accepted

Committed on-device assessment state is stored in SQLite. Server synchronization is downstream of local persistence and does not replace SQLite as the operational source of truth on the device.

## ADR-003 — Assessment never depends on network

**Status:** Accepted

Installed assessments must support questions, answers, navigation, local submission, results, and review without network access. Network failures cannot block these functions.

## ADR-004 — First prototype supports one question form

**Status:** Accepted

The first prototype supports single-correct MCQs with exactly four options keyed `A`, `B`, `C`, and `D`. Other question types are out of scope.

## ADR-005 — Answer keys are stored locally

**Status:** Accepted

Question packs contain local answer keys because this is a practice device, not a secure proctored examination system. This tradeoff enables fully offline scoring and review and does not claim resistance to content extraction.

## ADR-006 — Touch and buttons share an Action abstraction

**Status:** Accepted

Touchscreen controls and physical GPIO buttons emit the same logical actions. Core assessment behavior is independent of the input source.

## ADR-007 — GUI framework is not selected

**Status:** Open / intentionally deferred

The GUI framework will be selected only after candidates are benchmarked on actual Raspberry Pi Zero 2 W hardware with the target display workload. Phase 0 does not select Kivy, pygame, or another framework.

## ADR-008 — Raspberry Pi OS bitness is not selected

**Status:** Open / intentionally deferred

The choice between 32-bit and 64-bit Raspberry Pi OS must be based on measurements of memory use, startup time, dependency support, and runtime behavior on prototype hardware.

## ADR-009 — Phase 1 repository and tooling baseline

**Status:** Accepted

The implementation baseline is Python 3.11 or later, packaged from the `app` namespace with boundaries matching the Phase 0 architecture. Pytest is the test runner, Ruff is the linter, and GitHub Actions on Ubuntu with Python 3.11 runs both checks for pushes and pull requests. Runtime dependencies remain empty in Phase 1; development dependencies are limited to Pytest and Ruff. Future-layer modules contain boundaries only and do not pull implementation dependencies forward.

## ADR-010 — Pure scoring consumes the complete question universe

**Status:** Accepted

Scoring is a deterministic, platform-independent pure function in `app/core/`. It compares final selected keys to local question answer keys and uses the question set's marking configuration. The complete question mapping is authoritative for assessment size: a missing response and an explicit response without a selected key both count as skipped. Unknown question references and duplicate current responses are rejected instead of ignored or double-counted. Insight question IDs are ordered by question position with question ID as a deterministic fallback.

## ADR-011 — SQLite migrations and repository transaction policy

**Status:** Accepted

The data layer uses standard-library SQLite with WAL, `synchronous=FULL`, foreign keys, and a 5000 ms busy timeout. Numbered SQL migrations are forward-only and each migration plus version update is atomic. Repository connections are caller-scoped, writes use short explicit transactions, and multi-row invariants are committed atomically. Question-set content is immutable after insertion; one in-progress attempt per profile is enforced; saved attempt order is write-once; and response upserts preserve the original current-response ID.

## ADR-012 — Phase 4 resume and incomplete-confidence policy

**Status:** Accepted

Resume uses the attempt's persisted question order and exact question-set version, never the current active pack. The first unanswered question becomes active; when every question is answered, the final question becomes active and submission still requires explicit confirmation. Selecting an answer is immediately committed with confidence `unrated`; a later explicit confidence selection updates that same response. This makes the interval between answer selection and the confidence prompt crash-safe without weakening the Phase 2 confidence/scoring contract. Closed-process downtime is excluded by restarting monotonic timing from the persisted accumulated total.

The existing one-in-progress-attempt-per-profile invariant remains the product rule. A profile must resume or explicitly abandon its existing attempt before starting another; abandonment preserves history and never deletes the attempt.

## ADR-013 — Validated immutable pack installation

**Status:** Accepted

Question packs are completely validated before database access: Draft 2020-12 JSON Schema validation is followed by semantic cross-item/path validation and existing-domain-model conversion. SHA-256 covers the exact input bytes and is stored as lowercase hexadecimal; Phase 5 does not define a logical/canonical JSON hash.

Every `(set_id, version)` is immutable, and duplicate imports are rejected rather than treated as replacement or idempotent update. Metadata, questions, and optional active-version switching commit in one SQLite transaction. Older versions remain installed, while attempts stay pinned to their original version and persisted question order. Pack deletion is not exposed in Phase 5.

## ADR-014 — Phase 6A input simulation and GPIO boundary

**Status:** Accepted for bring-up preparation; hardware verification pending

Keyboard and future GPIO inputs reuse the existing canonical `Action` enum. Adapters translate physical input only and contain no assessment or screen business logic. Escape maps to `BACK`. The shared physical controls default to `NEXT` and `MENU`; a future screen action router may resolve them to `CONFIRM` and `BACK` without changing GPIO wiring.

The prototype BCM plan is A=5, B=6, C=13, D=19, PREV=26, NEXT/CONFIRM=20, and MENU/BACK=21. GPIO uses internal pull-ups, active-low switches, and an initial 40 ms software debounce target. `gpiozero` remains a Pi-side optional dependency and is imported lazily so laptop tests do not require GPIO packages or hardware. None of these electrical choices is marked verified until physical-button testing is performed.

## ADR-015 — Pygame-compatible Phase 7A desktop prototype

**Status:** Accepted for Phase 7A prototype only; production choice pending

The laptop prototype uses the pygame API supplied by the `pygame-ce` package, selected because it
has a compatible CPython 3.14 wheel in the development environment. It is isolated in the `gui`
optional dependency group. The UI renders to one 800×480 logical surface and scales that surface
for a resizable desktop window. Keyboard and mouse interactions both become canonical Actions
before reaching the framework-neutral controller.

This does **not** supersede ADR-007. The final production GUI framework is **PENDING PHASE 7B**
and requires measurements on the actual Raspberry Pi and display. No Phase 7A laptop observation
is evidence of Raspberry Pi memory use, frame rate, touch latency, or startup performance.

## ADR-016 — Phase 8A laptop UI routing and long-content policy

**Status:** Accepted for laptop implementation

The offline laptop UI uses distinct profile, installed-subject, and question-set screens before
entering the existing assessment state machine. Subjects and sets come from repository-loaded
question packs. Presentation selection indices are UI state; attempt state and rules remain in the
application service and engine.

Typical content is wrapped on the main 800×480 question and review screens. A lightweight
three-page full-content view, reached through canonical `CONFIRM` and navigated with `PREV` and
`NEXT`, keeps long question, option, and explanation content available without tiny scrollbars or
new input abstractions. This is a laptop usability decision, not Raspberry Pi validation.

## ADR-017 — Phase 9A local-first attempt synchronization

**Status:** Accepted; implemented through the Phase 9C backend contract

Assessment completion never performs HTTP. The local completion transaction marks the attempt
`completed + pending`, after which an explicitly invoked one-shot worker owns synchronization.
Completed attempt content is immutable to the sync layer and is never deleted by sync outcomes.

The attempt UUID is the upload resource ID and `Idempotency-Key`. Payload version 1 is built only
from authoritative persisted values, retains the attempt's exact `(set_id, set_version)`, and orders
responses by persisted attempt-question position. A proven already-accepted response for the same
UUID is success.

The worker processes an oldest-completed-first bounded batch. It persists `syncing` before HTTP,
uses deterministic bounded exponential retry delays without sleeping, and stores retry due time,
failure category, and a short diagnostic. Transient failures are automatically eligible until five
failed uploads by default. Permanent and authentication failures remain `failed` for diagnostics
and manual/future recovery but are not automatically selected. A stale `syncing` lease is reset to
`pending` on a later cycle so crashes cannot strand an attempt.

## ADR-018 — PostgreSQL server persistence with retained SQLite boundaries

**Status:** Accepted and validated for Phase 9C

PostgreSQL is selected as backend/server persistence. Device persistence remains SQLite because
offline assessment execution is a hard requirement; Phase 9C does not alter the device repository
or its migrations. These databases have different responsibilities and are not interchangeable.

The backend uses one SQLAlchemy ORM model set and session/service path for PostgreSQL and SQLite.
SQLAlchemy's cross-platform UUID type maps device attempt identities to native PostgreSQL UUID and
compatible SQLite storage. Timestamps entering the API must be timezone-aware; PostgreSQL stores
them with time zone and application-created audit timestamps use UTC.

Alembic owns backend PostgreSQL schema changes. Production migration policy is forward-only;
downgrades exist for safe local/test recreation, not as an automatic production rollback plan.
SQLite remains available for fast backend tests and smoke development, where startup can create
the disposable schema. PostgreSQL schemas must be migrated before FastAPI serves uploads.

Attempt identity and per-question response uniqueness remain database constraints. Response
foreign keys use restricted deletion to protect immutable assessment history. The existing
canonical SHA-256 fingerprint and transactional attempt-plus-responses insert are unchanged.

The decision was validated on Windows with PostgreSQL 17.11, service `postgresql-x64-17`, an
isolated development database and destructive-test database, and non-superuser `assessment_app`.
Fresh and repeat migrations, real device sync, rollback, idempotency, conflict, concurrency, lost
acknowledgement, FastAPI/PostgreSQL restart, and outage recovery all passed. No credential value is
recorded in the repository.

## ADR-019 — Paired device credentials

**Status:** Accepted for Phase 10A

The device identity is a generated UUIDv4 persisted in local `schema_meta`; no MAC address,
hostname, or hardware serial is used. Pairing uses a cryptographically random, short-lived,
single-use six-digit code plus an independent high-entropy claim secret. Credentials use a public
lookup identifier and high-entropy secret; only a SHA-256 hash is stored server-side and direct
comparisons use constant-time checking.

Credential records are separate from devices so revocation, replacement, and later rotation are
possible. Re-pairing issues a fresh secret and revokes the previous active credential. Pairing and
authentication are sync-only concerns and never gate local assessment work.

## ADR-020 — Explicit recovery instead of destructive automation

**Status:** Accepted for Phase 10B

SQLite corruption never triggers automatic deletion or reinitialization. Startup fails with a
controlled local-database error so the original evidence remains available. Restore is an explicit
operator action against an integrity-validated backup and makes a destination safety copy.
Completed assessments remain local through all sync failures; stale `syncing` leases are
recoverable, and manual retry changes only sync metadata. Named fault hooks are inert unless an
explicit test injector is supplied.

## ADR-021 — Signed, versioned application releases

**Status:** Accepted for Phase 10C

Application manifests are canonical JSON signed with Ed25519; artifacts are bound by filename,
size, and SHA-256. Private signing keys remain only in the release environment, while devices hold
public keys selected through a signing key ID. Updates never overwrite the running tree in place:
verified archives stage atomically into versioned directories, activation persists metadata, and a
failed health check rolls back. Semantic downgrades are rejected by default. Device DB migrations
must preserve rollback compatibility; destructive schema rollback is not attempted.

## ADR-022 — Immutable remote content with local historical retention

**Status:** Accepted for Phase 10D

Published question-pack versions are immutable and database-unique by `(set_id, version)`. The
backend stores exact validated bytes under a server-generated basename; neither API callers nor
pack metadata select filesystem paths. A device downloads into a generated temporary file, checks
catalog size and SHA-256, reuses the Phase 5 schema/semantic validator, verifies internal catalog
identity, and invokes the existing atomic importer.

Remote catalog absence never deletes local content. Successful newer versions may become active
only after their complete import commits, while installed historical versions remain addressable.
In-progress attempts remain pinned to their original exact version and question order. Content
sync is explicitly invoked, bounded, and never runs in the question, answer, navigation, submit,
result, or review paths; authentication or network failure therefore cannot block assessment.

## ADR-023 — Local-first diagnostics and minimized support artifacts

**Status:** Accepted for Phase 10E

Device diagnostics use one typed, read-only snapshot and four health levels. Network checks are
explicit opt-in, because backend absence is degraded operation rather than loss of local readiness.
Support bundles exclude raw databases and assessment content; attempt identity is a short one-way
reference. Standard-library logging uses centralized redaction. A persistent audit table is
deferred until retention and access-control policy exists; a minimal safe audit event vocabulary is
logged instead.

## OPEN DECISIONS

The following are explicitly unresolved and must not be inferred from Phase 0:

- Production GUI framework (Phase 7A uses pygame-compatible APIs for prototyping only).
- Raspberry Pi OS 32-bit versus 64-bit.
- Exact touchscreen model.
- Final touchscreen resolution.
- Exact power requirements, battery/adapter design, and shutdown behavior.
- Content source and licensing.
- Whether Hindi is required and, if so, localization/font/input requirements.
- Production approval identity/provider and Pi secure credential storage.
- Whether RTC hardware is needed.
- Final production hardware.
- Software source-code license and copyright attribution.
