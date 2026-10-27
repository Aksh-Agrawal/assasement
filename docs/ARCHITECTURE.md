# Architecture Contract

Status: Phase 10E observability and pilot-readiness tooling implemented on the Phase 10D
device-authenticated, Phase 9C PostgreSQL backend.
Device SQLite remains the offline source of truth. FastAPI uses database-agnostic SQLAlchemy
models, Alembic owns the backend schema, and PostgreSQL is the server persistence target. SQLite
remains a backend test convenience. Raspberry Pi networking remains pending.

Diagnostics are a read-only application service over existing repository, credential-store,
content, and activation metadata. Default collection is offline-only. Optional probes flow to
FastAPI liveness/readiness and authenticated catalog/update endpoints. Support bundles serialize
only the typed minimized snapshot and centrally redacted bounded logs—never raw databases,
credentials, profiles, answers, confidence, response history, or pack contents.

## System shape

The independent application-update path is:

```text
Authenticated Backend Update Metadata
        ↓
Update Client (metadata only unless explicitly downloaded)
        ↓
Manifest Schema + Ed25519 Verification
        ↓
Artifact Size + SHA-256 Verification
        ↓
Traversal-safe Atomic Staging
        ↓
Versioned Release Activation
        ↓
Health Check
        ↓
Healthy / Metadata Rollback
```

This path never participates in application startup or assessment submission. The release signing
private key is absent from devices; only configured public verification keys are trusted.

The independent question-content path is:

```text
Backend Content Store
        ↓
Catalog API
        ↓
Authenticated Device
        ↓
Bounded Temporary Download
        ↓
Exact Size + SHA-256 Verification
        ↓
Phase 5 Schema + Semantic Validation
        ↓
Atomic Device Import
```

`app/content/` owns this one-shot flow and typed remote DTOs. It reuses the Phase 5 hashing,
validator, and importer; it never inserts remote rows directly. Catalog comparison only adds
missing exact versions and never interprets remote absence as permission to delete local data.
The existing active-version policy advances only after a successful commit. An attempt holds its
exact set version and persisted question order, so installing and activating a newer version does
not alter an in-progress assessment. No assessment screen performs a catalog request.

```text
Touchscreen ─┐
Keyboard ────┼──> Input Action Layer
GPIO Buttons ┘
                     │
                     ▼
                  UI Layer
                     │
                     ▼
             Assessment Engine
                     │
                     ▼
                Repository
                     │
                     ▼
                  SQLite


          Raspberry Pi / Device
                     │
              local persistence
                     ▼
             Device SQLite
                     │
                 HTTP sync
                     ▼
          Sync Worker + API Client
                     │
                     ▼
                  FastAPI
                     │
                  SQLAlchemy
                     │
                     ▼
                PostgreSQL

Backend SQLite remains available only for fast tests and smoke development.
```

The on-device assessment path ends at SQLite. The later synchronization path starts from committed SQLite data and runs independently.

## Layer boundaries

### Core — future `app/core/`

Core contains domain models, scoring, the assessment state machine, and monotonic timing. It is deterministic and hardware-independent.

Core must not import GUI libraries, `gpiozero`, HTTP libraries, Raspberry Pi-specific modules, SQLite, or `app.data`. It does not know how input was generated or records are stored. `app/assessment.py` is the application-orchestration boundary that coordinates the pure engine with repository calls and remains replaceable by later UI wiring.

### Repository — future `app/data/`

The repository owns SQL, schema migrations, transactions, and SQLite configuration. It exposes domain-oriented operations to core and sync code. The UI and assessment engine must never execute raw SQL.

Atomic persistence boundaries will be specified before implementation. At minimum, selecting or changing an answer must be durably committed before navigation reports success.

### UI — `app/ui/`

The UI owns screen rendering, presentation routing, display of current state, and collection of student interactions. It emits logical actions and renders state supplied by the controller/application boundary.

The UI must not contain scoring algorithms, execute SQL, or perform HTTP requests directly. Pygame-compatible rendering remains a laptop prototype choice; the production GUI framework remains open pending Phase 7B hardware benchmarks.

### Input — `app/input/`

Touch and GPIO adapters translate device-specific events into the same canonical `Action` values. Screen context determines which physical control maps to which action. Adapters do not decide scoring or directly mutate assessment data.

```text
Touch option A                 Physical button A
       │                              │
       └──────────────┬───────────────┘
                      ▼
               Action.SELECT_A
```

Phase 6A implements a pure keyboard translator and a GPIO adapter boundary that lazily imports `gpiozero` only when hardware startup is requested. The seven-button BCM plan is A=5, B=6, C=13, D=19, PREV=26, NEXT=20, and MENU=21, with pull-ups, active-low wiring, and 40 ms debounce. NEXT/CONFIRM and MENU/BACK contextual decisions are supplied through an action resolver outside the hardware adapter. Keyboard simulation proves Action translation only and is not GPIO verification.

### Sync — `app/sync/`

The sync worker reads locally committed completed records and communicates over HTTP on localhost
for development (HTTPS remains required for production). It retries with persisted bounded backoff,
reconciles proven duplicate acknowledgements, and recovers stale `syncing` rows without owning the
assessment state machine.

```text
Completed Attempt
        ↓
      SQLite
        ↓
Pending Sync Queue
        ↓
   Sync Worker
        ↓
    API Client
        ↓
 Local FastAPI Backend
        ↓
SQLAlchemy + Alembic
        ↓
PostgreSQL (backend target)
```

Assessment submission commits `completed + pending` locally and returns without invoking the sync package. The worker is explicitly triggered and processes a bounded oldest-completed-first batch. Before HTTP it persists `syncing`; success persists `synced` and `synced_at`; failure persists a category, a short diagnostic, an incremented attempt count, and a due time only for retryable failures. Permanent and authentication failures remain local but are not automatically retried. Transient failures stop being selected at the automatic retry limit; no row is deleted.

A `syncing` row older than the configured threshold is returned to `pending` on the next cycle.
Re-upload is safe because the immutable local attempt UUID is both the resource ID and
`Idempotency-Key`. A retained `failed` row can be explicitly requeued through the repository API
after credentials, payload compatibility, or support issues are repaired.

The backend's SQLAlchemy models preserve exact question-set identity/version and enforce attempt
UUID and per-attempt question uniqueness in the database. One transaction inserts an attempt and
all responses. PostgreSQL uses native UUID and timezone-aware timestamp types. Alembic owns its
schema. SQLite exercises the same ORM/service semantics in fast tests.

Network absence, timeout, authentication failure, server failure, or a stopped sync worker must never block viewing questions, answering, navigation, local submission, results, or review. SQLite is the offline source of truth for device operation.

### Device identity and authenticated sync

```text
UUIDv4 in device schema_meta
        ↓
Short-lived, single-use pairing session
        ↓
High-entropy credential (hash only on backend)
        ↓
Bearer-authenticated SyncApiClient
        ↓
Attempt linked to authenticated devices row
```

Pairing applies only to synchronization. The claim secret proves possession of the requesting
session; a credential is returned only after development approval and only once. The local
credential file is separate from assessment SQLite data and replaceable for future Pi secure
storage. Credential rows support revocation and future rotation; re-pairing issues a fresh secret
and does not reactivate an old one.

The Windows Phase 9C validation used PostgreSQL 17.11 at `localhost:5432`, service
`postgresql-x64-17`, databases `assessment_dev` and `assessment_test`, and non-superuser role
`assessment_app`. Service outage and restart testing preserved device data and backend persistence;
the retained device attempt synchronized successfully after restoration.

## Canonical action contract

The future `Action` enum contains at least:

```text
SELECT_A
SELECT_B
SELECT_C
SELECT_D

NEXT
PREV
CONFIRM

MENU
BACK

SURE
NOT_SURE
GUESSING

MARK_REVIEW

SUBMIT
```

`SELECT_A` through `SELECT_D` select the corresponding answer in question context. `SURE`, `NOT_SURE`, and `GUESSING` assign confidence to an attempted response. `NEXT` and `PREV` request navigation; `CONFIRM` accepts a pending contextual choice; `MENU` and `BACK` request contextual navigation; `MARK_REVIEW` toggles or sets a question's review marker as later specified; and `SUBMIT` requests submission.

The action name expresses intent, not a fixed GPIO pin. A touchscreen control and a physical button can emit the same action. The active screen and state decide whether an action is valid and how a physical control maps to it. Invalid actions must leave domain state unchanged and may produce UI feedback. Exact per-screen button maps are not frozen in Phase 0.

## Assessment state machine

Initial states:

```text
IDLE
  │ select a set/version
  ▼
TEST_SELECTED
  │ start or resume
  ▼
IN_QUESTION ◄─────────────────────┐
  │ select/change answer          │
  ▼                               │
AWAITING_CONFIDENCE               │
  │ choose confidence or continue │
  └───────────────────────────────┘
  │ request submit
  ▼
SUBMIT_CONFIRM
  │ confirm
  ▼
COMPLETED
  │ calculate/display
  ▼
RESULT
  │ open review
  ▼
REVIEW
```

- `IDLE`: no assessment has been selected.
- `TEST_SELECTED`: an immutable `(set_id, version)` is selected and ready to start, or a resumable attempt is identified.
- `IN_QUESTION`: one question is active. Answer selection, confidence updates, timing, review marking, and permitted navigation occur here.
- `AWAITING_CONFIDENCE`: an answer exists but no explicit confidence has been chosen. Choosing `SURE`, `NOT_SURE`, or `GUESSING` returns to `IN_QUESTION`. Continuing without a rating stores `unrated`.
- `SUBMIT_CONFIRM`: the student must explicitly confirm final submission or cancel back to the assessment.
- `COMPLETED`: the attempt is durably finalized and no assessment responses may be edited.
- `RESULT`: aggregate scoring and analytics are displayed from the finalized attempt.
- `REVIEW`: questions, selected answers, correct answers, and available explanations can be inspected without mutating the completed attempt.

Selecting, changing, clearing, or rating an answer triggers immediate durable persistence. A transition that navigates away from a question does not complete until the latest response state and accumulated time are committed. After restart, resume loads the in-progress attempt's exact `(set_id, version)`, write-once `attempt_questions` order, current responses, confidence, review flags, and accumulated timing totals. It selects the first question without a selected answer. If all questions have answers, it selects the final question and requires an explicit submit request. No implicit completion occurs. Invalid state transitions raise `InvalidTransition`; navigation beyond either boundary raises `NavigationBoundary`.

Answer selection is committed immediately with confidence `unrated`, before the confidence prompt is shown. An explicit confidence choice updates the same response row. This representation satisfies the existing domain and database invariant that every selected answer has a confidence bucket while preserving the crash-safe meaning “answer exists, explicit confidence was not supplied.” Blank persisted responses are permitted for first-shown timing and review metadata and score as skipped.

## Timer contract

Response duration uses a monotonic clock for elapsed-time measurement; it must not be calculated by subtracting system wall-clock timestamps.

- A question timer begins or resumes when that question becomes active.
- It pauses when leaving question context, including navigation to another question or a non-question screen.
- Every revisit adds a new active interval to the question's accumulated duration.
- Total response time is the sum of completed active intervals plus any current active interval at the chosen persistence boundary.
- Wall-clock timestamps may be stored separately for auditing, ordering, or synchronization.
- NTP corrections, manual clock changes, timezone changes, Wi-Fi connection, and reboot-time wall-clock corrections must not alter already accumulated durations.

A monotonic reading does not survive process or device restart. The application checkpoints accumulated time when selecting or rating an answer, changing review status, navigating, pausing, submitting, or exiting safely. Resume starts a new monotonic segment from the persisted total, so closed-process downtime is never counted. A sudden loss can only lose the uncheckpointed portion of the current active segment; it cannot corrupt or reduce previously committed timing.

## Phase 4 application flow

```text
CLI (replaceable by future UI)
  │
  ▼
AssessmentApplication ──────► Repository ──────► SQLite
  │
  ├────► AssessmentEngine
  ├────► MonotonicTimer
  └────► score_attempt
```

The application service owns orchestration order: pause timing, perform a core transition, commit through the repository, then expose success. The engine owns temporary state and transition validation only. Scoring remains a single pure function; neither the application service nor CLI duplicates it. Question order and the exact set version in SQLite are authoritative on resume.

## Phase 5 content boundary

`app/content/` owns bounded UTF-8 reading, JSON Schema validation, cross-item semantic checks, exact-byte SHA-256 verification, conversion into existing core domain models, and import orchestration. It may call the repository's cohesive atomic import method but never accesses raw SQL or repository connection internals. It has no network dependencies.

The validator and importer are deliberately separate. Validation returns a `ValidatedPack` and summary without opening SQLite. Import validates the complete file first, then passes one complete `QuestionSet` aggregate to the repository. Future download code must obtain bytes before invoking this local pipeline.

## Related contracts

- Scoring: `docs/SCORING_SPEC.md`
- Stable identifiers and versions: `docs/IDENTIFIERS.md`
- Question packs: `schemas/pack.schema.json`
- Proposed server interface: `docs/API.md`

## Implementation guardrails

These dependency rules apply to the package skeleton and future implementation:

### `core/`

Core may depend on the Python standard library and domain models or functions inside `app/core/`. It must not depend on UI code, input hardware, database modules, HTTP/network clients, or Raspberry Pi-specific packages. An AST-based unit test rejects known forbidden imports and imports across application layers.

### `data/`

Data owns SQLite configuration, migrations, SQL, transactions, row/domain mapping, integrity checks, and repository implementations. No other application layer executes raw SQL.

### `ui/`

UI calls the application service and read-only repository interfaces. It must not contain raw SQL, duplicated scoring logic, or HTTP synchronization behavior.

## Phase 7A desktop UI boundary

```text
Keyboard adapter ─┐
                  ├─> Canonical Action ─> UIController ─> AssessmentApplication
Mouse hit-test ───┘                                      │
                                                         ├─> AssessmentEngine
                                                         └─> Repository ─> SQLite

Future GPIO adapter ─────> Canonical Action (pending hardware)
Future touchscreen ──────> mouse-like hit test (pending Pi testing)
```

`app/ui/controller.py` owns presentation routing (`HOME`, `QUESTION`, `CONFIDENCE`,
`SUBMIT_CONFIRM`, `RESULT`, `REVIEW`, and `ERROR`) but does not duplicate the core assessment
state machine. It sends mutations through `AssessmentApplication`; reads needed for local profile
and set selection go through `Repository`. Renderers only draw state and return controls carrying
canonical `Action` values.

Keyboard events are translated by the existing `KeyboardInput` adapter. A mouse click is a
Phase 7A surrogate for touch: desktop coordinates are transformed into the centralized 800×480
logical space, hit-tested, and routed through the same controller. Pygame is the Phase 7A
prototype framework only. The production framework remains pending Phase 7B Raspberry Pi
benchmarking. GPIO and actual touchscreen behavior remain pending hardware testing.

Closing the window asks `AssessmentApplication.pause()` to checkpoint active monotonic timing;
it never submits. Rendering uses a frame cap, but assessment timing remains independent of frame
rate and continues to use the application service's monotonic timer.

## Phase 8A complete offline UI flow

```text
Profile → Subject → Question Set → Question ⇄ Confidence
                                  │
                                  ▼
                         Submit Confirmation
                                  │
                                  ▼
                                Result ⇄ Review
                                  │
                                  ▼
                                Profile
```

Subjects are derived from installed `QuestionSet.subject` values rather than a UI constant.
Question-set cards are filtered by the selected subject and populated from SQLite repository
aggregates. If the selected profile has an in-progress attempt, the UI shows its exact set and
answered count and resumes that attempt rather than violating the one-in-progress invariant.

`UIController` owns only presentation state such as selected list indices, current screen, review
position, and full-text page. It delegates start, resume, answer, confidence, navigation, review
marking, pause, submission, scoring, and completed review to `AssessmentApplication`. The
application service and engine continue to enforce immutable completion and exact-version resume.

### `input/`

Input adapters will translate device or touch events into canonical `Action` values. The canonical action module is platform-independent and contains no GUI, GPIO, database, or network integration.

### `sync/`

Sync is implemented as an explicitly invoked independent concern using the local FastAPI backend.
It is never required for assessment operation and is not yet a scheduled/background service.

## Persistence transaction policy

SQLite connections are explicitly owned and closed by a repository instance; there is no module-global connection. Every write operation uses a short explicit transaction and rolls back on failure. Transactions never span student think-time.

Multi-row invariants use a single transaction. In particular, question-set metadata plus questions can be imported atomically, attempts can be created with their fixed question order atomically, full attempt order is saved atomically, and attempt completion updates status, completion timestamp, duration, score, and pending-sync state in one commit.

Each new connection enables WAL, `synchronous=FULL`, foreign keys, and a 5000 ms busy timeout. Wall-clock timestamps are normalized to UTC ISO-8601 text by the data layer. These timestamps are audit metadata only; Phase 4 duration calculations use an injectable monotonic clock.
