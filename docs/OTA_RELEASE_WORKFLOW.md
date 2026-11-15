# Questraa Raspberry Pi OTA release workflow

A push to `main` validates the device source. **It does not publish an OTA update.** Pushing a matching version tag such as `v0.1.3` triggers the release workflow. The update becomes available through the device catalog only after validation, signing, GitHub Release creation, and cloud publication succeed.

This guide covers the device repository `Aksh-Agrawal/assasement` and an already provisioned Raspberry Pi running Raspberry Pi OS 64-bit (ARM64), Python 3.13, and the PySide6/Qt Quick kiosk. The standard managed app root is `/opt/questraa-device` and the standard persistent data root is `/var/lib/assessdev`. Use the effective paths on devices configured differently. The examples use `0.1.2 → 0.1.3` for illustration.

## 1. Release milestones

| Step | What it does | Evidence |
| --- | --- | --- |
| Develop and commit | Records reviewed changes in Git. Ordinary commits can retain the installed release version. | Reviewed commit and clean worktree. |
| Push ordinary changes to `main` | Validates merged development commits without publishing an OTA release. | Source checks for the new `main` commit. |
| Update the application version and merge the release candidate | Sets the version the app and newly installed package will report. Wait for validation of this final `main` commit before tagging. | `app/version.py` has the intended version and ARM64 validation is green for the exact candidate commit. |
| Create an annotated tag | Associates `v<NEXT_VERSION>` with the validated commit locally. | Local tag resolves to the intended commit. |
| Push the single release tag | Starts validation on the tagged revision and checks tag/version parity. | The tag exists on GitHub and the tag-triggered workflow is visible. |
| Validate and sign | Builds a deterministic source archive and signs the generated manifest using the production Ed25519 key after validation passes. | The signed-artifact verification step succeeds. |
| Publish GitHub Release | Attaches the archive, manifest, and detached signature to the versioned release. | All three assets are present under the intended tag. |
| Publish to the cloud catalog | Uploads the signed bundle to the authenticated cloud admin API. | The workflow logs `Published Questraa <NEXT_VERSION> to the authenticated device catalog` and the exact version is recorded in that catalog. |
| Install through the Pi UI | Uses the device credential to check and download, verifies the bundle, and hands installation to systemd. | Managed `current` selects the expected version and the updater records `successful`. |
| Verify on the Pi | Confirms the running kiosk, assessment data, and sync behavior. | SSH and functional checks in section 5 pass on a pilot device. |

## 2. Pre-release checklist

### Required for every release

- [ ] Confirm the repo and branch, fetch `origin`, review the intended changes, and inspect staged, unstaged, untracked, and ignored files. At tagging time, the worktree and index must be clean and `HEAD` must match the fetched `origin/main`.
- [ ] Review staged filenames and patch content for private signing keys, tokens, passwords, `.env` files, credential JSON, SQLite files and WAL/SHM sidecars, logs, virtual environments, or generated artifacts. Keep those files out of Git. The offline gate checks for private key material in the source tree, and the staged review covers other kinds of credentials and data.
- [ ] Run Ruff, the device regression suite, the offline readiness gate, Git diff checks, and the isolated Qt startup smoke test. Review the reports and wait for green checks on the exact `main` commit before tagging.
- [ ] Check `app/version.py`, package metadata, the intended tag, and workflow compatibility values. Review the supported installed-version range and SQLite schema floor. Confirm the candidate version is newer than the deployed version and unused in GitHub and the target catalog.
- [ ] Confirm the release maintainer can create the tag under the repository ruleset. Confirm the signing secret and cloud publication configuration are available, and that the cloud and pilot Pi trust the matching public key.
- [ ] Confirm the pilot uses 64-bit Linux, reports `aarch64`, and uses Python 3.13 with its native Qt libraries. Check free disk space and inodes for the app tree, persistent data, and temporary work. The helper checks at least four times the artifact size plus 300,000,000 bytes free on the app filesystem. Allow additional headroom for the per-release virtual environment, dependency downloads, and SQLite backups.
- [ ] Confirm device API access and supported upgrade paths. Record the pilot's account/profile, offline content, recent History and Analytics, and queued or failed sync state before it installs.

### Additional gates for changes that affect compatibility

| Change | Additional check |
| --- | --- |
| Authentication, authorization, signing, or catalog | Exercise download and lookup against an isolated cloud environment with real test credentials. Confirm device and cloud trust the expected public key and key ID, the authorized publication path still works, and invalid or revoked credentials and tampered bundles fail as expected. Coordinate trust changes before tagging. |
| Device-cloud API or sync | Run affected integration tests with the companion cloud source and its test dependencies. Exercise old-device/new-cloud and new-device/deployed-cloud combinations as applicable. Include offline pending attempts, process restart, retry after a lost acknowledgement, correct profile attribution, and no duplicate attempts. |
| SQLite or assessment persistence | Test upgrades from a representative copy of each supported installed schema. Verify profiles, pinned packs, attempts, answers, confidence, History, settings, and pending sync records survive. Open the migrated copy with the previous app, check integrity and representative workflows, and verify the previous app can use rows the new app writes. |
| Updater, service units, or dependencies | Test with the helper actually installed on the oldest supported Pi, then test on a disposable ARM64 pilot. Exercise constrained storage, interrupted dependency download, SQLite/Qt probe failure, activation failure, power interruption, and rollback without losing new attempts or pending sync. Confirm wheels and native libraries on Raspberry Pi OS. Changes to systemd units and launch scripts require a separately reviewed provisioning plan because the OTA archive does not contain `scripts/`. |

The `--offline` readiness gate runs on isolated state. It covers SQLite, local assessment and content, sync retention, signed updates, and recovery tests. It skips live cloud and PostgreSQL checks. For conditional integration work, use the companion cloud test setup and a disposable test database. [Device-cloud contract](DEVICE_CLOUD_CONTRACT.md) · [Offline readiness checks](RELEASE_CHECKLIST.md)

## 3. Prepare, validate, and tag from Windows PowerShell

### A. Inspect the checkout

```powershell
Set-Location C:\folder\mainfolder\startup
git status
git status --short --untracked-files=all
git status --short --ignored=matching
git branch --show-current
git remote get-url origin
git fetch origin
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed. Verify GitHub access before proceeding.' }
git status --short --branch
git log --oneline --left-right HEAD...origin/main
Get-Content .\app\version.py
```

Expect `origin` to point to `Aksh-Agrawal/assasement`. Review local changes before staging anything. Resolve any branch divergence through the normal review and merge process. A release tag must point at the final candidate on `main`.

### B. Update the version

Edit only the `__version__` assignment in `app/version.py` for the version bump. For example, change `__version__ = "0.1.2"` to `__version__ = "0.1.3"` as part of a future release.

| Surface | Expected value for the example |
| --- | --- |
| `app/version.py` | Canonical runtime version `0.1.3`. `app.__version__` exposes it. |
| `pyproject.toml` | Setuptools reads the version dynamically from `app.version.__version__`. Leave that mapping in place. |
| Git tag | Annotated `v0.1.3`, pointing to the reviewed commit. |
| Signed manifest and artifact | `update-manifest.json` has `release.version` equal to `0.1.3`. The archive is `assessment-device-0.1.3.tar.gz` and contains `release.json` with `{"version":"0.1.3"}` and the corresponding application version. |

Use three numeric components without suffixes. The manifest schema and install request require that form. The workflow validates that the tagged source version agrees with the tag before passing it to the builder. [Version source](../app/version.py) · [Package metadata](../pyproject.toml) · [Manifest schema](../schemas/update_manifest.schema.json)

### C. Run local verification

Use a Python 3.13 virtual environment with the `dev` and `gui` extras installed. The commands use its interpreter directly. Open a disposable PowerShell session for these checks so the test environment settings remain scoped to that shell. Stop at the first failure.

```powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe -ErrorAction Stop).Path
& $python --version
& $python -c 'import sys; assert sys.version_info[:2] == (3, 13), sys.version'
if ($LASTEXITCODE -ne 0) { throw 'Use a Python 3.13 virtual environment for release checks.' }

# Install or refresh the editable package after the version bump.
& $python -m pip install -e '.[dev,gui]'
if ($LASTEXITCODE -ne 0) { throw 'Project dependency installation failed.' }

git diff --check
if ($LASTEXITCODE -ne 0) { throw 'Fix unstaged whitespace errors.' }
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Fix staged whitespace errors.' }

$env:QT_QPA_PLATFORM = 'offscreen'
$env:ASSESS_LOG_DIR = Join-Path ([IO.Path]::GetTempPath()) "questraa-ota-logs-$([guid]::NewGuid())"
& $python -m ruff check .
if ($LASTEXITCODE -ne 0) { throw 'Ruff failed.' }
& $python -m pytest -q -m 'not cloud_integration'
if ($LASTEXITCODE -ne 0) { throw 'Device tests failed.' }
& $python -m tools.release_check --offline
if ($LASTEXITCODE -ne 0) { throw 'Review artifacts/release-readiness.md before proceeding.' }
```

The offline gate writes `artifacts/release-readiness.md` and `artifacts/release-readiness.json`. Exit code `0` is a pass, `1` indicates warnings, and `2` means a required check failed. Keep the test logs outside the working tree. The repository currently tracks `var/log/assessment-device.log`, so a test run with default paths can dirty that file. A Windows runtime failure requires investigation and reproduction in a clean Python 3.13 environment. The ARM64 workflow supplies the target-side software evidence.

Run the Qt startup smoke test with disposable paths. It loads the QML app, exercises startup, and exits. The full signed-package installation smoke also runs in the ARM64 GitHub workflow.

```powershell
$releaseSmokeRoot = Join-Path ([IO.Path]::GetTempPath()) "questraa-ota-smoke-$([guid]::NewGuid())"
New-Item -ItemType Directory -Path $releaseSmokeRoot -ErrorAction Stop | Out-Null
$env:QT_QPA_PLATFORM = 'offscreen'
$env:ASSESS_DATA_DIR = $releaseSmokeRoot
$env:ASSESS_APP_ROOT = Join-Path $releaseSmokeRoot 'app'
$env:ASSESS_SQLITE_PATH = Join-Path $releaseSmokeRoot 'device.db'
$env:ASSESS_CREDENTIAL_PATH = Join-Path $releaseSmokeRoot 'credentials.json'
$env:ASSESS_PACK_DIR = Join-Path $releaseSmokeRoot 'packs'
$env:ASSESS_MEDIA_DIR = Join-Path $releaseSmokeRoot 'media'
$env:ASSESS_DOWNLOAD_DIR = Join-Path $releaseSmokeRoot 'downloads'
$env:ASSESS_LOG_DIR = Join-Path $releaseSmokeRoot 'log'
$env:ASSESS_UPDATE_DIR = Join-Path $releaseSmokeRoot 'update'
$env:ASSESS_UPDATE_INBOX = Join-Path $env:ASSESS_UPDATE_DIR 'inbox'
& $python -m app.ui_qt.main --db $env:ASSESS_SQLITE_PATH --smoke-test
if ($LASTEXITCODE -ne 0) { throw "Qt startup failed. Inspect $releaseSmokeRoot." }
```

### D. Review, commit, and get the candidate onto `main`

```powershell
git status --short --untracked-files=all
git diff --stat
git diff
git add -- app/version.py
# Stage each other reviewed file by its exact path. git add -p can stage tracked hunks.
git diff --cached --name-status
git diff --cached
git diff --cached --check
if ($LASTEXITCODE -ne 0) { throw 'Fix staged whitespace errors.' }
git commit -m 'Prepare Questraa device release 0.1.3'
if ($LASTEXITCODE -ne 0) { throw 'Commit failed.' }
git status --short --branch
```

If an unintended file is staged, use `git restore --staged -- path/to/file`, then review the index again. For a reviewed direct push from the local `main` branch, use `git push --no-follow-tags origin main`. If `main` is protected, push the release branch with `git push --no-follow-tags -u origin HEAD` and merge through the normal pull request checks. After merging, run `git switch main` and `git pull --ff-only origin main`. The `--no-follow-tags` flag prevents Git from including locally created annotated tags when `push.followTags` is enabled. Confirm the final `main` SHA and green **Publish signed Raspberry Pi release → validate** checks for that SHA in the Actions tab. This proves the merged source can be built and smoke-tested on ARM64 before the tag unlocks production signing. The tag-triggered run validates again. [GitHub Actions](https://github.com/Aksh-Agrawal/assasement/actions)

### E. Quick release cheat sheet

Run this from the repository after the steps above. Replace `<NEXT_VERSION>`. Review the displayed SHA and confirm the green **main** run for that SHA before typing the publication confirmation. The last command **intentionally triggers production OTA publication**.

```powershell
Set-Location C:\folder\mainfolder\startup
$version = '<NEXT_VERSION>'
if ($version -notmatch '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$') {
    throw 'Set the intended numeric MAJOR.MINOR.PATCH version.'
}
$tag = "v$version"
if ((git branch --show-current) -ne 'main') { throw 'Check out main first.' }
$dirty = git status --porcelain=v1 --untracked-files=all
if ($LASTEXITCODE -ne 0 -or $dirty) { throw 'The checkout must be clean.' }

git fetch origin
if ($LASTEXITCODE -ne 0) { throw 'Fetch failed.' }
$candidate = git rev-parse --verify HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve the candidate commit.' }
$remoteMain = git rev-parse --verify refs/remotes/origin/main
if ($LASTEXITCODE -ne 0 -or $candidate -ne $remoteMain) {
    throw 'The candidate must match origin/main.'
}

$python = (Resolve-Path .\.venv\Scripts\python.exe -ErrorAction Stop).Path
$sourceVersion = & $python -c 'from app import __version__; print(__version__)'
if ($LASTEXITCODE -ne 0 -or $sourceVersion -ne $version) { throw 'Tag/version mismatch.' }
git show-ref --verify --quiet "refs/tags/$tag"
if ($LASTEXITCODE -ne 1) { throw 'The local tag exists or the tag check failed.' }
git ls-remote --exit-code --refs origin "refs/tags/$tag"
if ($LASTEXITCODE -ne 2) { throw 'The remote tag exists or GitHub could not be verified.' }

git show --no-patch --oneline $candidate
if ($LASTEXITCODE -ne 0) { throw 'Cannot display the candidate commit.' }
if ((Read-Host "After verifying green main CI and release checks, type PUBLISH $tag") -cne "PUBLISH $tag") {
    throw 'Publication cancelled.'
}
git tag -a $tag $candidate -m "Questraa device $version"
if ($LASTEXITCODE -ne 0) { throw 'Tag creation failed.' }
git show --no-patch $tag
if ($LASTEXITCODE -ne 0) { throw 'Tag verification failed.' }
git push --no-follow-tags origin "refs/tags/${tag}:refs/tags/${tag}"
if ($LASTEXITCODE -ne 0) { throw 'Tag push failed. Check GitHub before retrying.' }
```

Push only the intended tag. Never force-move, delete and recreate, or reuse a published tag/version. A ruleset rejection needs a release maintainer with tag-creation access. If a push gives an ambiguous result, check the exact remote ref and its workflow before deciding whether to retry the same push. Changes to a tagged candidate require a new version and tag.

## 4. What GitHub Actions publishes

The device release workflow triggers on pushes to `main` and tags matching `v*.*.*`. The **validate** and **release** jobs use `ubuntu-24.04-arm` with Python 3.13. [Device release workflow](../.github/workflows/device-release.yml)

1. **Validate source.** Install native Qt libraries and `.[dev,gui]`. Assert `aarch64` and Python 3.13, and assert `v` plus the app version matches the ref on tag runs. Run `ruff check .`, `pytest -q -m 'not cloud_integration'`, and `python -m tools.release_check --offline`.
2. **Build an ephemeral-key package and test its installation.** Build and verify a signed test archive, extract it, install `[gui]` into a fresh venv, and run the Qt offscreen smoke test from a temporary runtime directory. Assert installed package metadata equals the application version and check SQLite schema `>= 9` and integrity. General CI also runs on pushes and PRs, including a separate device test workflow that runs unfiltered `pytest -q`. Use the native ARM64 validate job for the release gate.
3. **Produce and verify the production bundle.** The **release** job requires a tag and successful validation. `tools.build_release` creates the application archive without live data, writes the canonical manifest, and signs its exact canonical bytes with Ed25519. The manifest includes the stable channel, target, version gates, key ID, artifact filename, size, and SHA-256. `tools.verify_release` checks the signature, hash, and compatibility against the declared baseline using the corresponding public key. The tar.gz contains application code, migration and QML assets, schemas, selected tools, and packaging files.
4. **Publish GitHub Release assets.** The workflow attaches `assessment-device-<NEXT_VERSION>.tar.gz`, `update-manifest.json`, and `update-manifest.sig` to the tagged GitHub Release.
5. **Publish the same bundle to the cloud catalog.** The job logs in through `/api/v1/admin/auth/login` using a cookie session, checks `max_upload_bytes` via `/api/v1/admin/settings`, and posts the manifest and base64-encoded signature/artifact to `/api/v1/admin/releases`. It requires confirmation of the expected version with `status: published`. The Pi discovers the bundle from `/api/v1/device-updates/latest` and downloads `/api/v1/device-updates/<NEXT_VERSION>/artifact` using its own device credential.

| Setting | What to verify before tagging |
| --- | --- |
| GitHub secret `UPDATE_SIGNING_PRIVATE_KEY_B64` | Base64 of the complete Ed25519 private PEM for `questraa-stable-1`. Keep it in the release environment. |
| GitHub secrets `UPDATE_CLOUD_URL`, `UPDATE_ADMIN_EMAIL`, `UPDATE_ADMIN_PASSWORD` | Exact cloud API HTTPS origin and an authorized cloud admin account. The URL format excludes paths, queries, fragments, and embedded credentials. |
| GitHub variable `UPDATE_CLOUD_ORIGIN` | Exact allowed HTTPS request origin. The workflow defaults to `https://startup-cloud-1.onrender.com`. Confirm it is accepted by the deployed cloud's origin policy. |
| Cloud `RELEASE_PUBLIC_KEYS` | JSON object mapping `questraa-stable-1` to base64 of the **raw Ed25519 public key**. |
| Pi `ASSESS_UPDATE_PUBLIC_KEY` and `ASSESS_UPDATE_KEY_ID` | The matching PEM **public** key, normally `/etc/assessdev/update-public.pem`, and ID `questraa-stable-1`. A Pi trusts one configured key in this implementation. Plan coordinated device/cloud provisioning for key changes. |
| Cloud `MAX_UPLOAD_BYTES` and device download ceiling | The workflow checks the whole JSON body after base64 expansion. The device client separately caps the raw archive at 100,000,000 bytes. Review both limits if packaging grows. |

The workflow relies on repository tag restrictions for release authorization and declares no GitHub environment approval gate. Review protections and the exact tagged source before pushing a release. Keep credential values out of Git, documentation, shell history, and shared logs. [Release builder](../tools/build_release.py) · [Verifier](../tools/verify_release.py) · [GitHub Releases](https://github.com/Aksh-Agrawal/assasement/releases)

### Verify downloaded release assets

Download the three GitHub Release assets into a single directory. Use the deployment's trusted Ed25519 public PEM from a separate, trusted source. Run the following from the repository root with the verification dependencies installed. Replace the example values with the release version and the actual pilot's installed version and SQLite schema. This checks the bundle against the selected upgrade path without extracting or installing it.

```powershell
$python = (Resolve-Path .\.venv\Scripts\python.exe -ErrorAction Stop).Path
$assetDir = Read-Host 'Directory containing the three GitHub Release assets'
$publicKey = Read-Host 'Path to the trusted release public PEM'
$version = '0.1.3'
$installedVersion = '0.1.2'
$installedSchema = 9
& $python -m tools.verify_release `
    (Join-Path $assetDir 'update-manifest.json') `
    (Join-Path $assetDir 'update-manifest.sig') `
    (Join-Path $assetDir "assessment-device-$version.tar.gz") `
    --public-key $publicKey --current-version $installedVersion --platform linux `
    --architecture aarch64 --db-schema $installedSchema
if ($LASTEXITCODE -ne 0) { throw 'Release asset verification failed.' }
```

The CLI verifies the signature with the supplied PEM. Also check that `signing_key_id` in the verified manifest equals the pilot's configured key ID, normally `questraa-stable-1`. The device verifier enforces that mapping.

**Partial publication.** A tag or a visible GitHub Release is possible even if the catalog upload fails. Read the failed step and verify the deployed admin catalog before retrying, especially after a timeout or `409`. Cloud versions are immutable and the catalog can have committed even when the runner missed the reply. If the version is already present, compare its manifest and hash against the released assets. If only cloud publication is missing, have the authorized catalog operator publish the verified, unchanged GitHub bundle after correcting the cause. Use the [original tag run's retry controls](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs) for a transient or configuration failure once you have verified whether the catalog write occurred. A rerun rebuilds the manifest with a new timestamp and re-signs it, so coordinate any rerun that could replace published assets. Use a fresh version for a corrected bundle.

## 5. Install and verify on a Raspberry Pi

### Before installation

1. Confirm a one-time managed install exists, with the root-owned `current` link, the kiosk, updater and recovery units, and the intended public key and cloud API. For a device still running from a home checkout, inspect its effective data paths and follow the bootstrap runbook first. The bootstrap derives the legacy checkout from the script's repository unless explicitly overridden. Older bootstrap helper revisions may need the release-directory permission fix before their first OTA. [One-time setup and older helper check](SOFTWARE_UPDATER_IMPLEMENTATION.md)
2. Use a pilot first. Choose a maintenance window with steady power and internet, ensure no assessment is active, and record the old version plus the data and sync baseline from section 2. Retain a verified SQLite-aware backup and preserve device credentials separately with restricted access. Check the actual DB/credential locations on customized devices. The update service takes its own activation backup.
3. Check OS architecture, system Python and storage. The native updater makes its venv with `/usr/bin/python3`. Confirm the Pi can reach the device catalog and package index, and has a valid device pairing.

```sh
uname -m
/usr/bin/python3 --version
df -h /opt/questraa-device /var/lib/assessdev /tmp
df -i /opt/questraa-device /var/lib/assessdev /tmp
systemctl is-active assessdev-ui.service
systemctl status assessdev-update.service assessdev-recover.service --no-pager
```

Expect `aarch64`, Python `3.13.x`, and an active kiosk. The update service runs on demand and is normally inactive while idle.

The standard units read `/etc/assessdev/device.env`. The updater and recovery units also read the root-only `/etc/assessdev/updater.env` and invoke the standalone helper at `/usr/local/libexec/assessdev-updater.py`. The installer renders the service account and paths into the units. Keep configuration and live data outside the versioned release directories. Review effective settings locally and share only redacted diagnostics. [Installer](../scripts/install_updater.sh)

### Install in the kiosk

Open **Settings → Software Update → Check for Updates → Download & Install**. Confirm the expected newer version before installing. The UI downloads and verifies the application archive, then hands the staged request to `assessdev-update.service`. The UI defers the handoff while an assessment is active. Keep the maintenance window clear of new assessments after the handoff because the updater can restart the kiosk when preparation finishes. Let the updater complete. The normal path restarts the kiosk service automatically. The base OS, firmware, and content packs have separate update paths.

### Verify over SSH

Use the default installation paths in these read-only checks or substitute the configured paths.

```sh
readlink -f /opt/questraa-device/current
cat /opt/questraa-device/current/release.json
sudo cat /var/lib/assessdev/update/status.json
systemctl is-active assessdev-ui.service
sudo /opt/questraa-device/current/.venv/bin/python -I -c 'from app import __version__; print(__version__)'
```

| Check | Expected after a successful install |
| --- | --- |
| Managed `current` target and `release.json` | `/opt/questraa-device/releases/<NEXT_VERSION>` and `{"version":"<NEXT_VERSION>"}`. |
| `update/status.json` | `"state": "successful"` and `"version": "<NEXT_VERSION>"`. An interrupted install that recovers can also report `successful` with a recovery detail. |
| `assessdev-ui.service` | `active`. The kiosk opens normally and stays up. |
| Package and Settings version | The selected package import reports `<NEXT_VERSION>`. **Current version** in the reopened Software Update screen reports the same version and that version is no longer offered for installation. |

Finish the pilot confirmation on the display.

- Open the existing student account and linked profile. Confirm the expected profiles, downloaded packs, and representative saved assessment History and answer reviews.
- Compare recent Analytics and accuracy to the baseline. Open an offline pack and complete a short assessment on a test profile with the network disconnected. Confirm the result appears in History and survives a normal app restart if restart persistence is part of the pilot check.
- Check Sync status before reconnecting. Confirm the queued test attempt and any baseline pending entries are retained or already reconciled. Reconnect and confirm device-cloud connectivity and sync of the test attempt once under the correct profile. Check the previous successfully synced History remains available.
- Record the tag SHA, GitHub Release, catalog confirmation, service/active release results, and pilot acceptance. ARM64 CI smoke and systemd `active` each cover only part of what the physical pilot verifies.

## 6. Troubleshooting

### A. New update is missing

1. **Check the tag and workflow.** A main push or a local-only tag cannot publish the update. On GitHub, inspect the expected annotated tag and its Actions run. Check for tag ruleset rejection, tag/version mismatch, and failed validation or signing.
2. **Check actual cloud publication.** A GitHub Release can exist on its own. Confirm the cloud publication log names the correct version and the Pi points to the same environment. Investigate admin login/Origin, upload limit, or manifest/trust errors in the failed step. The device client treats `404` from the latest endpoint as no available update, so also confirm the deployed backend serves that route. In the current cloud source, the catalog returns the most recently published database release. The Pi applies its own version and compatibility checks.
3. **Check compatibility.** Compare the Pi's installed version with the manifest's minimum, SQLite's installed schema with the schema floor, and target with `linux/aarch64`. Current/same and older versions are filtered out. The UI can show a newer incompatible manifest and disable installation. Check signer/key configuration if installation rejects an otherwise compatible candidate.
4. **Check pairing and connectivity.** `401/403` means update authentication failed. Use the existing device pairing/account workflow to check pairing, and verify network, DNS, TLS, and API origin. Keep credential values out of diagnostics.
5. **Refresh the UI.** Select **Check for Updates** again after the active operation settles. A successful fresh check replaces the in-memory manifest. If the current process is older than the active release, finish the restart and compare the three version signals in section 5.

### B. The download finishes but installation fails

Check the service logs first. The UI's **Download & Install** label covers both the cloud archive download and a separate pip dependency installation on the Pi.

```sh
sudo journalctl -u assessdev-update.service -n 150 --no-pager
sudo systemctl status assessdev-update.service assessdev-recover.service assessdev-ui.service --no-pager
sudo journalctl -u assessdev-ui.service -u assessdev-recover.service -b -n 150 --no-pager
sudo cat /var/lib/assessdev/update/status.json
```

| Evidence | What to check next |
| --- | --- |
| UI download timeout, truncated archive, or HTTP error before an install request | Check the device app log and cloud access. Check the published manifest and artifact sizes and confirm storage can serve the artifact. Ordinary download failures remove the partial file. A later retry can reuse a complete cached artifact after verification. |
| `ReadTimeout`, interrupted wheel download, or pip `CalledProcessError` / `TimeoutExpired` | Identify the pip subprocess and package in the updater journal. For a `PySide6-Essentials` download timeout, see the next section. A missing compatible distribution or build failure calls for checking Python 3.13, aarch64 wheel availability, native Qt libraries, and the package index. |
| Insufficient storage or `No space left on device` | Check `df` for the app root, data root, and temporary filesystem. Retained releases, per-version venvs, and backups consume space. Preserve the active and prior release and diagnostic/data files while resolving capacity. |
| `ManifestError`, `SignatureError`, or `IntegrityError` | Check the released manifest against the signed assets, the device's configured public key/key ID, and the archive size and SHA-256. Both the UI and privileged helper verify the bundle before extraction in their respective staging areas. |
| Migration probe fails or reports changed protected rows | Reproduce on a disposable SQLite copy with both the candidate and prior releases. Check migration compatibility, integrity, and preserved data including sync metadata. The probe captures subprocess output, so its journal message can be generic. |
| Qt startup probe fails | Reproduce the offscreen startup on a clean, disposable runtime to inspect detailed QML/plugin errors. Check native libraries, packaged QML resources and Python dependencies. |
| Updated kiosk starts then exits or fails health checks | Read the UI service journal for display/Qt, permissions, SQLite, or process restart errors. The helper checks that the service stays active with a stable new main PID. A systemd service can exit normally after performing a rollback, so check `current` and the status file too. |
| `That release version is already installed` while `current` still points to the previous version | The version directory can remain after a failed activation. Reconcile the selected version, retained directories, and transaction record with the device operator. Repeatedly pressing Install will encounter the existing directory. |

### C. PySide6-Essentials download timeout

The OTA tarball contains application source. During installation the Pi creates a new venv and runs pip for `.[gui]`, which can fetch a large `PySide6-Essentials` wheel. If the journal shows an interrupted wheel download on an otherwise functioning network, an operator can increase pip's socket timeout and download-resumption retries for this service. The helper still passes `--retries 2` for connection attempts, disables pip's cache, and limits pip installation to 1,200 seconds. The systemd update unit has a 1,800-second service startup timeout. Older pip in the newly created venv may lack download-resumption support, so inspect the relevant Python's pip/venv provisioning when diagnosing. [pip options](https://pip.pypa.io/en/stable/cli/pip/) · [pip changelog](https://pip.pypa.io/en/stable/news/)

When the updater service is idle, run `sudo systemctl edit assessdev-update.service`. Add these lines to the editable drop-in, above the commented unit reference. The default drop-in is `/etc/systemd/system/assessdev-update.service.d/override.conf`.

```ini
[Service]
Environment="PIP_TIMEOUT=120"
Environment="PIP_RESUME_RETRIES=12"
```

```sh
sudo systemctl daemon-reload
systemctl show assessdev-update.service --property=DropInPaths
/usr/bin/python3 -m ensurepip --version
```

Confirm systemd shows the drop-in. `ensurepip --version` reports the bundled pip for a newly created venv. Then retry from the kiosk during the maintenance window. These settings can help with transient network stalls. A missing wheel, sustained network outage, storage problem, or elapsed updater timeout still requires its own fix.

### D. The UI says failed after installation appears to have succeeded

Compare the active `current` link and its `release.json`, the kiosk's **Current version**, and the updater's `status.json`. Those values represent the selected release, the version imported into the running process, and the last updater outcome, respectively. `current_release.json` records activation/rollback bookkeeping. The live selection is the managed symlink. Use the journal timestamps and status file modification time to distinguish the last attempt from an older error.

The current QML reads the running version and the controller checks trusted active release metadata. A mismatch can show **Active release** and **Restart required to load the active release** while the old process is still alive. The controller suppresses cached offers at or below the selected version and ignores the prior status file revision for a fresh operation. It clears the UI error when the selected version matches a successful status. An older kiosk build can show a stale offer or outdated version, and some failures write an empty version to `status.json` with only the exception category.

- If the target and `successful` status agree but the display is old, verify the updater has finished and that the managed kiosk is the process on screen. Review the kiosk journal and arrange a controlled kiosk restart if needed, after any assessment ends. Reopen Software Update and recheck.
- If the target remains the previous version or status is `rolled_back`, inspect the journals and treat it as an unsuccessful activation. If the link selects the new version but status remains `failed` or `installing`, reconcile the transaction, helper, and kiosk logs before trying another install.

[QML update screen](../app/ui_qt/qml/screens/SoftwareUpdateScreen.qml) · [Settings controller](../app/ui_qt/controllers/settings_controller.py)

### E. Interrupted installation and rollback

- **Before activation:** The active code stays selected while the privileged helper re-verifies, extracts, installs dependencies in a separate venv, probes a copy of the database with the candidate and prior package, and smoke-tests Qt with disposable state. The migration probe compares protected student/content/sync rows. A failure at these checks leaves the currently selected release in place.
- **During activation:** The helper stops the kiosk, stores an SQLite online backup and a credential copy when present, writes a transaction record, switches `current` atomically, and starts the kiosk. After the health check passes, it refreshes the standalone helper from the signed release. If startup, the health check, or the helper refresh fails after activation begins, the helper attempts to restore the previous code selection and restart it. The original app files and its venv remain in the previous release directory.
- **At boot after an interruption:** `assessdev-recover.service` runs before the kiosk. For an `installing` status, it inspects the transaction and selected version. If activation never switched the release, it records failure and keeps the old release. If the new release is selected, it smoke-tests the candidate and completes recovery if it passes or restores the previous release if it fails. An inconsistent selection/transaction or a failed recovery unit needs operator diagnosis before the kiosk can start.
- **Data during rollback:** Existing live SQLite and credential files stay in place, including changes made after the backup. The helper uses backups only for missing files. It does not downgrade the schema. Backups are under `/var/lib/assessdev/backups/` by default and are retained. App rollback depends on the previous version being able to use the migrated database.
- **Operator response:** Preserve the live DB and any WAL/SHM files, credential file, backups, `transaction.json`, releases, and service journals. Use the supported managed recovery path and escalate inconsistent state. Avoid deleting data or update records, manually repointing the symlink, reinstalling from a Git checkout, or bypassing signature validation.

[Privileged updater and recovery](../tools/updater_service.py) · [Update unit](../scripts/systemd/assessdev-update.service) · [Recovery unit](../scripts/systemd/assessdev-recover.service)

## 7. Versioning and compatibility

| Change type | Example |
| --- | --- |
| Small compatible bug fix | `0.1.2 → 0.1.3` |
| Backward-compatible feature | `0.1.3 → 0.2.0` |
| Breaking compatibility change | Deliberately plan migration, cloud/device sequencing, the oldest supported starting version/schema, and a rollback or forward-recovery path before selecting a version. |

The workflow currently targets `linux/aarch64`, passes `--min-supported-version 0.1.0` and `--required-db-schema 8` in both builds, and verifies against that baseline. The current migration files reach schema `9`. The schema floor is the database version a device must already meet **before** installation. The candidate can migrate it further. Review both build invocations, their matching verifier arguments and the smoke-test schema assertion when a compatibility requirement changes. Select the lowest baseline the real upgrade paths support. If devices are below it, plan a vetted intermediate upgrade or a maintenance migration before publishing, since the client checks the catalog's latest manifest.

SemVer expresses change intent. Prove migration and rollback compatibility with representative data and the prior release. Prefer additive migrations that preserve existing reads and writes, including newly saved attempts and pending sync rows.

## 8. Final sign-off

- [ ] Candidate version and commit match the annotated tag. ARM64 validation is green for `main` and the tag.
- [ ] The versioned GitHub Release has all three assets and the catalog confirms the same signed release.
- [ ] Pilot device selects and runs the intended version. Kiosk startup, account/profile, History, Analytics, offline practice, and sync checks pass.
- [ ] Record the old/new versions, candidate SHA, Actions run, catalog confirmation, pilot result, and any operator follow-up.

Use this guide for future production OTA releases. The older [manual deployment procedure](SOFTWARE_RELEASE.md) describes copying code to `/opt/assessment-device`. The [laptop update architecture](UPDATES.md) uses a metadata-based activation simulator. The [updater implementation notes](SOFTWARE_UPDATER_IMPLEMENTATION.md) still describe the one-time provisioning path and historical behavior. For a managed Pi, the routine update uses the cloud catalog and the systemd-controlled `/opt/questraa-device/current` selection.
