# Question-Pack Lifecycle

Status: Phase 10D local and authenticated remote-content implementation contract.

`schemas/pack.schema.json` remains the normative Draft 2020-12 structure for schema version 1. Phase 5 adds operational validation and installation rules without changing that schema.

## Pipeline

```text
bounded exact bytes
  → strict UTF-8 decode and JSON parse
  → JSON Schema validation
  → semantic validation
  → optional expected SHA-256 verification
  → existing domain-model conversion
  → one repository transaction
  → SQLite
```

Validation completes before any database write. The same byte-oriented validator can later receive bytes saved by a downloader; it contains no HTTP, DNS, FastAPI, or server dependency.

Phase 10D now supplies those saved bytes through the one-shot remote pipeline documented in
`docs/CONTENT_SYNC.md`. Remote imports do not create another validator or SQL path.

## Validation policy

- Only schema version `1` is supported.
- Set metadata and meaningful required text must remain non-blank after trimming.
- Marking and difficulty use the bounds already defined by the Phase 0 schema and domain models.
- Question IDs and positions are unique within a pack.
- Positions are contiguous `1..N`. Malformed packs are rejected rather than reordered.
- Every question contains options exactly once and in canonical `A`, `B`, `C`, `D` order.
- Correct keys must reference an actual option.
- Optional explanations may be omitted, but are non-blank when present.
- A media reference may be `null`. A non-null reference must be a normalized relative POSIX path beneath `media/`; absolute paths, drive paths, backslashes, traversal, dot components, and colon-containing components are rejected.
- Media-file existence, type, asset size, and asset hash validation are deferred until a pack archive/manifest contract exists.

Pack files are read with a configurable size guard. The default is 25 MiB, chosen as a development safety ceiling rather than a frozen product/content limit.

## SHA-256

The stored content hash is the lowercase hexadecimal SHA-256 of the exact pack bytes. Whitespace or property-order changes therefore produce a different file hash even when parsed JSON values are equivalent. No canonical/logical JSON hash is currently stored.

An expected digest can be supplied before import. A mismatch raises structured `HASH_MISMATCH` validation and prevents the repository operation from starting.

## Immutable versions and activation

`(set.id, set.version)` is immutable. Phase 5 rejects every duplicate version, including an exact-byte re-import, with `DUPLICATE_SET_VERSION`. Importing v2 retains v1 and makes v2 active by default; `--inactive` is available to install without activation.

For an active import, insertion of metadata, insertion of every question, deactivation of the prior active version, and activation of the new version share one `BEGIN IMMEDIATE` transaction. Any exception rolls back every operation. Other connections cannot observe an intermediate state with a partial pack or no active working version. SQLite also rolls back an uncommitted transaction after process termination; later fault campaigns may exercise power-loss behavior directly.

Attempts remain pinned to their stored `set_id`, `set_version`, and `attempt_questions` order. Activating v2 never rewrites an in-progress v1 attempt. Foreign-key `ON DELETE RESTRICT` already prevents a referenced set version from being removed, and Phase 5 exposes no destructive pack-deletion API.

Successful imports persist the exact-byte `content_hash` and a UTC `downloaded_at` timestamp. For local files, `downloaded_at` means installed/imported time.

## Developer commands

```bash
python -m tools.validate_pack content/sample_biology.json
python -m tools.import_pack content/sample_biology.json --db development.db
python -m tools.import_pack content/sample_biology.json --db development.db --dry-run
```

Future catalogue/download code should verify download limits, save or receive exact bytes, and pass those bytes or a local file into this same pipeline. Network behavior, signatures, pack archives, and media manifests are not part of Phase 5.
