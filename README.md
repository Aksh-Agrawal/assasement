# Assessment device repository

This repository runs the offline-first Raspberry Pi assessment device. Cloud source
in `backend/` is **TEMPORARY — being migrated to assasement-cloud repository**.
It is excluded from Pi deployment and is not a device runtime dependency.

Install the device with `python -m pip install -e ".[gui]"` (add `dev` for tests).
Configure `ASSESS_API_URL` and device paths through the environment; see
[.env.example](.env.example). With no API URL, local assessment remains available.
Run `python -m app.ui.app --fullscreen` and optionally run
`python -m app.sync.service` in a separate process for periodic uploads/heartbeat.

The [migration map](docs/DEVICE_MIGRATION_MAP.md) records ownership and temporary
files. The [device/cloud contract](docs/DEVICE_CLOUD_CONTRACT.md) defines the HTTP
boundary for the independent cloud repository. Existing development backend
instructions below are transitional and require separate cloud dependencies.

# Offline-First Student Assessment Device

An offline-first practice-assessment application intended for a Raspberry Pi Zero 2 W with a small touchscreen and physical buttons. Installed Biology and Chemistry assessments must remain usable without internet access; networking and synchronization are later-phase concerns.

## Current phase

Current implementation phase: Phase 10F — final release/pilot regression automation

This repository provides the offline device application plus a focused FastAPI attempt-sync
backend. The device database remains SQLite and is never replaced: assessments continue to work
offline. SQLAlchemy and Alembic now provide the PostgreSQL backend persistence path, while SQLite
remains available for fast backend tests and smoke development.

Current status:

- Keyboard input simulation: implemented and laptop-tested.
- Mouse input: implemented as a future-touch surrogate through the same Action/controller path.
- Current GUI framework: pygame API via the `pygame-ce` package — Phase 7A prototype only.
- Production GUI framework: **PENDING PHASE 7B RASPBERRY PI BENCHMARK**.
- Phase 6B Raspberry Pi hardware verification: pending.
- Phase 7B Raspberry Pi GUI benchmarking: pending.
- Physical GPIO verification: pending.
- Touchscreen hardware validation: pending.
- Local FastAPI attempt-upload backend: implemented and laptop-tested.
- PostgreSQL driver, ORM path, Alembic migration, and opt-in integration suite: implemented.
- Live PostgreSQL 17.11 validation on Windows: complete.
- Verified databases: `assessment_dev` and isolated `assessment_test` on `localhost:5432`.
- Verified application role: non-superuser `assessment_app`.
- Pi networking and Wi-Fi validation: pending.
- Device UUID, pairing, credential storage, authenticated sync, and revocation: implemented.
- Deterministic crash/fault campaign, backup/restore, diagnostics, and rotating logs: implemented.
- Ed25519-signed manifests, verified staging, simulated activation, and rollback: implemented.
- Immutable backend pack catalog, authenticated exact-byte download, and safe device import: implemented.
- Real PostgreSQL → FastAPI → authenticated device → SQLite v1/v2 content flow: verified.
- Typed health snapshots, redacted support bundles, readiness checks, and pilot check: implemented.
- One-command offline/full release readiness reports and CI gate: implemented.
- Wi-Fi settings UI: pending.

## Laptop sync tooling

Run the deterministic recovery campaign and safe local diagnostics:

```powershell
python -m pytest -m fault
python -m tools.diagnose
```

See `docs/RELIABILITY.md` for transaction boundaries, crash semantics, failure matrix, and explicit
restore procedure.

Pilot support commands:

```powershell
python -m tools.diagnose
python -m tools.diagnose --network --base-url http://127.0.0.1:8000
python -m tools.diagnose --json
python -m tools.create_support_bundle
python -m tools.pilot_check
python -m tools.pilot_check --network --base-url http://127.0.0.1:8000
```

Final software release checks (offline is the safe default):

```powershell
python -m tools.release_check
python -m tools.release_check --offline
python -m tools.release_check --full
```

The commands write redacted JSON and Markdown evidence under `artifacts/`. Full mode requires
`DATABASE_URL` and a dedicated PostgreSQL `TEST_DATABASE_URL` whose database name contains
`test`; it does not start or modify system services. See `docs/RELEASE_CHECKLIST.md`.

Default diagnostics and pilot checks are offline-only. See `docs/OBSERVABILITY.md`,
`docs/ERROR_CODES.md`, and `docs/SUPPORT_RUNBOOK.md`. Support bundles never include the device
database, credential file, student answers, or question content.

Remote content development commands (after backend migration and device pairing):

```powershell
python -m backend.tools.publish_pack content/sample_biology.json
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
python -m tools.sync_content --base-url http://127.0.0.1:8000
python -m tools.sync_content --base-url http://127.0.0.1:8000 --dry-run
```

`CONTENT_STORAGE_PATH` selects the ignored development artifact directory. See
`docs/CONTENT_SYNC.md` for immutable versions, integrity checks, atomic import, active-version
behavior, and offline guarantees.

Signed-update development commands:

```powershell
python -m tools.generate_update_keys
python -m tools.build_release --version 0.2.0 --private-key var/update-keys/dev.update-private.pem
python -m tools.verify_release dist/update/update-manifest.json dist/update/update-manifest.sig dist/update/assessment-device-0.2.0.tar.gz --public-key var/update-keys/dev.update-public.pem
python -m tools.simulate_update dist/update/update-manifest.json dist/update/update-manifest.sig dist/update/assessment-device-0.2.0.tar.gz --public-key var/update-keys/dev.update-public.pem --current-release <existing-release-directory>
python -m pytest -m update
```

The private signing key is release-environment-only and must never be copied to a device. See
`docs/UPDATES.md` for verification, staging, simulation, rollback, and migration policy.

Completed attempts are committed locally as pending and assessment execution never imports or calls
the HTTP client. Inspect eligible deterministic payloads without requests or state mutation:

```bash
python -m tools.sync_once --db var/assessment-device.db --dry-run
```

Run one bounded development upload cycle against the local backend:

```bash
python -m tools.sync_once --db var/assessment-device.db --base-url http://localhost:8000
```

The client reads its paired credential from the ignored `var/device_credentials.json`. With no
credential, it performs no request and reports `PAIRING_REQUIRED`. Scheduling/systemd and
Raspberry Pi network validation remain pending.

## Local development backend

Install device, test, GUI, and backend dependencies:

```powershell
python -m pip install -e ".[dev,gui]"
python -m pip install -r backend/requirements.txt
```

Start FastAPI from the repository root:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

In a second terminal request pairing; in a third, approve the displayed six-digit code:

```powershell
python -m tools.pair_device --base-url http://127.0.0.1:8000
python -m tools.approve_pairing 483921

# after pairing
python -m tools.sync_once --db var/assessment-device.db --base-url http://127.0.0.1:8000
```

Run fast isolated backend tests with `python -m pytest backend/tests -m "not postgres"`. Configure
the dedicated `TEST_DATABASE_URL` and run `python -m pytest backend/tests -m postgres` for real
PostgreSQL coverage. See `backend/README.md` for native setup and migration commands. The approval
and revocation CLIs are development/test-only; no admin dashboard is part of Phase 10A.

The verified Phase 9C PostgreSQL result is `3 passed, 0 failed, 0 skipped`. It covers fresh and
repeat migration, real schema constraints, transaction rollback, device-client synchronization,
idempotency, conflict, lost acknowledgement, concurrent duplicates, backend restart, and database
outage recovery. Device tests remain independent of both FastAPI and PostgreSQL.

## Requirements

- Python 3.11 or later
- Git

## Setup

Create a virtual environment from the repository root:

```bash
python -m venv .venv
```

Activate it on Unix or macOS:

```bash
source .venv/bin/activate
```

Activate it in Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the project and development tools:

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev,gui]"
python -m pip install -r backend/requirements.txt
```

Run the development entry point:

```bash
python -m app.main
```

## Complete offline desktop UI

First install the sample pack into the default development database if it is not already
installed:

```bash
python -m tools.import_pack content/sample_biology.json --db var/assessment-device.db
```

Launch the separately packaged GUI entry point:

```bash
python -m app.ui.app
```

Use `--db PATH` for another SQLite database. Startup checks lead to the local profile picker,
PIN unlock when applicable, and Home. Add a local profile explicitly with your chosen name.
Practice follows Subject → Chapter → Question Set → Test Setup. Home offers an interrupted
attempt with its original pack version and saved answers. Settings opens the device console.
See [the device UI flow](docs/UI_FLOW.md) for routes, input mappings and integration limits.

Answer with A–D, select confidence with S/N/G (or Enter for Unrated), navigate with the arrow
keys, toggle review with R, request submission with T, and use Escape for Back. Enter confirms
selection and opens the full-content view on question/review screens. At submission confirmation,
Enter continues the test; T or the labelled touch target submits. F12 saves a development
screenshot under ignored `var/screenshots/`.

The window renders one 800×480 logical surface and scales it to the resizable desktop window.
This target is an unverified prototype resolution, not a statement about final display hardware.
`--base-url URL` configures network services; `--fullscreen` and `--gpio` enable optional device
integration. Local assessment does not require a server. To render previews without touching
student data, run `python -m tools.ui_smoke`; previews use a temporary real database and sample pack.

## Offline CLI assessment

Install the development fixture once in a development database:

```bash
python -m tools.cli_test --seed-sample
```

After that, run the same database without reseeding:

```bash
python -m tools.cli_test
```

The default development database is `var/assessment-device.db`. Override it with
`--database PATH` or the `ASSESSDEV_DATABASE` environment variable. Seeding is explicit,
idempotent, and never resets existing data.

Choose a profile and installed set, then use `A`–`D` to answer and select Sure, Not Sure,
Guessing, or Unrated confidence. `N` and `P` navigate, `R` toggles review, `S` requests the
two-step submission flow, and `Q` checkpoints timing and exits with the attempt in progress.
The next run detects that attempt and can resume it. Completion displays Phase 2 score and
confidence analytics and offers a read-only per-question review.

## Question-pack tooling

Validate a UTF-8 JSON pack without changing a database:

```bash
python -m tools.validate_pack content/sample_biology.json
```

Atomically install a validated version into a development database and make it active:

```bash
python -m tools.import_pack content/sample_biology.json --db development.db
```

Add `--dry-run` to perform parsing, schema validation, semantic validation, domain conversion,
and SHA-256 calculation without opening or changing SQLite. Add `--expected-sha256 HEX` when
the exact-byte digest is known. Imports reject an already-installed `(set_id, version)` instead
of replacing it. See `docs/QUESTION_PACKS.md` for the lifecycle and safety rules.

## Hardware bring-up preparation

Run the laptop keyboard diagnostic:

```bash
python -m tools.hardware.test_keyboard_input
```

The Pi-side utilities are prepared but have not been hardware-verified:

```bash
python -m tools.hardware.monitor_pi
python -m tools.hardware.monitor_pi --watch --interval 5
python -m tools.hardware.test_buttons
```

Use `docs/PI_SETUP.md` for imaging, deployment, display/touch checks, power, and thermal
procedures. Record only observed values in `docs/measurements.md` and track physical
acceptance in `docs/HARDWARE_ACCEPTANCE.md`.

## Quality checks

```bash
ruff check .
pytest
```

These checks require no internet, Raspberry Pi hardware, PostgreSQL server, or production SQLite files after dependencies are installed.

## Architecture

The package boundaries follow the Phase 0 architecture contract:

```text
core    → pure assessment domain logic
data    → SQLite, migrations, and repository implementation
input   → canonical actions, keyboard adapter, and planned GPIO adapter
ui      → controller, logical layout, and Phase 8A offline desktop presentation
sync    → one-shot upload worker, retry policy, payloads, and isolated HTTP client
auth    → local and session authentication
system  → operating-system integration
```

Device `data` owns offline SQLite, migrations, transactions, and row/domain mapping. `core` remains
independent. Backend SQLAlchemy is database-agnostic, Alembic owns PostgreSQL schema changes, and
PostgreSQL is the server persistence target. Backend SQLite is only a fast test/development
convenience. `sync` remains explicitly triggered and is not required for assessment execution.
See `docs/ARCHITECTURE.md` for the binding dependency rules.

## Local database

The repository always receives a database `Path`; laptop tests use temporary file-backed databases and no production Raspberry Pi path is assumed. SQLite runs in WAL mode with `synchronous=FULL`, foreign keys enabled, and a 5000 ms busy timeout. See `docs/DB_SCHEMA.md` for schema and migration details.

## Phase 0 contracts

The specifications under `docs/`, the question-pack schema, sample content, and scoring vectors are preserved as the source of truth for future phases.


## Hosted connection readiness

See [Cloud connection](docs/CLOUD_CONNECTION.md) for the configuration-only future
connection procedure and [Hosted acceptance](docs/HOSTED_ACCEPTANCE_TEST.md) for
the pending physical-Pi golden tests. Run `python -m tools.cloud_check` for a safe
connection report; an empty API URL is an expected waiting state.
