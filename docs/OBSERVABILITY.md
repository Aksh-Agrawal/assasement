# Observability and pilot readiness

Phase 10E is local-first. `DeviceStatus` is the versioned, machine-readable snapshot returned by
the read-only `collect_device_status()` service. It reports application/release versions, SQLite
quick-check and size, pairing presence, minimized attempt references, sync queue/last state,
installed and active pack versions, content/update state, and offline readiness.

Health levels are exact: `OK` means local health with no known action; `DEGRADED` means offline
operation remains available but a backlog or optional backend check failed; `ACTION_REQUIRED`
means pairing/credential repair is required; `ERROR` means local DB health blocks safe operation.
Stable codes are documented in `ERROR_CODES.md`.

## Commands

```powershell
python -m tools.diagnose
python -m tools.diagnose --json
python -m tools.diagnose --network --base-url http://127.0.0.1:8000
python -m tools.create_support_bundle
python -m tools.pilot_check
python -m tools.pilot_check --network --base-url http://127.0.0.1:8000
```

Default diagnostics and pilot checks make no network requests. Network mode checks liveness,
database-backed readiness/migration state, authentication, content catalog, and update endpoint.
Exit codes are `0` ready, `1` warning/degraded, and `2` blocking failure.

Logging remains standard-library logging with rotating files and the format `timestamp level
component event`. A centralized filter plus final-output formatter removes bearer/device
credentials, pairing codes, PostgreSQL URL passwords, environment database URLs, configured
secret canaries, and private-key blocks, including secrets present in exception text.

Support ZIPs contain `diagnostics.json`, a privacy manifest, version text, and bounded recent
redacted logs. They deliberately exclude SQLite files, credential files, `.env`, database URLs,
private keys, profile names/IDs, selected answers, confidence, response events, and question-pack
contents. Raw database export is not supported by default.

Administrative/security events use safe logs (`device_paired`, `device_revoked`, and
`pack_published`). A persistent backend audit table is deferred until retention/access-control
requirements exist; adding an ungoverned table would increase sensitive operational data.
