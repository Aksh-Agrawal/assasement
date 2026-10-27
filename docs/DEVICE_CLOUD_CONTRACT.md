# Device/cloud API contract (v1)

The device repository owns its HTTP clients and validation copies of formats. The
independent `assasement-cloud` repository owns endpoint implementations, device
registry, approval, server persistence, dashboards, storage and cloud deployment.
Never import server modules to share a model. See DEVICE_MIGRATION_MAP.md for the audit.

## Configuration and transport

`ASSESS_API_URL` is an HTTP(S) origin, without a path, credentials, query or fragment.
No URL is hardcoded. An unset/empty value means offline mode. Examples of deployment
values are `http://192.168.x.x:8000` (development) and `https://api.example.com`
(production). Explicit CLI `--base-url` or AppConfig arguments override environment
defaults. `.env.example` lists all device path, timeout and interval variables.
Python reads process environment; it does not implicitly load `.env` files.

`app/api/client.py:DeviceApi` constructs the canonical domain clients in app/auth,
app/content, app/sync and app/update. `app/api/contracts.py` publishes device-owned
TypedDict shapes and references to the existing validated dataclasses. Heartbeat
uses `app/api/heartbeat.py`. No duplicate server implementation exists here.

Requests use bounded timeouts (connect 5 seconds, read 15 seconds by default).
Redirects are not followed. Download references stay on the configured origin;
no third-party storage SDK or signed URL is required by the device.

## Identity, authentication and pairing

SQLite stores the stable, device-generated UUID. Pairing does not regenerate it.
Authenticated requests carry `Authorization: Bearer <device credential>`.
Credentials are stored atomically in `ASSESS_CREDENTIAL_PATH`, mode 0600 on Pi.
The token is never part of assessment payloads or heartbeat JSON.

1. `POST /api/v1/pairing/request`, JSON `{device_id, device_name}` (name nullable).
   Response: `{session_id, pairing_code, claim_secret, expires_at}`. `expires_at`
   is an ISO-8601 timestamp with timezone. Display only the short pairing code.
2. `GET /api/v1/pairing/{session_id}/status`, header
   `X-Pairing-Claim: <claim_secret>`. Response: `{status}` where status is pending,
   approved, expired or consumed (the device also handles denied).
3. `POST /api/v1/pairing/{session_id}/claim`, same claim header. Response:
   `{credential: <nonempty opaque token>}`. Save locally after successful response.
   Approval happens entirely in cloud admin tooling; no approval endpoint is
   implemented by device code. Lost/expired claims require a new session.

Pairing transport failures leave existing credentials untouched. UI background
operations show an unavailable state and allow retry. CLI surfaces HTTP failures;
there is no silent replacement of identity or credentials. Poll defaults: 2 seconds,
600-second deadline; terminal expired/consumed/denied states stop polling.

## Heartbeat

`POST /api/v1/devices/heartbeat`, authenticated, JSON exactly:

```json
{"software_version":"0.1.0","installed_pack_count":2,"pending_attempt_count":3,"free_storage_bytes":4096,"diagnostic_summary":"OK"}
```

Counts are non-negative integers. Pending includes pending, failed and syncing
completed attempts. Diagnostic summary is one of OK, DEGRADED, ACTION_REQUIRED,
ERROR; the background service reports the SQLite integrity outcome. It never sends
arbitrary diagnostic text, tokens, PINs, Wi-Fi passwords, DATABASE_URL, private keys,
profiles or assessment answers. Response: `{ "status": "accepted" }`.

The independent cloud repository implements this endpoint; the temporary backend does not.
Heartbeat failures cannot invalidate assessment completion or sync acknowledgements.
Default heartbeat cadence is 300 seconds, scheduled on the 60-second worker cycle.

## Catalogue and exact-byte downloads

`GET /api/v1/content/catalog`, authenticated. Response:

```json
{"schema_version":1,"packs":[{"set_id":"example","version":1,"title":"Example","subject":"Science","chapter":"Cells","question_count":20,"size_bytes":1234,"sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","published_at":"2026-10-27T00:00:00Z"}]}
```

The current v1 format uses `size_bytes` (not `size`), a positive version and
question count, SHA-256 hex, and a timezone-aware publication timestamp. Duplicate
set/version entries are rejected. Compatible unknown metadata fields are ignored;
required fields and schema version remain validated. Download metadata is represented by RemotePack;
its derived `download_reference` is
`/api/v1/content/packs/{URL-encoded-set_id}/{version}`. It is not an extra v1 JSON field.

`GET` that reference with bearer auth returns the exact published pack bytes. Device:
fetch catalogue -> stream to temporary file with byte limit -> verify size and
SHA-256 -> validate existing pack schema -> atomically import into local SQLite.
No questions run directly from HTTP responses. Existing set versions are immutable;
active attempts remain pinned to their local version. Default cap: 25 MiB per pack,
5 downloads per content cycle. Local content import remains available without cloud.
See PACK_FORMAT.md, QUESTION_PACKS.md and CONTENT_SYNC.md.

## Attempt upload and acknowledgements

`PUT /api/v1/attempts/{attempt_uuid}`, authenticated, with
`Idempotency-Key: {attempt_uuid}` and `X-Attempt-Payload-Version: 1`.
`app/sync/payloads.py:build_upload_payload` is the canonical serializer;
`app/api/contracts.py:AttemptUpload` describes every nested field:

- payload_version=1, attempt_id, device_id (nullable)
- profile: local_profile_id, server_user_id (nullable); no display name or PIN
- question_set: set_id, set_version, marking {correct, wrong, skip}
- started_at, completed_at: timezone-aware timestamps; duration_ms
- result: {score}
- responses: response_id, question_id, selected_key, confidence, is_correct,
  response_time_ms, marked_review, first_shown_at, answered_at

A skipped response has null selected_key/confidence/is_correct. Answers use A-D;
confidence uses sure/not_sure/guessing/unrated. UUIDs and timestamps come from
committed SQLite state and remain stable across retries.

Cloud returns 201 for first durable acceptance or 200 for idempotent acceptance,
with `{status: "accepted"|"synced", attempt_id, code: "accepted"|"already_uploaded"}`.
For compatibility the existing client treats any 2xx as acknowledgement; cloud must
never emit 2xx before durable storage. A 409 is acknowledged only when its body
contains the same attempt_id and a recognized duplicate code (already_uploaded,
attempt_already_exists, duplicate_attempt) or accepted/synced status. Other conflicts
are permanent failures. Never acknowledge a different UUID.

The worker persists pending -> syncing -> synced only after acknowledgement.
Connection loss after cloud commit leaves a retryable local attempt; retry uses the
same UUID and cloud deduplication. Stale syncing rows recover after 300 seconds.
Result screens read committed local results and never wait for network.

## Software update metadata

`GET /api/v1/device-updates/latest`, authenticated, returns
`{manifest: <object>, signature: <base64 Ed25519 signature>}`. The manifest is validated
against `schemas/update_manifest.schema.json`, with schema_version, signing_key_id,
release (version/channel/created_at/min_supported_version/required_db_schema),
artifact (filename/size_bytes/sha256), compatibility (platform/architecture).
Signature covers canonical sorted compact UTF-8 JSON. No cloud-provided trust key
is accepted; the trusted public key is provisioned locally.

`GET /api/v1/device-updates/{version}/artifact` returns the artifact bytes. The
existing verifier checks signature, hash, size, compatibility and downgrade policy
before staging/activation. Interrupted downloads are removed and may be retried.
See UPDATES.md for health checks and rollback. No automatic update activation was
introduced by separation.

## Retry and offline rules

Attempt timeouts, connection failures, HTTP 408/425/429 and 5xx are transient.
Existing exponential retry policy (bounded automatic attempts, default 5) persists
retry state locally. HTTP 401/403 stops the upload batch until credentials are
repaired; other failures remain local for diagnosis/manual retry. Content and update
clients retain their existing failure classification. Pairing and downloads are
explicit user actions. Catalogue and update metadata also receive low-frequency
background checks; failed downloads do not replace installed content.

`python -m app.sync.service` runs bounded attempt cycles on a separate SQLite
connection/process and emits safe heartbeat metadata. Each client is closed after
use. With no API URL or credential it performs no network work. Systemd example:
`scripts/systemd/assessdev-sync.service`. It runs independently of the pygame process;
assessment, scoring, resume, profiles and PINs need neither cloud nor this service.

## Cloud handoff acceptance

Validate pairing/claim, bearer rejection/revocation, exact content bytes, UUID
idempotency including lost acknowledgements, heartbeat and signed update endpoints
in the independent cloud repository. Temporary backend and admin scripts can then
be removed in a later cleanup commit. The device is ready for that connection;
this change does not certify an untested external cloud deployment.
