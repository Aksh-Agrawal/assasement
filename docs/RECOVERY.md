# Local startup recovery

A blocking local startup failure displays `DB-001`, Retry, Diagnostics and Recovery options.
Network failure never opens recovery. Retrying reopens the existing database; it does not delete,
replace or reset assessment records. Startup diagnostics expose safe check summaries only.

1. Close the GUI and stop any sync process before inspecting or replacing database files.
2. Preserve the database and any WAL/SHM files together before maintenance. Check device power,
   free storage and file permissions. Do not erase files as a first troubleshooting step.
3. Retry startup after resolving the underlying storage condition.
4. If support determines restoration is necessary, select a known-good backup and use the existing
   `tools.restore_local_db` procedure. Validate a separate destination first:

   ```text
   python -m tools.restore_local_db VERIFIED_BACKUP SEPARATE_RESTORED_DATABASE
   python -m tools.diagnose --db SEPARATE_RESTORED_DATABASE
   ```

5. Replacement of the active database is a separate, deliberate maintenance action. The restore
   tool requires `--overwrite` for an existing destination and creates a safety copy. Confirm that
   all writers are stopped and preserve sidecar files before replacement.

See `RELIABILITY.md` and `SUPPORT_RUNBOOK.md` for backup and support procedures. The recovery UI
provides guidance rather than exposing filesystem paths or performing a destructive restore.
