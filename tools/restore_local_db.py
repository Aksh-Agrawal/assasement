"""Explicitly restore a validated SQLite backup with a destination safety copy."""

import argparse
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.data.db import check_integrity


def _valid_database(path: Path) -> bool:
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True) as connection:
            return check_integrity(connection).ok
    except sqlite3.DatabaseError:
        return False


def restore(source: Path, destination: Path, *, overwrite: bool = False) -> Path | None:
    if source.resolve() == destination.resolve():
        raise ValueError("Source and destination must differ")
    if not source.is_file() or not _valid_database(source):
        raise ValueError("Source backup failed SQLite integrity validation")
    safety_copy = None
    if destination.exists():
        if not overwrite:
            raise FileExistsError("Destination exists; pass --overwrite for explicit replacement")
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        safety_copy = destination.with_name(f"{destination.name}.pre-restore-{stamp}.bak")
        shutil.copy2(destination, safety_copy)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".restore-tmp")
    shutil.copy2(source, temporary)
    temporary.replace(destination)
    return safety_copy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    safety = restore(args.source, args.destination, overwrite=args.overwrite)
    print("Restore completed after integrity validation.")
    if safety:
        print(f"Previous destination safety copy: {safety}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
