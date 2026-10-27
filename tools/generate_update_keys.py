"""DEVELOPMENT ONLY: generate an Ed25519 update signing/verification key pair."""

import argparse
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, default=Path("var/update-keys/dev.update-private.pem"))
    parser.add_argument("--public", type=Path, default=Path("var/update-keys/dev.update-public.pem"))
    args = parser.parse_args()
    if args.private.exists() or args.public.exists():
        raise SystemExit("Refusing to overwrite an existing update key")
    args.private.parent.mkdir(parents=True, exist_ok=True)
    args.public.parent.mkdir(parents=True, exist_ok=True)
    private = Ed25519PrivateKey.generate()
    args.private.write_bytes(private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    args.public.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    os.chmod(args.private, 0o600)
    print("Development update keys generated. PRIVATE UPDATE SIGNING KEY — DO NOT COMMIT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
