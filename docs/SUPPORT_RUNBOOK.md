# Pilot support runbook

Start with `python -m tools.diagnose --json` and `python -m tools.pilot_check`. Create a redacted
bundle with `python -m tools.create_support_bundle`; never request credential files or raw SQLite.

## Device will not sync

For `SYNC-001` verify backend reachability/PostgreSQL readiness, then retry. For `SYNC-002` inspect
pending/failed/auth-required counts. Completed attempts remain local.

## Device not paired or credential rejected

`AUTH-001` means pair the device. `AUTH-002` means the stored credential was rejected/revoked;
re-pair through Phase 10A. Never copy tokens into tickets or logs.

## Content update failed

For `CONTENT-001`, keep using installed content. Check catalog authentication, storage presence,
declared size, SHA-256, and Phase 5 validation. Do not delete historical packs or migrate attempts.

## Software update failed

For `UPDATE-001`, inspect staged/current/previous versions and signature verification. A failed
health check should leave or restore the last healthy release. Never copy private signing keys.

## DB health error

For `DB-001`, stop writes, preserve the original database, and use the documented integrity and
backup/restore process. Never automatically reset a corrupt database.

## Backend or PostgreSQL unavailable

`BACKEND-001` is degraded, not an offline-assessment failure. Check `/health`, then `/ready` for
safe database and Alembic-head status. Restore the backend independently; installed content and
local assessment remain available.
