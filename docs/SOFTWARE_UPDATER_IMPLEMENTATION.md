# Questraa Raspberry Pi software updater

## Audit of the previous Settings action

The previous implementation was only a signed download and staging flow:

1. `app/ui_qt/qml/screens/SoftwareUpdateScreen.qml` called `SettingsController.checkUpdate()` and `downloadUpdate()`.
2. `app/ui_qt/controllers/settings_controller.py` exposed the detected `available_update`, but its version getter used a `1.2.1` fallback instead of reading the manifest.
3. `app/ui/device.py` routed `update_check` and `update_download` through `DeviceApi.updates()`. The check called `UpdateClient.check_for_update()` (`GET /api/v1/device-updates/latest`). The download called `UpdateClient.download_update()` (`GET /api/v1/device-updates/{version}/artifact`), checked the Ed25519 signature, SHA-256, version, platform, architecture and database schema, then called `stage_update()`.
4. `app/update/client.py`, `manifest.py`, `verifier.py` and `staging.py` already provided authenticated manifest retrieval, bounded `.part` downloads, signature/integrity verification and traversal-safe extraction.
5. There was no production activation path. `app/update/activation.py` only simulated version metadata and rollback through a test callback. The Qt controller had no install slot; the separate compatibility controller's “Install & Restart” choice was disabled and explicitly said a release launcher was required.
6. The device cloud API endpoint already existed. `startup-cloud/backend/app/api/routes/admin.py` had an authenticated admin release-publishing API that verifies the configured public key, manifest and artifact before storing an immutable version; the device update endpoint reads that release catalog.

So the button could check and stage a verified release. It could not install it, add dependencies, switch the running application, restart, test startup or roll back.

## Implemented flow

- The Qt Settings screen now shows installed and available versions, signed release notes, compatibility, checking/downloading/installing/success/failure states and a download progress bar. `Download & Install` downloads and verifies the bundle, then requests installation.
- While a student is in an active assessment, installation waits until that assessment exits. The app remains available during metadata checks, downloads and isolated dependency installation.
- `app/update/staging.py` retains the signed manifest and signature with the staged bundle. The independent updater verifies the original artifact and manifest a second time before activation.
- `scripts/systemd/assessdev-update.service` runs the fixed updater at `/usr/local/libexec/assessdev-updater.py` as root. The app can only request a version through one narrow sudoers rule; it cannot supply a shell command, install path, URL, or systemd unit name.
- Each app version has its own release directory and virtual environment under `$ASSESS_APP_ROOT/releases/<version>`. Dependencies install there, leaving the current release and its environment intact until the new Qt smoke test and copied-database migration probe pass.
- App data, credentials and update state live outside version directories under `$ASSESS_DATA_DIR`; content and recovery paths are separately configured. Before activation the service takes an SQLite online backup and saves a transaction record. It switches `$ASSESS_APP_ROOT/current` with an atomic symlink rename, restarts the configured UI unit, and checks that the kiosk service stays up with one process. Failed health checks restore application code only; live data is never replaced by an older snapshot.
- The trusted updater helper lives outside version directories so a failed app release cannot replace the tool needed to roll back. After a healthy activation, the helper refreshes itself from the newly verified, signed release for the next update.
- `scripts/systemd/assessdev-recover.service` runs before the kiosk at boot. If power is lost during activation, it checks the selected version and performs the smoke check or restores the previous application symlink while retaining existing local data.
- If internet, authentication, disk space, artifact integrity, package installation, compatibility, migration validation or startup checks fail, no unverified release becomes current. Update failures do not reset the database or pending sync records.

The service deliberately requires additive, migration-safe releases. It probes the new migration against a temporary copy before stopping the app, and refuses any migration that changes protected student/content/sync rows. Database migrations must remain forward-compatible: do not remove or rename fields/tables needed by the previous release. The previous app now tolerates a higher migration version without trying to downgrade it. Backups are retained under `$ASSESS_DATA_DIR/backups/` for operator recovery; automatic cleanup is not configured.

## Release publishing

`.github/workflows/device-release.yml` validates pushes to `main` and version tags on ARM64 Ubuntu with Python 3.13. Validation runs lint, the device tests, the offline readiness checks and an installed-package Qt smoke test with an ephemeral signing key. Only a version tag whose version matches the application can reach the production signing and publication job.

Before the workflow can publish:

- The cloud service needs `RELEASE_PUBLIC_KEYS` set to JSON mapping `questraa-stable-1` to the base64 encoded raw Ed25519 public key. Set `MAX_UPLOAD_BYTES` high enough for the base64 encoded artifact plus JSON (the existing default is 25 MiB).
- Configure GitHub Actions secrets `UPDATE_SIGNING_PRIVATE_KEY_B64`, `UPDATE_CLOUD_URL`, `UPDATE_ADMIN_EMAIL` and `UPDATE_ADMIN_PASSWORD`.
- The release upload uses an authenticated cookie and the backend checks its Origin header. The workflow defaults to `https://startup-cloud-1.onrender.com`. Set the optional GitHub Actions variable `UPDATE_CLOUD_ORIGIN` to another exact HTTPS origin in `CORS_ALLOWED_ORIGINS` if the frontend changes.
- Put only the PEM public key on the Pi at `/etc/assessdev/update-public.pem`. Never place the private signing key on the device or in the repository.
- The v0.1.1 workflow targets `linux/aarch64`, requires app 0.1.0 or later and accepts an installed SQLite schema of 8 or later. The package migrates schema 8 to 9. The regression test verifies existing responses, pending sync state and question-set pins survive the migration.

### Existing 0.1.0 installations

The 0.1.0 updater installed by the original bootstrap creates its staging tree under `UMask=0077`. It changes ownership on the new release, but does not grant the kiosk group access to those files. If the installed helper still has that implementation, the kiosk cannot read the first OTA release and the corrected helper inside that release never becomes active.

Before publishing this OTA, identify the installed helper and its unit configuration with read-only checks. If the permissions fix is missing, update the standalone helper through an approved maintenance session using the reviewed release source. Keep the existing managed release, database, credentials and content paths in place. Verify the service account can traverse and read a staged release before attempting the one-click update.

The workflow itself does not require a human environment approval. Because a matching `v*.*.*` tag can access the Ed25519 signing key and cloud admin credentials, protect that tag pattern in GitHub rulesets and restrict tag creation to release maintainers before enabling the secrets. The cloud route validates the admin session, manifest schema, trusted Ed25519 signature, artifact hash and immutable version. The cloud schema was checked locally; production cloud configuration was not changed.

Create the stable key pair once on a trusted release workstation (never on the Pi):

```powershell
.\.venv\Scripts\python.exe -m tools.generate_update_keys `
  --private var\update-keys\questraa-stable-1.private.pem `
  --public var\update-keys\questraa-stable-1.public.pem
```

Set GitHub secret `UPDATE_SIGNING_PRIVATE_KEY_B64` to the base64 encoding of the complete private PEM file:

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes('var\update-keys\questraa-stable-1.private.pem'))
```

Set cloud variable `RELEASE_PUBLIC_KEYS` to the JSON value printed by this command. It contains only the raw public key, encoded for the cloud verifier:

```powershell
.\.venv\Scripts\python.exe -c "import base64,json; from cryptography.hazmat.primitives import serialization; from cryptography.hazmat.primitives.serialization import load_pem_public_key; k=load_pem_public_key(open(r'var\update-keys\questraa-stable-1.public.pem','rb').read()); print(json.dumps({'questraa-stable-1':base64.b64encode(k.public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()}))"
```

Use the same public PEM for the Pi setup and cloud environment. If it is rotated, overlap old and new trusted key IDs during a transition; do not replace the only key until every active Pi trusts the next key.

## One-time Raspberry Pi setup

### Existing Pi paths

The old app's normal defaults are cwd-relative: `AppConfig.database_path` resolves to `var/assessment-device.db`, `CredentialStore` to `var/device_credentials.json`, cached question packs to `content/`, media to `media/`, and recovery-content downloads to `runtime/content-downloads/tmp/`. The previous installer instead assumed user `assess`, app root `/opt/assessment-device`, and data root `/var/lib/assessdev`; it could miss the actual database when the app ran under `/home/aksh/assasement` or used `ASSESS_*` overrides.

The installer defaults to the Pi account `aksh`, the legacy checkout `/home/aksh/assasement`, and a new protected release root `/opt/questraa-device`. It reads existing `ASSESS_DATA_DIR`, `ASSESS_SQLITE_PATH` and `ASSESS_CREDENTIAL_PATH` values from `/etc/assessdev/device.env` when available, and accepts explicit `ASSESS_LEGACY_*` overrides. It checks the live DB, stops the kiosk and redundant standalone sync service before copying with SQLite's online backup API, refuses to overwrite destination data, verifies the copy, and retains the original DB and credentials. Packs, media and recovery downloads remain at their current paths outside versioned code directories. App, account, data, database, credential, content, media, download, log and service paths are configurable. The managed release root cannot have an ancestor writable by the kiosk user, so the unprivileged app cannot redirect the privileged updater to user-controlled code.

Before installation, inspect the actual process and paths on the Pi. These commands are read-only; replace `<PID>` with the process ID printed by the first command:

```sh
ps -u aksh -o pid,args | grep '[p]ython.*app.ui_qt.main'
sudo systemctl cat assessdev-ui.service
tr '\0' '\n' < /proc/<PID>/environ | grep '^ASSESS_'
```

If no `ASSESS_SQLITE_PATH` is set, the historical cwd-relative default is `/home/aksh/assasement/var/assessment-device.db`. Confirm it exists and passes an integrity check:

```sh
python3 - <<'PY'
import sqlite3
p = '/home/aksh/assasement/var/assessment-device.db'
db = sqlite3.connect(f'file:{p}?mode=ro', uri=True)
print(db.execute('PRAGMA quick_check').fetchone())
db.close()
PY
```

Expected output is `('ok',)`. If the running process shows another database or credential path, pass that exact path below. Do not continue if the live DB location is unclear or the integrity check fails.

These commands assume Debian 13, Python 3.13.5, the existing `aksh` account and group, approved bootstrap code in `/home/aksh/assasement`, and the reviewed public key copied to the Pi. Confirm the primary group with `id aksh`; if it is not `aksh`, use that group for the key permissions and `ASSESS_SERVICE_GROUP`. The updater release root must remain outside any path the kiosk user can write. This is a one-time migration; later app releases do not use Git. From the release workstation, copy the public key (replace the host with the Pi's SSH address):

```powershell
scp var\update-keys\questraa-stable-1.public.pem aksh@<pi-host>:/tmp/questraa-stable-1.public.pem
```

Wait until no assessment is active. The installer stops the kiosk before copying the DB and aborts if a manually launched Questraa process remains.

```sh
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip xserver-xorg xinit openbox xserver-xorg-legacy libegl1 libgl1 libxkbcommon0 libxcb-cursor0 libxkbcommon-x11-0 libxcb-xinerama0
sudo install -d -o root -g aksh -m 0750 /etc/assessdev
sudo install -o root -g aksh -m 0640 /tmp/questraa-stable-1.public.pem /etc/assessdev/update-public.pem
cd /home/aksh/assasement
sudo env ASSESS_APP_ROOT=/opt/questraa-device \
  ASSESS_LEGACY_APP_ROOT=/home/aksh/assasement \
  ASSESS_SERVICE_USER=aksh ASSESS_SERVICE_GROUP=aksh \
  ASSESS_LEGACY_SQLITE_PATH=/home/aksh/assasement/var/assessment-device.db \
  ASSESS_LEGACY_CREDENTIAL_PATH=/home/aksh/assasement/var/device_credentials.json \
  sh scripts/install_updater.sh
sudo systemctl status assessdev-recover assessdev-ui --no-pager
```

The explicit legacy `var/` paths above are correct only if read-only checks confirmed them; otherwise replace them with the discovered paths, or pass `ASSESS_LEGACY_DATA_DIR` to derive defaults. The release root is `/opt/questraa-device`; persistent data targets are `/var/lib/assessdev/assessment-device.db` and `/var/lib/assessdev/device_credentials.json`. Existing target files are never overwritten. Source files remain at their original paths after setup. Unless the live config specifies otherwise, packs/media/downloads remain at `/home/aksh/assasement/content`, `/home/aksh/assasement/media`, and `/home/aksh/assasement/runtime/content-downloads/tmp`. Review `/etc/assessdev/device.env` and root-only `/etc/assessdev/updater.env` before enabling the kiosk.

The setup script creates the initial versioned release, installs its Python/Qt dependencies, puts the updater and launch wrappers outside release directories, renders systemd units for `aksh` and the selected paths, and validates its narrow sudo rule with `visudo`. It does not recursively change ownership or remove the old checkout/state. Keep the original paths until successful boot and a separate backup are confirmed.

## Future releases

After approving and merging a device change, create and push a new semantic version tag. The workflow validates, signs, builds, publishes to GitHub Releases and registers that same signed bundle in the cloud catalog. Once the Pi can reach the API and is paired, the student selects **Settings → Software Update → Check for Updates → Download & Install**. It finishes installation and restarts the kiosk itself.

Do not use `git pull` as the software update mechanism after the one-time versioned installation. Content pack updates remain separate from application software releases.

## Recovery

- **Automatic rollback:** the update service switches back to the previous `current` release if the new kiosk fails its startup check. It keeps the live SQLite database and credentials; replacing them with pre-update snapshots could discard a newly completed attempt or pending sync row. Backups are retained for manual recovery and never overwrite existing files.
- **Power interruption:** the boot recovery unit examines the durable transaction record before launching the kiosk.
- **Manual inspection from SSH:** `sudo systemctl status assessdev-update assessdev-recover assessdev-ui --no-pager`; `sudo journalctl -u assessdev-update -u assessdev-recover -u assessdev-ui -b --no-pager`; inspect `/etc/assessdev/updater.env`, the configured update status path, and backups under the configured data root.
- **Manual previous release selection:** stop the kiosk, change `$ASSESS_APP_ROOT/current` to point at the desired existing release, then start the kiosk. Keep the live database; do not restore an older snapshot over it. Do not delete the current or previous release before confirming a known-good boot.

## Verification and physical work still required

Software tests exercise signature and checksum rejection, interrupted downloads, incompatible manifests, safe archive extraction, staging, simulated activation/rollback, SQLite/credential backup and rollback preservation, first-time data migration, incorrect path rejection, forward-schema compatibility, SettingsController/QML binding and 800x480 QML screen compilation. The root systemd updater is intentionally not run against a laptop installation.

The Raspberry Pi still needs physical verification for: first-time bootstrap and database/credential migration; cloud authentication and signed release discovery; ARM64 dependency installation; progress display and assessment deferral; disk-full and dependency failure; successful update/restart; failed Qt startup and rollback; power loss at each activation point and boot recovery; display/touch operation after restart; and confirmed preservation/re-sync of pending attempts and local packs.
