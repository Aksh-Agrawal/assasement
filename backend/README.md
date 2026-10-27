> **TEMPORARY — being migrated to assasement-cloud repository.**
> Retained until independent cloud validation. Device runtime and Pi deployment do not require this directory.

# Phase 10A paired-device backend

The FastAPI backend accepts completed attempts from the existing Phase 9A device client. Device
SQLite remains the offline source of truth. PostgreSQL is the target backend database; SQLite is
retained only as a zero-setup backend smoke/test convenience.

## Verified Windows PostgreSQL environment

Phase 9C was validated on 2026-10-18 with:

```text
PostgreSQL: 17.11
Host/port: localhost:5432
Windows service: postgresql-x64-17
Development database: assessment_dev
Test database: assessment_test
Application role: assessment_app (non-superuser)
Alembic revision: 20261019_03
```

The development database was migrated with `python -m alembic -c backend/alembic.ini upgrade
head`. A fresh test migration and repeated `upgrade head` both succeeded against PostgreSQL. The
real PostgreSQL suite command is `python -m pytest backend/tests -m postgres`; the verified result
was `3 passed, 0 failed, 0 skipped`. Passwords are intentionally omitted.

## Install

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,backend]"
```

This installs FastAPI, SQLAlchemy 2.x, Alembic, Uvicorn, and the single PostgreSQL driver
`psycopg[binary]`. The backend does not load `.env` automatically; copy `backend/.env.example` to
an ignored `.env` for reference and set values in the process environment or deployment secret
manager.

## SQLite quick development mode

With no `DATABASE_URL`, the backend uses ignored `backend/dev.db` and creates the SQLite schema at
application startup. This mode is for quick development, fast tests, and CI without PostgreSQL:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
python -m pytest backend/tests -m "not postgres"
```

Tests create isolated temporary SQLite files and do not use `backend/dev.db`.

## PostgreSQL development mode

Docker is not required. On Windows, install PostgreSQL using the official PostgreSQL installer and
include both the server and command-line tools. Confirm `psql --version` and `pg_isready` work.
Development requires a running server, `psql`, a dedicated database, a non-superuser application
role, and a locally chosen password.

Connect once as a PostgreSQL administrator and create dedicated development and test databases.
Replace the example password locally; never commit it:

```sql
CREATE ROLE assessment_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD 'CHANGE_ME';
CREATE DATABASE assessment_dev OWNER assessment_app;
CREATE DATABASE assessment_test OWNER assessment_app;
```

The database owner has the schema privileges needed by Alembic. Normal application execution must
use `assessment_app`, not the `postgres` superuser. API bearer credentials and PostgreSQL
credentials are separate secrets.

Configure the development database and apply migrations from the repository root:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://assessment_app:CHANGE_ME@localhost:5432/assessment_dev"
python -m alembic -c backend/alembic.ini upgrade head
python -m alembic -c backend/alembic.ini current
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

PostgreSQL tables are never created automatically by FastAPI startup. Run Alembic first. The
application uses SQLAlchemy's normal default PostgreSQL connection pool with `pool_pre_ping`; no
PgBouncer or speculative pool tuning is configured. Initial PostgreSQL connection establishment is
bounded to five seconds so an outage becomes a retryable API failure before the device HTTP read
timeout.

## PostgreSQL integration tests

PostgreSQL tests are opt-in and reject a URL whose database name does not contain `test`. They
reset the Phase 9C schema and data, so never point `TEST_DATABASE_URL` at development or production:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://assessment_app:CHANGE_ME@localhost:5432/assessment_test"
python -m pytest backend/tests -m postgres
```

The suite migrates an empty test schema, repeats `upgrade head`, uses the real device Repository,
SyncWorker and SyncApiClient through a real Uvicorn socket, and checks persistence, idempotency,
conflict, concurrent duplicate handling, restart persistence, lost acknowledgements, and connection
failure recovery.

Fast tests remain separate:

```powershell
python -m pytest backend/tests -m "not postgres"
```

## Migration policy

Revision `20261018_01` creates attempt storage. Forward revision `20261018_02` adds devices,
pairing sessions, hash-only credentials, and authenticated attempt ownership. Revision
`20261019_03` adds immutable question-pack catalog metadata and `(set_id, version)` uniqueness.
Production policy is
forward-only: test/local downgrades exist
for safe schema recreation but production rollback should use a reviewed forward repair migration
and backup/restore plan.

## Data rules

- Device attempt IDs use SQLAlchemy `Uuid`: native PostgreSQL UUID and compatible SQLite storage.
- Request timestamps must be timezone-aware. PostgreSQL stores them as `TIMESTAMP WITH TIME ZONE`;
  the application creates audit timestamps in UTC.
- `device_attempt_id` and `(attempt_id, question_id)` are database-unique.
- Attempt and response inserts share one transaction.
- Response foreign keys use `ON DELETE RESTRICT`; immutable history is not cascade-deleted.
- The SHA-256 algorithm remains canonical JSON over every validated request-body field.
- Indexes cover device attempt identity, profile, question-set ID/version, and creation time.

Pair with `python -m tools.pair_device --base-url http://127.0.0.1:8000`, approve using the
**DEVELOPMENT / TEST ONLY** command `python -m tools.approve_pairing <code>`, and revoke using
`python -m tools.revoke_device <device-uuid>`. Raw credentials are never stored in PostgreSQL or
printed by the pairing CLI.

## Development question content

`CONTENT_STORAGE_PATH` configures an ignored artifact directory and defaults to
`backend/runtime/content`. After applying migrations, publish a validated pack and start the API:

```powershell
python -m backend.tools.publish_pack content/sample_biology.json
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

The publisher reuses the device Phase 5 validator and exact-byte SHA-256 implementation. Catalog
and pack download require the existing device bearer credential. No admin HTTP endpoint or web UI
is provided.
