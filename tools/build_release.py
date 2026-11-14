"""Build a deterministic tar.gz application release and signed canonical manifest."""

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from packaging.version import Version

from app import __version__
from app.update.manifest import canonical_manifest_bytes


def _files(root: Path) -> list[Path]:
    files = [root / "pyproject.toml", root / "setup.py", root / "README.md"]
    for directory in (root / "app", root / "schemas", root / "tools"):
        for path in directory.rglob("*"):
            relative = path.relative_to(root)
            if not path.is_file() or path.is_symlink() or any(
                part.startswith(".") or part == "__pycache__" for part in relative.parts
            ):
                continue
            if path.name in {"approve_pairing.py", "revoke_device.py"}:
                continue
            if (path.suffix == ".py"
                or relative.parent == Path("app/data/migrations") and path.suffix == ".sql"
                or relative.parent == Path("schemas") and path.suffix == ".json"
                or relative.is_relative_to("app/ui_qt/qml")
                and (path.suffix in {".qml", ".svg"} or path.name == "qmldir")
                or relative.is_relative_to("app/ui_qt/assets") and path.suffix == ".svg"
            ):
                files.append(path)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def build_artifact(root: Path, output: Path, version: str) -> None:
    entries = []
    for path in _files(root):
        name = path.relative_to(root).as_posix()
        data = path.read_bytes()
        if name == "app/version.py":
            data = f'"""Canonical semantic application version."""\n\n__version__ = "{version}"\n'.encode()
        entries.append((name, data))
    entries.append(("release.json", json.dumps({"version": version}, sort_keys=True, separators=(",", ":")).encode()))
    with output.open("wb") as raw, gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed, tarfile.open(fileobj=compressed, mode="w") as archive:
        for name, data in sorted(entries):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = 0
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(data))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default=__version__)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/update"))
    parser.add_argument("--key-id", default="development-1")
    parser.add_argument("--platform", default="linux")
    parser.add_argument("--architecture", default="aarch64")
    parser.add_argument("--min-supported-version", default=__version__)
    parser.add_argument("--required-db-schema", type=int, default=8)
    parser.add_argument("--notes", default="Questraa device software update")
    args = parser.parse_args()
    Version(args.version)
    args.output.mkdir(parents=True, exist_ok=True)
    filename = f"assessment-device-{args.version}.tar.gz"
    artifact = args.output / filename
    build_artifact(Path.cwd(), artifact, args.version)
    manifest = {
        "schema_version": 1,
        "signing_key_id": args.key_id,
        "release": {"version": args.version, "channel": "stable", "created_at": datetime.now(UTC).isoformat(), "min_supported_version": args.min_supported_version, "required_db_schema": args.required_db_schema, "notes": args.notes},
        "artifact": {"filename": filename, "size_bytes": artifact.stat().st_size, "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()},
        "compatibility": {"platform": args.platform, "architecture": args.architecture},
    }
    canonical = canonical_manifest_bytes(manifest)
    private = serialization.load_pem_private_key(args.private_key.read_bytes(), password=None)
    if not isinstance(private, Ed25519PrivateKey):
        raise SystemExit("Update signing key must be an Ed25519 private key")
    (args.output / "update-manifest.json").write_bytes(canonical)
    (args.output / "update-manifest.sig").write_bytes(private.sign(canonical))
    print(f"Signed release built: {artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
