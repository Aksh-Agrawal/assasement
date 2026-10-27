# Connecting the device after hosting

Readiness work does not deploy anything or modify Supabase. Until hosting exists,
leave `ASSESS_API_URL=` empty. Local profiles, installed content, assessment,
resume, scoring and pending uploads work offline.

## One-time Pi preparation

Install the device with `python -m pip install -e '.[gui]'`; no server extras or
Node are required. Follow PI_SETUP.md for writable paths and graphical startup.
Provision `/etc/assessdev/device.env` from `.env.example` and install/enable
`scripts/systemd/assessdev-sync.service`. Both the graphical launcher and sync
service must read the same environment file and use the same SQLite and credential
paths. Credentials must stay writable only by the device user (0600 on Pi).
Do not copy the old backend or cloud admin tools to the Pi.

## Future connection procedure

1. Set only `ASSESS_API_URL=https://<future-api-host>` in the existing environment
   file after the actual API is hosted. Use the API origin, without a trailing path,
   credentials, query or fragment. No Supabase address or service key belongs here.
2. Restart the graphical device app through its existing launcher and run
   `sudo systemctl restart assessdev-sync`. Export the same environment for CLI
   commands below, e.g. `set -a; . /etc/assessdev/device.env; set +a`.
3. Run `python -m tools.cloud_check`. Before hosting, an empty URL prints
   `API configured: NO` and `Cloud readiness: WAITING_FOR_API_URL`, exit 0.
   After hosting, expect DNS/verified HTTPS/health OK and PAIRING_REQUIRED.
4. Settings → Account → Pair Device → request code; approve that code in web admin.
   The UI polls and claims the device credential, then saves it locally. Alternatively
   run `python -m tools.pair_device` and approve its displayed code. Never copy a
   token into a command line or send it to support. Re-run cloud_check: expect READY.
5. Settings → Sync → Sync Now sends pending attempts and safe heartbeat metadata.
   Check the web device last-seen/counts. Automatic sync starts with the service,
   checks every 60 seconds and retries after connectivity returns; heartbeat and
   metadata checks default to every 300 seconds. No assessment waits for this work.
6. Settings → Content Updates → Check available content fetches the authenticated
   catalogue. CLI preview: `python -m tools.sync_content --dry-run`.
7. Download the assigned test pack from Content Updates. The CLI alternative,
   `python -m tools.sync_content --limit 1`, installs one eligible pack (choose a
   catalogue containing only the intended test pack for this command).
8. Disconnect networking, restart the app and complete an assessment with that pack.
   Confirm immediate results, local resume, and pending sync. Reboot to verify the
   pairing credential survives. Existing versioned attempts retain their content.
9. Restore networking. Wait for the next cycle or select Sync Now. Confirm pending
   count drops and the same attempt UUID appears once in web Results. Repeat Sync
   Now to verify no duplicate. Run the full HOSTED_ACCEPTANCE_TEST.md checklist.

## Transport and failure behavior

AppConfig reads `ASSESS_API_URL` once per process; Python does not load `.env`
implicitly. All HTTP clients use `app/api/transport.py`: bounded connect/read/write/
pool timeouts, bearer headers, certificate verification and redirects disabled.
Development can use `http://<laptop-LAN-IP>:8000` through the same variable; use a
trusted development network because HTTP is unencrypted. Production uses HTTPS
with its normal CA validation. There is no configuration to disable verification.

HTTP operations are single-shot. SyncWorker owns persistent bounded exponential
retry; retries retain the committed attempt UUID. Other operations allow explicit
retry. Failure states include OFFLINE, TIMEOUT, AUTH_REQUIRED, SERVER_ERROR,
INVALID_RESPONSE and CONTENT_VALIDATION_FAILED. UI never renders raw exceptions.
Interrupted downloads remove temporary files; size, SHA-256 and schema validation
precede atomic SQLite import. Question packs use hashes/schema; software updates
also require a locally trusted Ed25519 signature. Network input cannot replace trust.

The sync daemon refreshes catalogue/update metadata without automatic software
activation. User-selected pack downloads run in the console worker. Metadata failures
are isolated from committed uploads; active attempts keep their original version.

## Separation audit

The runtime imports no backend, FastAPI, PostgreSQL, Alembic, Next.js or Supabase
SDK. Wire contracts and JSON schemas are device-owned. The sibling cloud checkout
`E:\startup-cloud` owns route implementations; source was inspected read-only to
confirm pairing, catalogue, downloads and heartbeat. No cross-repository imports
or real Supabase interop were introduced.

The temporary `backend/` is deliberately retained: the legacy cloud-integration
fault test, `tools/approve_pairing.py`, `tools/revoke_device.py`, and release-check
`--full` still reference it. Removing it fails the requested safe-removal condition.
It is excluded from device packages and Pi deployment; normal device CI excludes
the optional cloud-integration test. Server packages are not device dependencies.
Migrate those legacy checks/admin tools to the cloud repository before deleting it.
