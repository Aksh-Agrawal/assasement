# Remote content synchronization

Phase 10D adds an explicitly invoked, laptop-testable content path. It does not add a scheduler,
daemon, Wi-Fi setup, teacher UI, object storage, CDN, or Raspberry Pi dependency.

## Publishing

Set `DATABASE_URL` for the migrated backend and optionally set `CONTENT_STORAGE_PATH` (default
`backend/runtime/content`). Apply Alembic, then publish from the repository root:

```powershell
python -m alembic -c backend/alembic.ini upgrade head
python -m backend.tools.publish_pack content/sample_biology.json
```

Publishing reads exact bytes and reuses `app.content.validator`, including the normative
`schemas/pack.schema.json` and semantic checks. SHA-256 is calculated over those exact bytes.
Metadata and the server-generated artifact basename are committed together. The database enforces
`UNIQUE(set_id, version)`: publishing identical bytes is idempotent, while different bytes for an
existing version are rejected. API input never supplies a storage path.

## Device pipeline

```text
Authenticated catalog
  → compare exact local set/version rows
  → select a configured bounded batch
  → generated temporary filename
  → enforce catalog size and hard maximum while streaming
  → verify final exact size
  → verify catalog SHA-256 with the Phase 5 helper
  → run Phase 5 JSON/schema/semantic validation
  → check internal set_id/version/question_count against catalog
  → call the Phase 5 atomic importer
  → activate only after commit when the version advances
```

Run one cycle after pairing:

```powershell
python -m tools.sync_content --base-url http://127.0.0.1:8000
python -m tools.sync_content --base-url http://127.0.0.1:8000 --dry-run
```

The client uses the existing Phase 10A credential file and configured connect/read timeouts. It
never prints the bearer token. `--limit` bounds downloads per cycle. Dry-run fetches and compares
the catalog but neither downloads nor imports.

## Version and failure policy

Exact `(set_id, version)` is canonical. Every published version may appear in the catalog, and the
device keeps all installed historical versions. Remote absence never deletes local content.
Installing a newer version can make it active for new selection only after the transaction commits.
Attempts persist their exact version and question order, so an in-progress attempt resumes against
unchanged historical questions even after a newer version becomes active.

Partial, truncated, oversized, hash-mismatched, metadata-mismatched, or invalid files never reach
the importer. Import faults roll back the entire new version. Temporary files are removed on
handled completion/failure; a process killed after download may leave only an ignored temp file,
never partial database state. Structured results distinguish installed, already present, download,
hash, validation, import, authentication, and network outcomes. Content failure is non-blocking.

Installed question content remains fully usable when the backend or network is unavailable.
