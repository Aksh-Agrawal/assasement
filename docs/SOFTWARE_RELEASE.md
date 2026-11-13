# Software release and rollback procedure

This procedure is prepared for a reviewed, committed device release. The current workspace contains uncommitted integration work; do not deploy it by pulling `main` or running the helper without reviewing its destination. The helper defaults to `~/assessment-device`, while the prepared kiosk service expects `/opt/assessment-device`; use the home directory only as a staging checkout.

## 1. Build and verify a release on the development host

From the device repository root, record the commit and review the whole tree before packaging:

```powershell
git status --short
git diff --check
git diff --stat
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q -k "not test_full_crash_offline_lost_ack_recovery_has_one_server_attempt"
```

Include only reviewed source, QML, docs, tests, migrations and required packaging files. Exclude `var/log/assessment-device.log`, `artifacts/`, `runtime/`, `.venv/`, `.git/`, credentials, SQLite files and WAL/SHM sidecars. Keep each repository's release commit separate; the device repository is the deployable appliance, while cloud code is released through its own workflow.

## 2. Stage code without touching device data

Use the existing helper only to stage into the assess account's home directory. It has no remote-delete option and excludes `var/` and SQLite files:

```sh
bash scripts/deploy_pi.sh assess@DEVICE_HOST assessment-device-staging
```

The kiosk service uses `/opt/assessment-device`, so copy reviewed code from staging to the installed path only after checking the staged commit. Do not copy the home directory's `.env`, virtual environment or runtime data.

## 3. Back up and validate SQLite before installing

Over SSH, stop both writers and identify the exact configured `ASSESS_SQLITE_PATH` from `/etc/assessdev/device.env` (the repository example defaults to `/var/lib/assessdev/assessment-device.db`). Never guess the path. Then:

```sh
sudo systemctl stop assessdev-ui assessdev-sync
DB=/opt/assessment-device/var/assessment-device.db
BACKUP="${DB}.before-release-$(date -u +%Y%m%dT%H%M%SZ)"
sudo sqlite3 "$DB" ".backup '$BACKUP'"
sudo sqlite3 "$BACKUP" 'PRAGMA quick_check;'
sudo sha256sum "$DB" "$BACKUP"
```

Keep the backup outside any deployment directory and preserve the original database and sidecars. If SQLite reports anything other than `ok`, stop and use the recovery procedure in `ROLLBACK.md` before proceeding.

## 4. Install dependencies and apply migrations

Copy code to `/opt/assessment-device` with no `--delete` and explicitly exclude `.venv`, `var`, `runtime`, `.env*`, artifacts and databases. On the Pi:

```sh
cd /opt/assessment-device
. .venv/bin/activate
python -m pip install -e '.[gui]'
```

The repository applies numbered SQLite migrations when it opens the database. Current tracked prior integration work includes additive migration `0008_question_solution_figures.sql`; Analytics/detail caching adds no migration. If migration 0008 is part of the reviewed release, verify a separate copy of the backup first. From the device repository root, while services are stopped, run `sqlite3 "$BACKUP" ".backup '/tmp/assessment-release-check.db'"`, then `ASSESS_SQLITE_PATH=/tmp/assessment-release-check.db .venv/bin/python -m app.ui_qt.main --smoke-test`, followed by `sqlite3 /tmp/assessment-release-check.db 'PRAGMA quick_check;'`. This tests the real pre-release schema without migrating the live database. Keep the configured production DB path unchanged and retain the backup until the application and quick check pass.

## 5. Start and verify

```sh
sudo systemctl daemon-reload
sudo systemctl reset-failed assessdev-ui assessdev-sync
sudo systemctl start assessdev-sync assessdev-ui
sudo systemctl status assessdev-ui assessdev-sync --no-pager
sudo journalctl -u assessdev-ui -u assessdev-sync -n 100 --no-pager
```

Verify the UI opens offline, select a non-production test profile, open Progress/Analytics, History, Review, Recovery Practice and Sync Status, then reconnect and check a retry. Physical screen/input and boot behavior are separate acceptance work and must be performed on the actual Pi.

## Rollback

1. Stop both services over SSH and preserve current code, logs, the current DB, WAL/SHM files and the pre-release backup.
2. Restore the previous reviewed code only after confirming it supports the database schema now present. This release adds no Analytics migration, but migration 0008 may be included from earlier pending work.
3. Never copy an older database over the live file. If the database must be restored, use a new filename, validate it with `PRAGMA quick_check`, update `ASSESS_SQLITE_PATH` to that new path, and preserve the current database for reconciliation. Restoring a pre-release backup can omit attempts completed after that backup.
4. Run `sudo systemctl reset-failed assessdev-ui assessdev-sync`, start services and check the logs. Leave the backup intact until assessment history has been reconciled.

Automatic schema downgrade, automatic data rollback and physical Raspberry Pi compatibility are not claimed.
