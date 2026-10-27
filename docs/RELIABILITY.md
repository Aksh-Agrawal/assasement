# Reliability and recovery contract

Phase 10D retains the Phase 10B durability guarantees on file-backed SQLite and the authenticated
FastAPI/PostgreSQL paths. Local assessment work never waits for the network.

## Durability and transaction boundaries

SQLite uses WAL, `synchronous=FULL`, foreign keys, a five-second busy timeout, and explicit
`BEGIN IMMEDIATE` write transactions. Response state, completion state, pack imports, sync-state
transitions, and migrations commit atomically. A fault before commit rolls the transaction back; a
fault after commit leaves the new state durable. Completion writes status, timestamp, duration,
score, and pending-sync state in one update.

Resume always uses the persisted question order and exact question-set version. A selected answer
whose confidence flow was interrupted remains `unrated`; resume chooses the first unanswered
question deterministically, and the durable answer remains available for navigation/review.

## Sync recovery

Completed attempts are never deleted for sync failures. Network, 5xx, and database outages are
transient and use deterministic bounded backoff. Authentication failures stop automatic retry and
preserve the attempt. A `syncing` lease older than the configured threshold returns to `pending`.
Attempt UUID plus backend uniqueness makes a retry after a lost acknowledgement idempotent.
`Repository.requeue_failed_attempt()` is the explicit immediate/manual retry path.

If pairing is approved but the client exits before claim, Phase 10B requests a new pairing session
after restart; claim secrets are intentionally memory-only. Missing or malformed local credential
storage means unpaired sync, not an assessment failure.

## Integrity, backup, and restore

Repository startup checks SQLite integrity before normal use. Failure raises
`LOCAL_DATABASE_ERROR`; the database is never deleted, reset, or overwritten automatically.
Online backups use `sqlite3.Connection.backup`. The explicit restore command validates the source,
refuses silent overwrite, and creates a timestamped safety copy when `--overwrite` is supplied:

```powershell
python -m tools.restore_local_db backup.db var/assessment-device.db --overwrite
```

Arbitrary corruption is detected, not automatically repaired.

## Failure matrix

| Failure | Expected behavior | Data lost? |
|---|---|---|
| Crash before answer commit | Previous durable response resumes | Only uncommitted input |
| Crash after answer commit | Answer, timing, confidence state, and review state resume | No |
| Crash before completion commit | Attempt remains in progress | No committed data |
| Crash after completion commit | Completed result remains pending sync | No |
| App closes during navigation | Persisted order and answers drive deterministic resume | No |
| Network/backend/PostgreSQL unavailable | Local attempt remains retryable | No |
| Lost server acknowledgement | Idempotent retry becomes synced | No |
| Credential missing, malformed, or revoked | Pairing/authentication required for sync | No |
| Stale syncing lease | Returned to pending after threshold | No |
| Invalid/crashed pack import | Whole new version rolls back; old active pack remains | No |
| Interrupted or oversized content download | Generated temporary file is discarded; importer is not called | No |
| Content SHA-256 or schema mismatch | New version is rejected; installed versions are unchanged | No |
| Content credential revoked/backend offline | Sync reports a structured failure; assessments continue locally | No |
| Crash after content download, before import | SQLite is unchanged; abandoned temp data may be cleaned later | No |
| SQLite corruption | Controlled failure; no automatic writes/reset | No |

## Diagnostics and logs

`python -m tools.diagnose` performs no network request and reports database accessibility,
integrity, schema version, pending/failed counts, device identity, credential presence, and backend
configuration without printing secrets or response payloads. UI logs rotate at 1 MB with three
backups. Logs contain lifecycle IDs and categories, never bearer credentials, pairing secrets,
answers, PostgreSQL URLs, or passwords.
