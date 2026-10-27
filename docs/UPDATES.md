# Signed application updates

Phase 10C implements a laptop-testable application-update architecture. It does not reboot a Pi,
swap system services, update firmware/OS images, or force installation.

## Version and manifest policy

`app/version.py` is the canonical version source and uses `MAJOR.MINOR.PATCH`: MAJOR is an
incompatible release, MINOR is a backward-compatible feature, and PATCH is a compatible fix.
Comparisons use `packaging.version.Version`, never string ordering.

The Draft 2020-12 schema at `schemas/update_manifest.schema.json` defines manifest version 1. The
signed fields include release version/channel/time, minimum supported installed version, required
device DB schema, artifact filename/size/SHA-256, development platform/architecture, and signing
key ID. `min_supported_version` means the currently installed application must be at least that
version for the declared upgrade path. Same-version installs and downgrades are rejected by
default; downgrade requires an explicit development/recovery override.

## Signing and key separation

Canonical JSON is UTF-8 with sorted keys and compact separators. The release environment signs
those exact bytes using Ed25519; the signed manifest contains the artifact SHA-256. Devices contain
only trusted public verification keys. The private signing key must remain in the release
environment and is ignored by Git. `signing_key_id` permits a future transition where old and new
public keys overlap before an old key is retired.

Verification order is schema, signature, filename/size, SHA-256, semantic version, platform and
architecture, then DB compatibility. Extraction cannot occur before all checks succeed.

## Packaging, download, and staging

The artifact is a deterministic `tar.gz` containing `app/`, schemas, dynamic package metadata, and
`release.json`; it excludes databases, credentials, environment files, logs, caches, Git data, and
test output. Downloads use authentication from Phase 10A, timeouts, a declared-size boundary, a
hard maximum, and a `.part` file removed on interruption.

Verified archives stage through a temporary directory and atomic rename. Absolute paths, parent
traversal, Windows drive paths, symlinks, and hard links are rejected. The running application is
never overwritten file-by-file.

## Activation, health, and rollback

Cross-platform activation uses versioned `releases/<version>/` directories and atomically written
`current_release.json` rather than requiring Windows symlinks. Metadata records current, previous,
staged, and status. A health-check callback validates a newly selected release. Failure immediately
restores the prior current version and records `rolled_back`; successful activation retains the old
version as previous.

Device database migrations must be backward-compatible whenever possible and run only during
controlled activation. Columns must not be destructively removed while rollback remains possible.
Code rollback after an incompatible forward-only migration is unsafe; manifests therefore declare
their required DB schema. Phase 10C performs no destructive schema rollback.

## Development commands

```powershell
python -m tools.generate_update_keys
python -m tools.build_release --version 0.2.0 --private-key var/update-keys/dev.update-private.pem
python -m tools.verify_release dist/update/update-manifest.json dist/update/update-manifest.sig dist/update/assessment-device-0.2.0.tar.gz --public-key var/update-keys/dev.update-public.pem
python -m tools.simulate_update dist/update/update-manifest.json dist/update/update-manifest.sig dist/update/assessment-device-0.2.0.tar.gz --public-key var/update-keys/dev.update-public.pem --current-release <existing-release-directory>
```

Never copy `*.update-private.pem` to a device. Update check/download/verification failures are
logged by category without credentials, authorization headers, private keys, or payload contents,
and never affect offline assessment execution.
