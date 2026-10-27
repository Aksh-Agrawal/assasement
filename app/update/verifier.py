"""Verify signed metadata and artifact bytes before any extraction."""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from packaging.version import Version

from app.update.errors import CompatibilityError, IntegrityError, SignatureError
from app.update.manifest import UpdateManifest

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class VerifiedUpdate:
    manifest: UpdateManifest
    artifact: Path


def verify_update(
    manifest_bytes: bytes,
    signature: bytes,
    artifact: Path,
    *,
    trusted_keys: dict[str, Ed25519PublicKey],
    current_version: str,
    platform: str,
    architecture: str,
    db_schema: int,
    allow_downgrade: bool = False,
) -> VerifiedUpdate:
    manifest = UpdateManifest.parse(manifest_bytes)
    key_id = manifest.data["signing_key_id"]
    key = trusted_keys.get(key_id)
    if key is None:
        raise SignatureError("Manifest signing key is not trusted")
    try:
        key.verify(signature, manifest.canonical_bytes)
    except InvalidSignature as error:
        LOGGER.warning("update verification failed category=signature")
        raise SignatureError("Manifest signature is invalid") from error
    expected = manifest.data["artifact"]
    if artifact.name != expected["filename"]:
        raise IntegrityError("Update artifact filename mismatch")
    try:
        actual_size = artifact.stat().st_size
    except OSError as error:
        raise IntegrityError("Update artifact is unavailable") from error
    if actual_size != expected["size_bytes"]:
        raise IntegrityError("Update artifact size mismatch")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if digest != expected["sha256"]:
        raise IntegrityError("Update artifact SHA-256 mismatch")
    current = Version(current_version)
    if manifest.version == current:
        raise CompatibilityError("Update version is already installed")
    if manifest.version < current and not allow_downgrade:
        raise CompatibilityError("Update downgrade is not permitted")
    if current < Version(manifest.data["release"]["min_supported_version"]):
        raise CompatibilityError("Installed version is below the supported upgrade path")
    compatibility = manifest.data["compatibility"]
    if compatibility != {"platform": platform, "architecture": architecture}:
        raise CompatibilityError("Update target is incompatible with this device")
    if manifest.data["release"]["required_db_schema"] > db_schema:
        raise CompatibilityError("Required database schema is not installed")
    LOGGER.info("update verification succeeded version=%s key_id=%s", manifest.version, key_id)
    return VerifiedUpdate(manifest, artifact)
