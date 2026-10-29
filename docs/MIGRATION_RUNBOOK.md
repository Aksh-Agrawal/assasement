# Phase 8 device migration runbook

No physical device was migrated in Phase 8. Run once from an operator SSH session,
never as a normal student startup procedure. Defaults assume /opt/assessment-device,
user assess and /etc/assessdev/device.env; adjust deliberately for the installed Pi.

## Inventory and WAL-safe backup

```sh
cd /opt/assessment-device
set -a; . /etc/assessdev/device.env; set +a
.venv/bin/python -m tools.pilot_inventory
sudo systemctl stop assessdev-ui assessdev-sync
umask 077
.venv/bin/python -m tools.backup_device /var/lib/assessdev/backups/phase8-before
```

The backup destination must be NEW and operator-only. The command uses SQLite's online
backup API, includes committed WAL pages, checks integrity and records schema/time/counts
and file hashes. It never opens Repository or migrates the source. Packs/questions,
answers, profile mappings, assignment context, device ID and pending sync are in SQLite.
It copies the configured credential file separately into the private backup. Stop writers
and pairing while taking the multi-file snapshot; live SQLite alone remains WAL-safe.

Preserve /etc/assessdev/device.env and public verification keys in operator-only config
backup, and preserve installed release directories/current_release.json plus the service
units separately. Never put credential/config backups into a support bundle. Retain
external media assets if introduced; present question content is embedded in SQLite.
The backup command does not export arbitrary filesystem trees, OS or Wi-Fi configuration.

## Validate before migrating

```sh
.venv/bin/python -m tools.restore_local_db /var/lib/assessdev/backups/phase8-before/assessment-device.db /var/lib/assessdev/restore-validation.db
.venv/bin/python -m tools.pilot_inventory --db /var/lib/assessdev/restore-validation.db
```

Compare schema, profiles, attempts, responses, packs and pending uploads to the manifest.
Protect and retain the source backup. Migration occurs when the new app opens Repository:
0001_init -> 0002_sync_retry -> 0003_student_identity -> 0004_profile_links ->
0005_profile_library -> 0006_institute_work. Migration is forward-only and transactional
per revision. Reopening repeats no applied SQL. Phases 7/8 add no SQLite migration.
Rehearse on the restored copy using `python -m tools.diagnose --db PATH` (this command
opens Repository and can migrate; pilot_inventory itself is strictly read-only).

## Install and validate software

Run scripts/deploy_pi.sh from the laptop to the intended install directory, or use the
reviewed release process. It excludes runtime data and does not delete remote files.
With both writers stopped, install the compatible package in its venv; do not overwrite
var/, credentials or SQLite with laptop files. Install and enable the service described
in PI_SETUP.md. Start GUI and sync, inspect journal by safe event category, and perform
all physical acceptance tests in PILOT_ACCEPTANCE.md before expanding the pilot.

## Explicit legacy claim

Log into the website, select an owned StudyProfile and generate its one-time link code.
On the Pi choose ONLY the intended local profile, Settings -> Account / Profiles ->
Link Study Profile. Enter that code, review the displayed local profile, then Confirm
link. Cancel sends no claim. Server verifies the account/profile intent and paired
installation; local persistence rejects conflicting ownership. The confirmation states
that older attempts stay unclaimed. Linking changes only future attempt-start snapshots;
never infer historical ownership from name/email/device/time. Invalid/expired/replayed
codes and network failures are covered locally; physical confirmation remains pending.

## Reconcile and clean up test fixtures

For each named pilot fixture compare attempt UUID, source=device, StudyProfile UUID,
set/version, institute assignment UUID, score, response count and sync acknowledgement
with website History/teacher Results. A browser attempt has a separate UUID/source=web.
Retry must preserve one server attempt. The local cross-repository test performs these
comparisons and proves personal results remain hidden from teachers.

Delete only fixtures recorded in the operator's test ledger via supported archive,
leave, revoke and unpublish actions. Retain completed attempt evidence and backup for
audit; do not cascade-delete student records or use broad SQL cleanup. Disposable local
test databases/servers are isolated from real accounts. Hosted cleanup is NOT TESTED.
