# Migrations

Migrations are forward-only, numbered SQL files applied in numeric order. Once a migration has shipped or has been applied to a database, never edit it. Add a new migration with the next number instead.

The runner records the latest applied version in `schema_meta`. Each migration and its version update execute in one transaction; starting an already-current database is a no-op.

Current migrations:

- `0001_init.sql`: Phase 3–8 local assessment schema.
- `0002_sync_retry.sql`: Phase 9A persistent retry time, in-flight timestamp, and error category.


- 0003_student_identity.sql: additive ownership/link fields and cached account hints; no automatic claim.

- 0004_profile_links.sql: durable verified-link context and creation-time attempt ownership snapshots.

- 0005_profile_library.sql: private physical versions and per-profile catalogue/eligibility cache; existing packs remain shared.

- 0006_institute_work.sql: separate per-profile institute grants and atomic creation-time assignment context; existing rows and pending uploads retained.

- 0007_custom_subjects.sql: rebuild question-set metadata to allow any nonblank subject up to 64 characters; preserve child content, grants and history. The runner disables foreign-key enforcement only around the atomic rebuild, validates all foreign keys before commit, and restores enforcement afterward.
