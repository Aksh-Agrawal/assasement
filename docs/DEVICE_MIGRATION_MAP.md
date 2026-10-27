# Device/cloud migration map

Audit recorded before implementation changes (2026-10-27).

| Major package / files | Classification | Separation action |
| --- | --- | --- |
| app/core, app/assessment.py | KEEP_DEVICE | Preserve engine, scoring, timer, resume and models. |
| app/ui, app/input, app/system | KEEP_DEVICE | Preserve pygame UI, canonical Actions, touch/keyboard/GPIO and Wi-Fi adapters. |
| app/data and SQL migrations | KEEP_DEVICE | Local SQLite, profiles/PIN, pending attempts and device settings. |
| app/auth | KEEP_DEVICE | Identity, local credential storage and HTTP pairing; no approval logic. |
| app/content | KEEP_DEVICE | Catalogue client, bounded download, hashing, validation and atomic local import. |
| app/sync | KEEP_DEVICE | Stable attempt payloads, HTTP upload, local acknowledgements and retry worker. |
| app/update | KEEP_DEVICE | Signed manifest parsing, HTTP download, verification, staging and activation. |
| app/config.py, app/diagnostics.py, app/main.py, app/version.py, app/faults.py | KEEP_DEVICE | Central configuration, local diagnostics and application entry points. |
| schemas, content, tests/fixtures/packs | SHARED_CONTRACT | Device owns validation copies of pack/update schemas and local content; copy versioned formats to cloud, never import cloud code. |
| HTTP request/response concepts in app/auth/pairing.py, app/content/catalog.py, app/sync/payloads.py, app/update/manifest.py | SHARED_CONTRACT | Retain existing wire formats; document and expose device contracts. |
| backend/app, backend/alembic, backend/tools, backend/tests, backend/pyproject.toml | TEMPORARILY_KEEP | MOVE_CLOUD destination: assasement-cloud. Retain source until cloud validation; exclude from Pi deployment. |
| tools/approve_pairing.py, tools/revoke_device.py | TEMPORARILY_KEEP | MOVE_CLOUD admin tools; currently import backend directly. Exclude from device distributions/deployment. |
| tools/release_check.py full mode | TEMPORARILY_KEEP | Cloud integration checks; offline mode must also work without backend files. |
| tools other than cloud admin helpers | KEEP_DEVICE | Local import, diagnosis, pairing, sync, update, release and support tooling. |
| scripts, .github/workflows | KEEP_DEVICE | Pi deployment and device CI; add systemd examples. |
| tests/unit, integration, content, update, faults, observability, release | KEEP_DEVICE | Most device tests use mock transports/local fixtures; one fault test has backend integration imports (see below). |
| backend/tests/test_end_to_end.py, test_content_end_to_end.py, test_postgresql.py | TEMPORARILY_KEEP | Tests intentionally couple server and device; move with cloud integration suite. |
| docs, README | KEEP_DEVICE | Device docs remain; server instructions are transitional references. |
| artifacts, var, runtime, caches, egg-info, .venv | KEEP_DEVICE | Generated/local-only state, not source or deployable secrets. Exclude from deployment. |

No Next.js portal, Supabase implementation, Vercel or Render configuration exists in this checkout.

## Audit findings

- app has zero imports from backend. Existing HTTP boundaries are app/auth/pairing.py,
  app/content/client.py, app/sync/client.py and app/update/client.py. Consolidate their
  discovery/configuration without duplicating clients or changing working wire formats.
- Root runtime dependencies are already device-only; the optional backend extra is
  transitional. backend/pyproject.toml independently lists server dependencies.
- AppConfig previously had no environment loader. CLI flags supplied API URLs and
  several credential defaults were fixed to var/. Configuration must resolve all
  device paths consistently while keeping explicit constructor/CLI overrides.
- Existing catalogue fields include size_bytes; download reference is the authenticated
  versioned pack endpoint, rather than a presigned third-party URL.
- Result persistence and background console work are local-first. Preserve upload UUIDs,
  acknowledgement policy, retries, validated content import and signed updates.
- Heartbeat is a new device-only contract; the separate cloud must implement its endpoint.
- Offline release reporting unconditionally read backend/pyproject.toml. Remove that
  filesystem requirement. Full checks remain explicitly transitional.
- Existing uncommitted UI/SQLite work is preserved; this task does not redesign it.

- tests/faults/test_reliability.py has one mixed cloud crash-recovery test. Keep its
  server imports local to that test and skip it when cloud dependencies are absent.

- Packaging verification found schemas and SQLite migrations needed explicit package
  data. Bundle both for regular wheel installs; signed release artifacts also include
  device tools needed by the UI support-bundle adapter.

- Offline CI/release checks deselect the explicitly marked cloud_integration fault
  test. The complete device suite also passes in a fresh environment without server
  packages; the mixed test remains runnable in the transitional cloud environment.
