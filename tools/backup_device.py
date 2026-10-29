"""Create a private WAL-safe database/state backup in a new directory."""
import argparse
import getpass
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

from app.config import AppConfig
from tools.pilot_inventory import inventory


def backup(database: Path, destination: Path, *, credentials: Path | None = None):
    if not database.is_file():
        raise FileNotFoundError("Existing database required")
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    if os.name == "nt":
        subprocess.run(["icacls", str(destination), "/inheritance:r", "/grant:r",
                        getpass.getuser() + ":(OI)(CI)F"], check=True, capture_output=True)
    output = destination / "assessment-device.db"
    # SQLite's backup API includes committed WAL pages; no migrations or checkpoint needed.
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as source:
        with sqlite3.connect(output) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise ValueError("Backup integrity check failed")
    os.chmod(output, 0o600)
    files = [output]
    if credentials and credentials.is_file():
        saved = destination / "device_credentials.json"
        with saved.open("xb") as target:
            os.chmod(saved, 0o600)
            with credentials.open("rb") as source:
                shutil.copyfileobj(source, target)
        files.append(saved)
    manifest = {"status": "complete", "inventory": inventory(output),
                "files": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--db", type=Path, default=config.database_path)
    parser.add_argument("--credentials", type=Path, default=config.credential_path)
    args = parser.parse_args()
    try:
        backup(args.db, args.destination, credentials=args.credentials)
        print("Backup complete; integrity verified. Keep the private directory operator-only.")
        return 0
    except Exception as error:
        print("Backup incomplete: " + type(error).__name__)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
