"""Atomic, traversal-safe staging of already verified tar.gz releases."""

import json
import logging
import shutil
import tarfile
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

from app.update.errors import StagingError
from app.update.verifier import VerifiedUpdate

LOGGER = logging.getLogger(__name__)


def _safe_member(name: str) -> bool:
    posix = PurePosixPath(name)
    windows = PureWindowsPath(name)
    return not (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or ".." in posix.parts
        or ".." in windows.parts
    )


def stage_update(update: VerifiedUpdate, root: Path) -> Path:
    LOGGER.info("update staging started: version=%s", update.manifest.version)
    staged_root = root / "staged"
    staged_root.mkdir(parents=True, exist_ok=True)
    target = staged_root / str(update.manifest.version)
    if target.exists():
        raise StagingError("Release version is already staged")
    temporary = Path(tempfile.mkdtemp(prefix="incoming-", dir=root))
    try:
        with tarfile.open(update.artifact, "r:gz") as archive:
            members = archive.getmembers()
            if any(
                not _safe_member(item.name)
                or item.issym()
                or item.islnk()
                or not (item.isfile() or item.isdir())
                for item in members
            ):
                raise StagingError("Archive contains an unsafe path or link")
            for item in members:
                destination = temporary.joinpath(*PurePosixPath(item.name).parts)
                if item.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = archive.extractfile(item)
                if source is None:
                    raise StagingError("Archive contains an unreadable file")
                with source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
        required = (temporary / "app", temporary / "pyproject.toml", temporary / "release.json")
        if not required[0].is_dir() or any(not path.exists() for path in required[1:]):
            raise StagingError("Release structure is incomplete")
        release = json.loads(required[2].read_text(encoding="utf-8"))
        if release.get("version") != str(update.manifest.version):
            raise StagingError("Release version does not match manifest")
        temporary.replace(target)
        LOGGER.info("update staging completed: version=%s", update.manifest.version)
        return target
    except (OSError, tarfile.TarError, json.JSONDecodeError) as error:
        LOGGER.warning("update staging failed: %s", type(error).__name__)
        raise StagingError("Release staging failed") from error
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
