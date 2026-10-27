"""SQLite connections, forward-only migrations, integrity checks, and backup."""

import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

MIGRATIONS_DIRECTORY = Path(__file__).with_name("migrations")
_MIGRATION_PATTERN = re.compile(r"^(?P<version>\d{4})_[a-z0-9_]+\.sql$")


class MigrationError(RuntimeError):
    """Raised when the on-disk migration sequence cannot be applied safely."""


@dataclass(frozen=True, slots=True)
class IntegrityCheckResult:
    """Result returned by SQLite's integrity checker."""

    ok: bool
    messages: tuple[str, ...]


def utc_now_text() -> str:
    """Return the current wall-clock timestamp as UTC ISO-8601 text."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def datetime_to_text(value: datetime) -> str:
    """Normalize an aware datetime to UTC ISO-8601 text."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamps must be timezone-aware")
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def datetime_from_text(value: str | None) -> datetime | None:
    """Parse repository timestamp text into an aware datetime."""
    if value is None:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def connect_database(path: Path) -> sqlite3.Connection:
    """Open one configured SQLite connection without running migrations."""
    database_path = Path(path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, isolation_level=None)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("PRAGMA wal_autocheckpoint = 1000")
    except BaseException:
        # A failed PRAGMA must not retain a file handle and obstruct recovery/retry.
        connection.close()
        raise
    return connection


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a short explicit write transaction with rollback on failure."""
    if connection.in_transaction:
        raise RuntimeError("Nested repository transactions are not supported")
    connection.execute("BEGIN IMMEDIATE")
    try:
        yield connection
    except BaseException:
        connection.rollback()
        raise
    else:
        connection.commit()


def _migration_files(directory: Path) -> tuple[tuple[int, Path], ...]:
    migrations: list[tuple[int, Path]] = []
    seen_versions: set[int] = set()
    for path in directory.glob("*.sql"):
        match = _MIGRATION_PATTERN.fullmatch(path.name)
        if match is None:
            continue
        version = int(match.group("version"))
        if version in seen_versions:
            raise MigrationError(f"Duplicate migration version {version}")
        seen_versions.add(version)
        migrations.append((version, path))
    return tuple(sorted(migrations))


def get_schema_version(connection: sqlite3.Connection) -> int:
    """Return the recorded schema version, or zero for an empty database."""
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'schema_meta'"
    ).fetchone()
    if exists is None:
        return 0
    row = connection.execute(
        "SELECT value FROM schema_meta WHERE key = 'schema_version'"
    ).fetchone()
    if row is None:
        raise MigrationError("schema_meta exists without schema_version")
    try:
        return int(row["value"])
    except (TypeError, ValueError) as error:
        raise MigrationError("schema_version is not an integer") from error


def run_migrations(
    connection: sqlite3.Connection,
    migrations_directory: Path = MIGRATIONS_DIRECTORY,
) -> int:
    """Apply missing numbered SQL migrations in ascending order."""
    migrations = _migration_files(migrations_directory)
    current_version = get_schema_version(connection)
    available_versions = {version for version, _ in migrations}
    if current_version and current_version not in available_versions:
        raise MigrationError(
            f"Database schema version {current_version} has no matching migration file"
        )

    for version, path in migrations:
        if version <= current_version:
            continue
        sql = path.read_text(encoding="utf-8")
        script = (
            "BEGIN IMMEDIATE;\n"
            f"{sql}\n"
            "INSERT INTO schema_meta(key, value) VALUES ('schema_version', "
            f"'{version}') ON CONFLICT(key) DO UPDATE SET value = excluded.value;\n"
            "COMMIT;"
        )
        try:
            connection.executescript(script)
        except sqlite3.Error:
            if connection.in_transaction:
                connection.rollback()
            raise
        current_version = version
    return current_version


def check_integrity(connection: sqlite3.Connection) -> IntegrityCheckResult:
    """Run ``PRAGMA integrity_check`` and return all diagnostic messages."""
    messages = tuple(row[0] for row in connection.execute("PRAGMA integrity_check"))
    return IntegrityCheckResult(ok=messages == ("ok",), messages=messages)


def quick_check(connection: sqlite3.Connection) -> IntegrityCheckResult:
    """Run SQLite's lightweight quick consistency check."""
    messages = tuple(row[0] for row in connection.execute("PRAGMA quick_check"))
    return IntegrityCheckResult(ok=messages == ("ok",), messages=messages)


def backup_database(connection: sqlite3.Connection, destination: Path) -> None:
    """Create one online SQLite backup without defining a rotation policy."""
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    backup_connection = sqlite3.connect(destination_path)
    try:
        connection.backup(backup_connection)
    finally:
        backup_connection.close()

