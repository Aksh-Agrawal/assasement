"""Read existing SQLite state without migration, creation or private row output."""
import argparse
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.auth.credentials import CredentialStore
from app.config import AppConfig
from app.version import __version__


def inventory(path: Path, credentials: Path | None = None):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        connection.execute("BEGIN")
        tables = {r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        result = {"captured_at": datetime.now(UTC).isoformat(), "app_version": __version__, "counts": {}}
        result["schema_version"] = connection.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()[0] if "schema_meta" in tables else None
        for name in ("profiles", "attempts", "responses", "question_sets", "institute_work", "profile_link_context"):
            result["counts"][name] = connection.execute('SELECT COUNT(*) FROM "' + name + '"').fetchone()[0] if name in tables else None
        if "profiles" in tables:
            columns = {r[1] for r in connection.execute("PRAGMA table_info(profiles)")}
            result["linked_profiles"] = connection.execute("SELECT COUNT(*) FROM profiles WHERE link_state='linked'").fetchone()[0] if "link_state" in columns else 0
            result["legacy_unclaimed_profiles"] = connection.execute("SELECT COUNT(*) FROM profiles WHERE ownership_state='legacy_unclaimed'").fetchone()[0] if "ownership_state" in columns else result["counts"]["profiles"]
        if "attempts" in tables:
            result["pending_uploads"] = connection.execute("SELECT COUNT(*) FROM attempts WHERE status='completed' AND sync_status!='synced'").fetchone()[0]
        result["device_identity_present"] = bool(connection.execute("SELECT value FROM schema_meta WHERE key='device_id'").fetchone()[0]) if "schema_meta" in tables else False
        result["credential_present"] = bool(credentials and CredentialStore(credentials).load_safe())
        result["integrity_ok"] = connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        return result


def main():
    config = AppConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=config.database_path)
    parser.add_argument("--credentials", type=Path, default=config.credential_path)
    args = parser.parse_args()
    try:
        print(json.dumps(inventory(args.db, args.credentials), indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"status": "unavailable", "kind": type(error).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
