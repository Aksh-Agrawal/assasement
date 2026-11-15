"""Atomic, traversal-safe staging of already verified tar.gz releases."""

import json
import logging
import shutil
import stat
import tarfile
import tempfile
from collections.abc import Callable
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


def _matching_file(path: Path, expected: bytes) -> bool:
    metadata = path.lstat()
    return (stat.S_ISREG(metadata.st_mode) and metadata.st_size == len(expected)
            and path.read_bytes() == expected)


def stage_update(
    update: VerifiedUpdate,
    root: Path,
    *,
    reuse_for_service: bool = False,
    progress: Callable[[str, float | None], None] | None = None,
) -> Path:
    LOGGER.info("update staging started: version=%s", update.manifest.version)
    staged_root = root / "staged"
    staged_root.mkdir(parents=True, exist_ok=True)
    target = staged_root / str(update.manifest.version)
    if target.exists() or target.is_symlink():
        if reuse_for_service:
            # The system service uses only these signed files and re-extracts the verified archive.
            try:
                if (stat.S_ISDIR(target.lstat().st_mode)
                        and _matching_file(target / "update-manifest.json", update.manifest.canonical_bytes)
                        and _matching_file(target / "update-manifest.sig", update.signature)):
                    return target
            except OSError as error:
                raise StagingError("Existing staged update metadata could not be read") from error
        raise StagingError("Release version is already staged")
    temporary = Path(tempfile.mkdtemp(prefix="incoming-", dir=root))
    try:
        with tarfile.open(update.artifact, "r:gz") as archive:
            if progress is not None:
                progress("checking_archive", None)
            members = archive.getmembers()
            if any(
                not _safe_member(item.name)
                or item.issym()
                or item.islnk()
                or not (item.isfile() or item.isdir())
                for item in members
            ):
                raise StagingError("Archive contains an unsafe path or link")
            total = sum(item.size for item in members if item.isfile())
            extracted = 0
            if progress is not None:
                progress("extracting", 0.0)
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
                    while chunk := source.read(256 * 1024):
                        extracted += output.write(chunk)
                        if progress is not None and total:
                            progress("extracting", extracted / total)
        if progress is not None:
            progress("finalizing", None)
        required = (temporary / "app", temporary / "pyproject.toml", temporary / "release.json")
        if not required[0].is_dir() or any(not path.exists() for path in required[1:]):
            raise StagingError("Release structure is incomplete")
        release = json.loads(required[2].read_text(encoding="utf-8"))
        if release.get("version") != str(update.manifest.version):
            raise StagingError("Release version does not match manifest")
        (temporary / "update-manifest.json").write_bytes(update.manifest.canonical_bytes)
        # The staged copy lets the independent system service verify the signature again.
        (temporary / "update-manifest.sig").write_bytes(update.signature)
        temporary.replace(target)
        LOGGER.info("update staging completed: version=%s", update.manifest.version)
        return target
    except (OSError, tarfile.TarError, json.JSONDecodeError) as error:
        LOGGER.warning("update staging failed: %s", type(error).__name__)
        raise StagingError("Release staging failed") from error
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
