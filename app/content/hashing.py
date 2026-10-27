"""Deterministic exact-byte hashes for question-pack integrity checks."""

import hashlib
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase hexadecimal SHA-256 digest of exact bytes."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Stream a file into SHA-256 without loading a second copy into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
