# Development API Contract

Status: Phase 10D contract. Pairing, attempt upload, authenticated update distribution, remote
question content, and health are concrete. PostgreSQL is the target backend persistence through
SQLAlchemy and Alembic; SQLite remains a fast backend test convenience. A production admin
identity provider remains pending.

The development base URL is normally `http://127.0.0.1:8000`. Production transport has not been
configured and must use HTTPS.

## Health

### `GET /health`

Returns `200 OK` and `{"status":"ok"}`. Authentication is not required.

### `GET /ready`

Performs a database `SELECT 1` and, on PostgreSQL, compares `alembic_version` with the expected
head. It returns only `status`, `database`, application `version`, and `migration`; connection
strings and credentials are never exposed. Database/migration failure returns `503`. `/health`
remains process liveness and does not depend on PostgreSQL.

## Development application updates

`GET /api/v1/device-updates/latest` requires the existing device bearer credential and returns a
canonicalizable manifest object plus its Base64 Ed25519 signature. It does not return a private
key. `GET /api/v1/device-updates/{version}/artifact` uses the same authentication and serves only
the artifact named by the configured development catalog manifest. A missing catalog returns 404;
invalid or revoked credentials return 401. These endpoints are a local development catalog, not a
production release-management service.

## Remote question content

Both content endpoints require the Phase 10A device credential:

```text
Authorization: Bearer device_<credential-id>.<secret>
```

`GET /api/v1/content/catalog` returns schema version 1 and every active, immutable published
version ordered by `subject`, `set_id`, then `version`. Entries contain only `set_id`, `version`,
`title`, `subject`, `chapter`, `question_count`, `size_bytes`, `sha256`, and `published_at`.
Server filesystem paths are never returned. Exact `(set_id, version)` is canonical; the catalog
does not require a latest-version shortcut.

`GET /api/v1/content/packs/{set_id}/{version}` returns the exact published JSON bytes as
`application/json`, with `Content-Length`, an SHA-256 ETag, and `X-Content-SHA256`. These headers
are useful metadata only; the device trusts the catalog digest and verifies the downloaded bytes.
An unknown or inactive exact version returns `404` and is never replaced with another version.
Missing, invalid, or revoked credentials return `401` for either endpoint.

## Attempt upload

### `PUT /api/v1/attempts/{attempt_id}`

Uploads one locally completed attempt and its responses. `attempt_id` is the device-generated UUID
and is both resource identity and idempotency identity.

```text
Authorization: Bearer device_<credential-id>.<secret>
Idempotency-Key: <attempt_id>
X-Attempt-Payload-Version: 1
```

The path ID, idempotency header, and body ID must match. The body is the exact Phase 9A payload:

```json
{
  "payload_version": 1,
  "attempt_id": "device-generated UUID",
  "device_id": "configured device ID or null",
  "profile": {
    "local_profile_id": "local profile ID",
    "server_user_id": "paired server user ID or null"
  },
  "question_set": {
    "set_id": "exact installed set ID",
    "set_version": 1,
    "marking": {"correct": 4, "wrong": -1, "skip": 0}
  },
  "started_at": "UTC timestamp",
  "completed_at": "UTC timestamp",
  "duration_ms": 1000,
  "result": {"score": 4},
  "responses": [
    {
      "response_id": "device-generated response ID",
      "question_id": "question ID",
      "selected_key": "A",
      "confidence": "sure",
      "is_correct": true,
      "response_time_ms": 1000,
      "marked_review": false,
      "first_shown_at": "UTC timestamp or null",
      "answered_at": "UTC timestamp or null"
    }
  ]
}
```

`selected_key`, `confidence`, and `is_correct` are all null for a skipped response. An answered
response supplies all three. The backend preserves exact question-set ID and version.

### Success and idempotency

First storage returns `201`:

```json
{"status":"accepted","attempt_id":"...","code":"accepted"}
```

The complete validated body is fingerprinted with SHA-256 over deterministic canonical JSON:
Pydantic JSON-mode values, sorted keys, compact separators, UTF-8, and no NaN. No body field is
excluded. Repeating the same UUID and fingerprint returns successful `201`:

```json
{"status":"synced","attempt_id":"...","code":"already_uploaded"}
```

No second row is created. The same UUID with a different fingerprint returns `409 Conflict` and
does not overwrite the original. Attempt and response rows are inserted in one transaction.
`device_attempt_id` is database-unique, as is `(attempt_id, question_id)` for responses.

## Device pairing and authentication

`POST /api/v1/pairing/request` accepts a UUID `device_id` and optional `device_name`, returning a
random six-digit code, opaque session ID, high-entropy claim secret, and expiry. The default TTL is
600 seconds and is configurable with `ASSESS_PAIRING_CODE_TTL_SECONDS`.

`GET /api/v1/pairing/{session_id}/status` and
`POST /api/v1/pairing/{session_id}/claim` require `X-Pairing-Claim`. Status exposes only
`pending`, `approved`, `expired`, or `consumed`. Claim returns a high-entropy credential once.
Responses never contain credential hashes or backend database IDs.

For **DEVELOPMENT / TEST ONLY**, approve with `python -m tools.approve_pairing <code>` and revoke
with `python -m tools.revoke_device <device-uuid>`. Both read `DATABASE_URL`; Phase 10A deliberately
has no admin HTTP endpoint or dashboard. Re-pairing revokes active credentials and generates a new
secret. Attempt ownership always comes from the authenticated device, never the request body.

## Error behavior and client mapping

- `400`: identity/version header mismatch or a database business error.
- `401`: missing, invalid, or revoked device credential.
- `409`: stored UUID was sent with different semantic data.
- `422`: JSON/schema validation error.
- `500`: unexpected server error.
- `503`: backend database is unavailable; the device retains and retries its local attempt.

The Phase 9A client maps `401`/`403` to authentication failure; `400`, conflicting `409`, and `422`
to permanent failure; and transport failures, timeouts, `408`, `425`, `429`, or `5xx` to retryable
failure. Any `2xx` is success.

Installed assessments remain usable without pairing or any network feature.
