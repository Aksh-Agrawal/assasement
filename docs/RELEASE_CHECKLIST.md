# Phase 10F release checklist

This is the repeatable laptop-side release and pilot gate. It deliberately does not claim
Raspberry Pi hardware readiness and does not configure GPIO, systemd, displays, touchscreens,
Wi-Fi, or boot behavior.

## Commands

The default is the safe offline mode:

```powershell
python -m tools.release_check
python -m tools.release_check --offline
```

It runs Ruff, device/core tests, fresh SQLite migration and integrity checks, the assessment and
restart/resume flows, local content validation and pinning, signed-update and tamper checks,
fault/recovery tests, diagnostics, support-bundle redaction, and the existing pilot check. It does
not require or probe FastAPI, PostgreSQL, or the network.

Run the full laptop gate before a pilot handoff:

```powershell
python -m tools.release_check --full
```

Full mode adds temporary local FastAPI integration servers and the real PostgreSQL integration
suite. It never starts, stops, or modifies Windows services. Existing test harnesses own and clean
up temporary HTTP servers, device databases, credentials, packs, and downloads.

## Required environment for full mode

Both `DATABASE_URL` and `TEST_DATABASE_URL` must exist. Their values are never printed or written
to the report. `TEST_DATABASE_URL` must use PostgreSQL and its database name must contain `test`;
the runner refuses destructive migration/integration work otherwise. Use a dedicated disposable
test database, not production or a shared development database. PostgreSQL must already be
running and reachable.

The full PostgreSQL suite validates the connection, Alembic head, schema constraints, pairing and
authentication, authenticated attempt synchronization, idempotency, lost-ack recovery, controlled
database-unavailable behavior, catalog/download/import, v1-to-v2 content upgrades and attempt
pinning. The update endpoint is checked through the existing authenticated backend test path.

## Results and evidence

Every check is one of:

- `PASS`: the check ran and met its contract.
- `WARN`: an optional/degraded check was unavailable or needs attention.
- `FAIL`: a required check failed; overall readiness is `FAIL`.
- `SKIP`: the check is outside the selected mode and does not make offline mode fail.

Exit codes are `0` for PASS, `1` for PASS with warnings/degraded readiness, and `2` for FAIL.
Reports are written to the gitignored paths:

```text
artifacts/release-readiness.json
artifacts/release-readiness.md
```

The JSON report records UTC timestamp, app/backend versions, mode, OS/Python metadata, overall
status, per-group checks, test counts, durations, and explicit `hardware_status: PENDING`. Reports
are passed through the Phase 10E redactor and do not contain database URLs, device credentials, or
passwords.

## Software readiness matrix

| Area | Status after successful command | Evidence |
|---|---|---|
| Offline assessment | PASS | isolated smoke, engine, UI/controller, resume tests |
| SQLite durability | PASS | fresh migrations, WAL/integrity, persistence and fault suites |
| Local content | PASS | valid/invalid packs, atomic import, version pinning |
| Signed updates | PASS | signature/hash/compatibility and tamper regression suite |
| Diagnostics/support | PASS | JSON validation, support-bundle exclusion/redaction, pilot check |
| FastAPI backend | PASS in full mode | backend health/migration integration tests |
| PostgreSQL | PASS in full mode | protected real PostgreSQL integration suite and Alembic head |
| Authentication | PASS in full mode | pairing, claim, protected request, invalid credential, revocation |
| Attempt sync | PASS in full mode | real HTTP/PostgreSQL sync, idempotency, lost-ack recovery |
| Remote content | PASS in full mode | authenticated catalog/download/import and v1-to-v2 scenario |
| Update API | PASS in full mode | authenticated metadata and artifact endpoint test |
| Pi display/touch | PENDING | Phase 6B/7B/8B hardware validation |
| GPIO | PENDING | physical hardware verification |
| Pi network/credentials | PENDING | on-device validation |
| Pi update activation | PENDING | real activation and reboot test |
| Boot/systemd/power/thermal | PENDING | hardware acceptance work |

## Release record checklist

- Run the offline command on every normal CI build.
- Run full mode locally against the designated PostgreSQL test database before pilot packaging.
- Attach both generated reports to the pilot/release record.
- Confirm all required software checks are PASS and review WARN entries.
- Keep Raspberry Pi hardware readiness marked PENDING until the hardware acceptance phases finish.

PostgreSQL CI is intentionally local-only for now. The existing CI has no PostgreSQL service, and
the normal workflow runs the deterministic offline subset so it stays stable and safe.
