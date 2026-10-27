"""One-shot, non-blocking remote question-pack synchronization."""

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from app.content.catalog import RemotePack, compare_catalog
from app.content.client import (
    ContentApiClient,
    ContentAuthError,
    ContentClientError,
    ContentNetworkError,
)
from app.content.downloader import DownloadSizeError, download_pack_to_temp
from app.content.hashing import sha256_file
from app.content.importer import import_pack
from app.content.validator import PackValidationError, validate_pack
from app.data.repo import Repository

LOGGER = logging.getLogger(__name__)
LAST_CONTENT_SYNC_SETTING = "last_content_sync_status"


class ContentSyncStatus(StrEnum):
    INSTALLED = "INSTALLED"
    ALREADY_PRESENT = "ALREADY_PRESENT"
    WOULD_DOWNLOAD = "WOULD_DOWNLOAD"
    FAILED_DOWNLOAD = "FAILED_DOWNLOAD"
    HASH_MISMATCH = "HASH_MISMATCH"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    IMPORT_FAILED = "IMPORT_FAILED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    NETWORK_UNAVAILABLE = "NETWORK_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class PackSyncResult:
    set_id: str
    version: int
    status: ContentSyncStatus
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ContentSyncResult:
    catalog_count: int
    installed_before: int
    eligible_count: int
    packs: tuple[PackSyncResult, ...]
    status: ContentSyncStatus | None = None


def _record(repository: Repository, result: ContentSyncResult) -> ContentSyncResult:
    status = result.status.value if result.status else "COMPLETE"
    error_code = None
    if result.status is ContentSyncStatus.AUTH_REQUIRED:
        error_code = "AUTH-002"
    elif result.status is not None:
        error_code = "CONTENT-001"
    repository.set_setting(
        LAST_CONTENT_SYNC_SETTING,
        json.dumps(
            {
                "status": status,
                "recorded_at": datetime.now(UTC).isoformat(),
                "error_code": error_code,
                "catalog_count": result.catalog_count,
                "eligible_count": result.eligible_count,
                "results": [item.status.value for item in result.packs],
            },
            separators=(",", ":"),
            sort_keys=True,
        ),
    )
    return result


def sync_content_once(
    repository: Repository,
    client: ContentApiClient,
    *,
    temp_directory: Path,
    max_pack_bytes: int,
    max_downloads_per_cycle: int,
    dry_run: bool = False,
) -> ContentSyncResult:
    """Fetch, compare, verify, validate, and atomically import a bounded batch."""
    if max_downloads_per_cycle < 1:
        raise ValueError("max_downloads_per_cycle must be positive")
    installed_before = len(repository.list_question_sets())
    try:
        catalog = client.fetch_catalog()
        LOGGER.info("content catalog fetched packs=%d", len(catalog.packs))
    except ContentAuthError:
        return _record(repository, ContentSyncResult(0, installed_before, 0, (), ContentSyncStatus.AUTH_REQUIRED))
    except (ContentNetworkError, ContentClientError) as error:
        LOGGER.warning("content catalog unavailable error=%s", type(error).__name__)
        return _record(
            repository,
            ContentSyncResult(0, installed_before, 0, (), ContentSyncStatus.NETWORK_UNAVAILABLE),
        )

    comparisons = compare_catalog(catalog, repository)
    eligible = [item for item in comparisons if item.eligible]
    results = [
        PackSyncResult(item.pack.set_id, item.pack.version, ContentSyncStatus.ALREADY_PRESENT)
        for item in comparisons
        if not item.eligible
    ]
    for item in eligible[:max_downloads_per_cycle]:
        pack = item.pack
        if dry_run:
            results.append(PackSyncResult(pack.set_id, pack.version, ContentSyncStatus.WOULD_DOWNLOAD))
            continue
        results.append(
            _install_one(
                repository,
                client,
                pack,
                temp_directory=temp_directory,
                max_pack_bytes=max_pack_bytes,
            )
        )
    return _record(
        repository,
        ContentSyncResult(len(catalog.packs), installed_before, len(eligible), tuple(results)),
    )


def _install_one(
    repository: Repository,
    client: ContentApiClient,
    pack: RemotePack,
    *,
    temp_directory: Path,
    max_pack_bytes: int,
) -> PackSyncResult:
    temporary: Path | None = None
    LOGGER.info("pack download started set_id=%s version=%d", pack.set_id, pack.version)
    try:
        temporary = download_pack_to_temp(
            client, pack, temp_directory=temp_directory, max_bytes=max_pack_bytes
        )
        LOGGER.info("pack download complete set_id=%s version=%d", pack.set_id, pack.version)
        if sha256_file(temporary) != pack.sha256:
            LOGGER.warning("pack hash mismatch set_id=%s version=%d", pack.set_id, pack.version)
            return PackSyncResult(pack.set_id, pack.version, ContentSyncStatus.HASH_MISMATCH)
        validated = validate_pack(temporary, expected_sha256=pack.sha256, max_bytes=max_pack_bytes)
        question_set = validated.question_set
        if (
            question_set.id != pack.set_id
            or question_set.version != pack.version
            or len(question_set.questions) != pack.question_count
        ):
            LOGGER.warning("pack metadata mismatch set_id=%s version=%d", pack.set_id, pack.version)
            return PackSyncResult(
                pack.set_id,
                pack.version,
                ContentSyncStatus.VALIDATION_FAILED,
                "catalog metadata does not match pack",
            )
        current = repository.get_active_question_set(pack.set_id)
        make_active = current is None or pack.version > current.version
        import_pack(
            temporary,
            repository,
            expected_sha256=pack.sha256,
            make_active=make_active,
            max_bytes=max_pack_bytes,
        )
        LOGGER.info("pack import success set_id=%s version=%d", pack.set_id, pack.version)
        return PackSyncResult(pack.set_id, pack.version, ContentSyncStatus.INSTALLED)
    except ContentAuthError as error:
        return PackSyncResult(pack.set_id, pack.version, ContentSyncStatus.AUTH_REQUIRED, str(error))
    except ContentNetworkError as error:
        return PackSyncResult(
            pack.set_id, pack.version, ContentSyncStatus.NETWORK_UNAVAILABLE, str(error)
        )
    except DownloadSizeError as error:
        return PackSyncResult(pack.set_id, pack.version, ContentSyncStatus.FAILED_DOWNLOAD, str(error))
    except PackValidationError as error:
        LOGGER.warning("pack validation failure set_id=%s version=%d", pack.set_id, pack.version)
        return PackSyncResult(
            pack.set_id, pack.version, ContentSyncStatus.VALIDATION_FAILED, str(error)
        )
    except ContentClientError as error:
        return PackSyncResult(pack.set_id, pack.version, ContentSyncStatus.FAILED_DOWNLOAD, str(error))
    except Exception as error:
        LOGGER.exception("pack import failed set_id=%s version=%d", pack.set_id, pack.version)
        return PackSyncResult(pack.set_id, pack.version, ContentSyncStatus.IMPORT_FAILED, type(error).__name__)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
