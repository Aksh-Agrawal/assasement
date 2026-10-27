"""Platform-independent application configuration skeleton."""

from dataclasses import dataclass
from pathlib import Path

from app import __version__


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Immutable paths and identity settings used by future application layers.

    Defaults are development-relative and do not read or create files. A future
    Raspberry Pi production mode may load explicit values from
    ``/etc/assessdev/config.toml``; that behavior is intentionally not part of
    Phase 1.
    """

    database_path: Path = Path("var/assessment-device.db")
    packs_directory: Path = Path("content")
    media_directory: Path = Path("media")
    log_directory: Path = Path("var/log")
    api_base_url: str | None = None
    sync_connect_timeout: float = 5.0
    sync_read_timeout: float = 15.0
    sync_batch_size: int = 10
    sync_max_automatic_retries: int = 5
    sync_stale_after_seconds: int = 300
    device_id: str | None = None
    application_version: str = __version__
    update_root: Path = Path("runtime/updates")
    update_platform: str = "development"
    update_architecture: str = "any"
    trusted_update_key_id: str = "development-1"
    trusted_update_public_key_path: Path = Path("config/update-public.pem")
    content_download_directory: Path = Path("runtime/content-downloads/tmp")
    content_max_pack_bytes: int = 25 * 1024 * 1024
    content_max_downloads_per_cycle: int = 5

