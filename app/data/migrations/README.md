# Migrations

Migrations are forward-only, numbered SQL files applied in numeric order. Once a migration has shipped or has been applied to a database, never edit it. Add a new migration with the next number instead.

The runner records the latest applied version in `schema_meta`. Each migration and its version update execute in one transaction; starting an already-current database is a no-op.

Current migrations:

- `0001_init.sql`: Phase 3–8 local assessment schema.
- `0002_sync_retry.sql`: Phase 9A persistent retry time, in-flight timestamp, and error category.

