"""Verify a signed release without extracting or installing it."""

import argparse
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app import __version__
from app.update.manifest import UpdateManifest
from app.update.verifier import verify_update


def verify_files(args: argparse.Namespace):
    manifest_bytes = args.manifest.read_bytes()
    parsed = UpdateManifest.parse(manifest_bytes)
    public = serialization.load_pem_public_key(args.public_key.read_bytes())
    if not isinstance(public, Ed25519PublicKey):
        raise SystemExit("Trusted update key must be an Ed25519 public key")
    return verify_update(
        manifest_bytes,
        args.signature.read_bytes(),
        args.artifact,
        trusted_keys={parsed.data["signing_key_id"]: public},
        current_version=args.current_version,
        platform=args.platform,
        architecture=args.architecture,
        db_schema=args.db_schema,
        allow_downgrade=args.allow_downgrade,
    )


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("manifest", type=Path)
    parser.add_argument("signature", type=Path)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--current-version", default=__version__)
    parser.add_argument("--platform", default="development")
    parser.add_argument("--architecture", default="any")
    parser.add_argument("--db-schema", type=int, default=2)
    parser.add_argument("--allow-downgrade", action="store_true")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    return parser.parse_args()


def main() -> int:
    verified = verify_files(arguments())
    print(f"Release {verified.manifest.version}: manifest, signature, hash, and policy valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
