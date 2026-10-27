"""Create a redacted support archive without databases, credentials, or answers."""

import argparse
import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.diagnostics import redact_text
from tools.diagnose import collect


def create_support_bundle(
    *,
    database_path: Path,
    credential_path: Path,
    log_directory: Path,
    update_root: Path,
    output_directory: Path,
    trusted_key_id: str,
    now: datetime | None = None,
) -> Path:
    status = collect(
        SimpleNamespace(
            db=database_path,
            credentials=credential_path,
            base_url=None,
            update_root=update_root,
            trusted_key_id=trusted_key_id,
            connect_timeout=5.0,
            read_timeout=15.0,
            network=False,
        )
    )
    credential = CredentialStore(credential_path).load_safe()
    secrets = tuple(
        value
        for value in (
            credential.token if credential else None,
            os.environ.get("DATABASE_URL"),
            os.environ.get("TEST_DATABASE_URL"),
        )
        if value
    )
    timestamp = (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y%m%d-%H%M%S")
    output_directory.mkdir(parents=True, exist_ok=True)
    destination = output_directory / f"support-bundle-{timestamp}.zip"
    diagnostic_text = redact_text(
        json.dumps(status, sort_keys=True, indent=2), secrets=secrets
    )
    manifest = {
        "schema_version": 1,
        "created_at": (now or datetime.now(UTC)).isoformat(),
        "privacy": "No database, credentials, profiles, answers, or question content included.",
    }
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("diagnostics.json", diagnostic_text)
        archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True, indent=2))
        archive.writestr("version.txt", str(status.get("app_version", "unknown")))
        for path in sorted(log_directory.glob("assessment-device.log*")):
            if path.is_file():
                text = path.read_text(encoding="utf-8", errors="replace")[-200_000:]
                archive.writestr(f"logs/{path.name}", redact_text(text, secrets=secrets))
    return destination


def main() -> int:
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.database_path)
    parser.add_argument("--credentials", type=Path, default=Path("var/device_credentials.json"))
    parser.add_argument("--logs", type=Path, default=config.log_directory)
    parser.add_argument("--update-root", type=Path, default=config.update_root)
    parser.add_argument("--output", type=Path, default=Path("var/support"))
    parser.add_argument("--trusted-key-id", default=config.trusted_update_key_id)
    args = parser.parse_args()
    destination = create_support_bundle(
        database_path=args.db,
        credential_path=args.credentials,
        log_directory=args.logs,
        update_root=args.update_root,
        output_directory=args.output,
        trusted_key_id=args.trusted_key_id,
    )
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
