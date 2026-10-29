# Phase 8 device rollback and maintenance

## Maintenance exit and crash recovery

The operator's dependable exit is over SSH:

```sh
sudo systemctl stop assessdev-ui
sudo systemctl status assessdev-ui --no-pager
```

Explicit systemctl stop does not restart the service. There is no student Linux menu
or ordinary Escape shortcut. The new xinit kiosk has no desktop/window-manager menu.
Unexpected exit restarts after 10 seconds; five starts within 120 seconds trip the limit.
After correcting the issue use `sudo systemctl reset-failed assessdev-ui` followed by
`sudo systemctl start assessdev-ui`. Inspect service logs locally without sharing raw
secrets. If SSH/network fails, use an operator console/second VT. Service commands are
prepared but real boot/crash recovery is NOT TESTED without the Pi.

## Migration/storage failure

1. `sudo systemctl stop assessdev-ui assessdev-sync`; stop any manual CLI writer too.
2. Preserve the failed database and -wal/-shm files together in a NEW protected directory;
   do not remove them or substitute a laptop DB. Take a SQLite backup when readable.
3. Use `python -m tools.restore_local_db VERIFIED_BACKUP NEW_RESTORED_PATH`; never restore
   over a live WAL database. Verify with tools.pilot_inventory and tools.diagnose.
4. Reconcile newly committed work since the backup before choosing any replacement.
5. Point ASSESS_SQLITE_PATH in /etc/assessdev/device.env to the validated replacement,
   preserve the old path/sidecars, ensure assess ownership, and restart both services.
   This reversible path switch avoids stale sidecars and preserves evidence for recovery.
6. Use a release supporting the current SQLite revision; do not downgrade schema or
   delete accounts/profiles to satisfy an older release. No automatic rollback is claimed.

## Credential revocation / rejected late assignment upload

Offline downloaded assessment remains available under the existing cache policy. Cloud
requests fail authentication without deleting local data. Re-pair through Settings ->
Account -> Pair Device with operator approval, then verify current profile-link status.
An installation identity must not change. After the underlying permission/pairing issue
is resolved, an operator may deliberately requeue a retained failed attempt:

```sh
.venv/bin/python -m tools.retry_upload ATTEMPT_UUID
```

That tool resets only failed sync bookkeeping for that exact completed UUID. It does
not alter answers, score, content, ownership or assignment context. Authorization is
rechecked on upload. Re-enrollment alone does not reactivate old assignment recipients.
Removed-membership assignment uploads remain FAILED/permanent and are excluded from
automatic retry; GUI status says Sync attention required. The original assignment and
all response evidence remain local. Previously acknowledged identical retries still
succeed. Do not convert rejected institute work into personal practice. Resolution of
old-recipient authorization requires explicit institute/operator policy; retain evidence.

## Bad release or content sync

Keep the existing database and all immutable packs. Verified updates can stage locally,
and ActivationManager's simulated health failure restores previous metadata. The
current kiosk launches the installed package; no tested process-level activation,
health monitor or service rollback consumes that metadata. Do not claim signed staging
is actual hardware activation. Restore the recorded compatible code artifact manually,
retain credentials/config/database, restart services, and run physical acceptance.

Interrupted/hash-invalid/schema-invalid downloads leave existing packs untouched.
Retry after a complete authorized catalogue refresh. Active attempts remain pinned to
the original version even after a newer pack is downloaded. Never wipe the library or
pending queue as a recovery step.
