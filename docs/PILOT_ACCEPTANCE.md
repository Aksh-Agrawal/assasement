# Phase 8 device pilot evidence — 29 October 2026

PHYSICAL PI ACCEPTANCE: PENDING. No hardware PASS is claimed.

Actual SSH check: documented assess@assessdev-proto1.local failed hostname resolution.
No Pi OS, display/input, boot, reboot, offline Wi-Fi, thermals, RAM or stability measurement
was obtained. No deployment was performed and no Pi database was modified.

Local evidence:

- PASS: historical SQLite prefixes 2/3/4/5/6 upgrade to 6 and repeat with original profiles,
  completed pending attempt, answers, question order and installed content preserved.
- PASS: explicit selected-profile mapping after migration leaves old upload unclaimed.
- PASS: live-WAL online SQLite backup, integrity, separate restore and count/state retention;
  private credential is backed up separately, never printed or added to support archives.
- PASS: real device Python client against local cloud proves assignment download/offline
  engine/resume/idempotent upload and personal-vs-assigned teacher privacy.
- PASS: removed-membership late completion stays FAILED/permanent, original payload and
  assignment retained, Sync attention required visible; explicit exact-UUID operator retry
  modifies bookkeeping only and never bypasses cloud authorization.
- PASS: generated support archive redacts password/token/Wi-Fi/service-key/enrollment
  fixtures and excludes databases, credentials and student response content.
- NOT TESTED: systemd/xinit boot-to-app, crash rate limiting and maintenance exit on actual Pi.
- NOT TESTED: real device credential-revocation recovery, content updates during active
  attempt, network-drop recovery, hosted delivery/sync, performance and 30-60 minute soak.
- NOT TESTED: actual signed-update service activation/health rollback. Existing implementation
  verifies/downloads/stages and simulates metadata rollback; kiosk uses installed package.

Use MIGRATION_RUNBOOK.md for protected inventory/backup, PI_SETUP.md for installation,
and ROLLBACK.md for exact maintenance and recovery commands. The full physical and hosted
scenario ledger is in the independent cloud repository's docs/PILOT_ACCEPTANCE.md.
Record each real scenario PASS / FAIL / NOT TESTED with timestamp, release and fixture IDs.
No accounts or attempts should be deleted to turn a failed scenario into a pass.

Restrict a pilot to approved single-account or supervised use until unrelated-account
shared-device access control/offline authentication policy is resolved. Legacy local
profile linking is supported; historical attempt import/transfer is not authorized.


## Actual local legacy database rehearsal

A protected SQLite online backup of the existing laptop var/assessment-device.db was
restored into an independent rehearsal file and migrated 2 -> 6. All original table rows
were compared, not only counts: 1 profile, 3 attempts, 9 responses and 1 installed pack
survived; question rows/order were retained and no profile was auto-claimed. The source
remains revision 2 and was not opened through Repository. This is laptop legacy evidence,
not a backup or migration of the physical Pi. Evidence: device artifacts/
phase8-local-legacy-backup/rehearsal-result.json (ignored, operator-private).


## Final local verification results

Cloud backend: 148 passed (full suite; disposable PostgreSQL and cross-repository clients
configured). Frontend: 32 passed; all three production-build browser acceptance scripts
passed; build, typecheck and lint passed. Device: 301 passed. Both Ruff checks and Git
whitespace checks passed after fixing a test import ordering issue. New migration/backup
and late-upload reconciliation checks were rerun after their final changes. One existing
Starlette/httpx deprecation warning appears in Python suites; no test failed.
Kiosk launcher: Git Bash `bash -n scripts/kiosk-session.sh` passed. This is syntax-only,
not evidence of systemd/Xorg startup. LF endings are enforced for shell/service files.


## Supplied connection details follow-up

Hosted origins are now known: backend https://startup-cloud.onrender.com and frontend
https://startup-cloud-1.onrender.com. Backend /health and /ready return 200 for the older
release; student/me is 404 and OpenAPI has no student/institute routes. Actual browser
shows the older admin login, not the new student interface. Full hosted device/product
acceptance remains blocked by deployment version. No production changes were made.
Both aksh@aksh and aksh@aksh.local failed hostname resolution. A reachable Pi IP/full SSH
command is still needed; physical acceptance remains PENDING.


## Tentative Pi target supplied by user

The user supplied `aksh@192.168.1.50` as a temporary, unconfirmed address. A
batch-mode read-only SSH attempt to port 22 timed out. No device identity was
verified, no host trust was bypassed and no Pi changes were made. Use this target
only as a placeholder until the actual address is confirmed. Physical acceptance
remains PENDING; this is not evidence that the Pi itself is faulty.
