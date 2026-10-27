# SQLite Schema and Migration Contract

Status: Phase 5 persistence contract, preserving the Phase 3 schema.

## Connection configuration

Every repository connection is file-backed at a caller-supplied `Path` and enables:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA wal_autocheckpoint = 1000;
```

No production Raspberry Pi path is selected in Phase 3. There is no module-global connection.

## Migrations

Migration files live in `app/data/migrations/` and use zero-padded numeric prefixes. They are applied in numeric order. Each migration and its `schema_meta.schema_version` update runs in one explicit transaction. Reopening a current database is a no-op.

Repository startup runs SQLite integrity validation before normal writes. A failure is surfaced as
`LOCAL_DATABASE_ERROR`; the file is never silently deleted or recreated. WAL plus
`synchronous=FULL` protects committed transactions, while foreign-key checks prevent orphaned
responses, attempt order rows, and response events. Online snapshots use SQLite's backup API.

Applied migrations are immutable: never edit a released/applied migration. Add the next numbered file for every schema change.

## Tables

- `schema_meta`: key/value metadata including schema version, device ID, and creation time.
- `profiles`: stable profile identity, optional server/PIN material, creation timestamp, and soft deletion timestamp.
- `question_sets`: immutable `(id, version)` metadata, marking JSON, content hash, download timestamp, and active-version flag. A partial unique index permits only one active version per logical set.
- `questions`: exact-version question content keyed by `(set_id, set_version, id)`, with unique position inside the version. Options are serialized as JSON in the data layer.
- `attempts`: device-generated attempt identity, profile/set references, lifecycle fields, score, and persistence-only synchronization state. Migration `0002_sync_retry.sql` adds `next_sync_at`, `sync_started_at`, and the constrained `sync_error_kind` used for durable retry scheduling and stale-work recovery. A partial unique index permits one in-progress attempt per profile.
- `attempt_questions`: write-once fixed question order, keyed by `(attempt_id, position)` with one occurrence of each question per attempt.
- `responses`: current/final state keyed uniquely by `(attempt_id, question_id)`. Upserts retain the original response ID.
- `response_events`: append-only answer history; it is not the current scoring source of truth.
- `settings`: non-secret key/value application settings.

## Timestamp and duration rules

Application timestamps are stored as UTC ISO-8601 text. The Raspberry Pi wall clock may be inaccurate while offline, so timestamps are auditing/synchronization metadata rather than elapsed-time authority. Phase 4 calculates response and attempt durations from a monotonic clock and persists accumulated milliseconds.

## Transaction policy

Writes are short and explicit. Failures roll back. Aggregate imports, attempt-plus-order creation, full order saves, and attempt completion are atomic. No transaction remains open while waiting for student input.

For a Phase 5 active pack import, the repository inserts inactive metadata, inserts every question, deactivates the prior active version, and activates the new version inside one transaction. A failure at any step removes the new metadata/questions and restores the old active flag through rollback. `content_hash` stores the lowercase exact-byte SHA-256 and `downloaded_at` stores UTC installation time for local imports.
