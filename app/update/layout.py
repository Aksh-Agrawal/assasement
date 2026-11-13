"""Safe filesystem layout and first-time state migration helpers."""

from __future__ import annotations

import os
import shutil
import sqlite3
import stat
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class InstallationPaths:
    app_root: Path
    data_root: Path
    database_path: Path
    credential_path: Path
    update_root: Path
    update_inbox: Path
    ui_unit: str
    service_user: str
    service_group: str


def validate_trusted_app_root(
    app_root: Path,
    service_uid: int,
    service_gids: set[int] | tuple[int, ...],
) -> None:
    """Reject a release root replaceable by the unprivileged kiosk account."""
    app_root = Path(app_root).resolve()
    candidates = (app_root, *app_root.parents)
    for directory in candidates:
        if not directory.exists():
            continue
        metadata = directory.stat()
        mode = stat.S_IMODE(metadata.st_mode)
        writable_by_service = (
            metadata.st_uid == service_uid
            or bool(mode & stat.S_IWOTH)
            or (metadata.st_gid in service_gids and bool(mode & stat.S_IWGRP))
        )
        if writable_by_service:
            raise ValueError(
                f"Privileged release root has a service-writable ancestor: {directory}"
            )


def configured_installation_paths(environ: Mapping[str, str] | None = None) -> InstallationPaths:
    """Resolve and validate explicit updater paths; reject unsafe DB locations."""
    env = os.environ if environ is None else environ
    app_root = Path(env.get("ASSESS_APP_ROOT", "/opt/questraa-device"))
    data_root = Path(env.get("ASSESS_DATA_DIR", "/var/lib/assessdev"))
    database = Path(env.get("ASSESS_SQLITE_PATH", str(data_root / "assessment-device.db")))
    credentials = Path(env.get("ASSESS_CREDENTIAL_PATH", str(data_root / "device_credentials.json")))
    update_root = Path(env.get("ASSESS_UPDATE_DIR", str(data_root / "update")))
    inbox = Path(env.get("ASSESS_UPDATE_INBOX", str(update_root / "inbox")))
    paths = (app_root, data_root, database, credentials, update_root, inbox)
    if any(not path.is_absolute() for path in paths):
        raise ValueError("Updater installation paths must be absolute")
    app_root = app_root.resolve()
    data_root = data_root.resolve()
    release_root = app_root / "releases"
    if data_root == app_root or release_root == data_root or release_root in data_root.parents:
        raise ValueError("Persistent data must stay outside the managed release tree")
    for label, path in (("SQLite database", database), ("device credentials", credentials)):
        resolved = path.resolve()
        if resolved == release_root or release_root in resolved.parents:
            raise ValueError(f"{label} must stay outside versioned release directories")
    ui_unit = env.get("ASSESS_UI_UNIT", "assessdev-ui.service")
    service_user = env.get("ASSESS_SERVICE_USER", "aksh")
    service_group = env.get("ASSESS_SERVICE_GROUP", service_user)
    if not ui_unit.endswith(".service") or any(c in ui_unit for c in " /\\\n\r"):
        raise ValueError("ASSESS_UI_UNIT must be a systemd service unit name")
    if not service_user.replace("_", "").replace("-", "").isalnum():
        raise ValueError("ASSESS_SERVICE_USER is invalid")
    if not service_group.replace("_", "").replace("-", "").isalnum():
        raise ValueError("ASSESS_SERVICE_GROUP is invalid")
    return InstallationPaths(
        app_root=app_root,
        data_root=data_root,
        database_path=database.resolve(),
        credential_path=credentials.resolve(),
        update_root=update_root.resolve(),
        update_inbox=inbox.resolve(),
        ui_unit=ui_unit,
        service_user=service_user,
        service_group=service_group,
    )


def validate_existing_database(database: Path) -> None:
    """Require an existing, readable SQLite DB with a clean integrity check."""
    database = Path(database)
    if not database.is_absolute() or not database.is_file():
        raise FileNotFoundError(f"Configured existing SQLite database is missing: {database}")
    uri = database.resolve().as_uri() + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        result = connection.execute("PRAGMA quick_check").fetchone()
        if result != ("ok",):
            raise sqlite3.DatabaseError(f"SQLite quick_check failed for {database}: {result}")
    finally:
        connection.close()


def _install_exclusive(source: Path, destination: Path) -> None:
    """Publish a prepared file atomically without replacing a concurrent target."""
    if os.name == "nt":
        # Windows rename fails when the destination already exists.
        os.rename(source, destination)
    else:
        # Same-filesystem hard-link creation is atomic and never overwrites.
        os.link(source, destination)


def migrate_existing_state(
    source_database: Path,
    destination_database: Path,
    source_credentials: Path | None = None,
    destination_credentials: Path | None = None,
) -> tuple[Path, Path | None]:
    """Online-copy existing SQLite/credentials without replacing any target.

    Source files are retained as recovery copies. Destination creation is
    exclusive and atomic; a pre-existing destination is an error unless source
    and destination resolve to the same path.
    """
    source_database = Path(source_database).resolve()
    destination_database = Path(destination_database).resolve()
    validate_existing_database(source_database)
    source_credentials = Path(source_credentials).resolve() if source_credentials and Path(source_credentials).is_file() else None
    destination_credentials = (
        Path(destination_credentials or source_credentials).resolve() if source_credentials else None
    )
    if source_credentials and destination_credentials != source_credentials and destination_credentials.exists():
        raise FileExistsError(f"Refusing to overwrite existing credentials: {destination_credentials}")
    if source_database != destination_database and destination_database.exists():
        raise FileExistsError(f"Refusing to overwrite existing database: {destination_database}")
    if source_database == destination_database:
        db_result = destination_database
    else:
        destination_database.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{destination_database.name}.", suffix=".migrate", dir=destination_database.parent
        )
        os.close(fd)
        temp_database = Path(temp_name)
        try:
            source = sqlite3.connect(source_database)
            target = sqlite3.connect(temp_database)
            try:
                source.backup(target)
            finally:
                target.close()
                source.close()
            validate_existing_database(temp_database)
            _install_exclusive(temp_database, destination_database)
            db_result = destination_database
        finally:
            temp_database.unlink(missing_ok=True)

    credential_result: Path | None = None
    if source_credentials and destination_credentials:
        if source_credentials == destination_credentials:
            credential_result = destination_credentials
        else:
            destination_credentials.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{destination_credentials.name}.", dir=destination_credentials.parent
            )
            os.close(fd)
            temporary = Path(temp_name)
            try:
                shutil.copy2(source_credentials, temporary)
                os.chmod(temporary, 0o600)
                _install_exclusive(temporary, destination_credentials)
                credential_result = destination_credentials
            finally:
                temporary.unlink(missing_ok=True)
    return db_result, credential_result
