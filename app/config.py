"""Platform-independent application configuration skeleton."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from app import __version__


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Environment defaults evaluated at construction; explicit arguments win.

    Reading configuration never creates files or contacts the network.
    """

    data_directory: Path = field(default_factory=lambda: Path(os.getenv("ASSESS_DATA_DIR", "var")))
    database_path: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "ASSESS_SQLITE_PATH",
                str(Path(os.getenv("ASSESS_DATA_DIR", "var")) / "assessment-device.db"),
            )
        )
    )
    credential_path: Path = field(
        default_factory=lambda: Path(
            os.getenv(
                "ASSESS_CREDENTIAL_PATH",
                str(Path(os.getenv("ASSESS_DATA_DIR", "var")) / "device_credentials.json"),
            )
        )
    )
    packs_directory: Path = field(
        default_factory=lambda: Path(os.getenv("ASSESS_PACK_DIR", "content"))
    )
    media_directory: Path = Path("media")
    log_directory: Path = field(
        default_factory=lambda: Path(
            os.getenv("ASSESS_LOG_DIR", str(Path(os.getenv("ASSESS_DATA_DIR", "var")) / "log"))
        )
    )
    api_base_url: str | None = field(default_factory=lambda: os.getenv("ASSESS_API_URL") or None)
    sync_connect_timeout: float = field(
        default_factory=lambda: float(os.getenv("ASSESS_CONNECT_TIMEOUT", "5.0"))
    )
    sync_read_timeout: float = field(
        default_factory=lambda: float(os.getenv("ASSESS_READ_TIMEOUT", "15.0"))
    )
    sync_interval_seconds: float = field(
        default_factory=lambda: float(os.getenv("ASSESS_SYNC_INTERVAL", "25"))
    )
    heartbeat_interval_seconds: float = field(
        default_factory=lambda: float(os.getenv("ASSESS_HEARTBEAT_INTERVAL", "60"))
    )
    sync_batch_size: int = 10
    sync_max_automatic_retries: int = 5
    sync_stale_after_seconds: int = 300
    device_id: str | None = None
    application_version: str = __version__
    update_root: Path = field(
        default_factory=lambda: Path(os.getenv("ASSESS_UPDATE_DIR", "runtime/updates"))
    )
    update_platform: str = "development"
    update_architecture: str = "any"
    trusted_update_key_id: str = "development-1"
    trusted_update_public_key_path: Path = Path("config/update-public.pem")
    content_download_directory: Path = field(
        default_factory=lambda: Path(
            os.getenv("ASSESS_DOWNLOAD_DIR", "runtime/content-downloads/tmp")
        )
    )
    content_max_pack_bytes: int = 25 * 1024 * 1024
    content_max_downloads_per_cycle: int = 5

    def __post_init__(self) -> None:
        from urllib.parse import urlsplit

        if self.api_base_url is not None:
            url = urlsplit(self.api_base_url)
            if (
                url.scheme not in {"http", "https"}
                or not url.netloc
                or url.username
                or url.password
                or url.query
                or url.fragment
                or url.path not in {"", "/"}
            ):
                raise ValueError("ASSESS_API_URL must be an HTTP(S) origin without credentials")
        for value in (
            self.sync_connect_timeout,
            self.sync_read_timeout,
            self.sync_interval_seconds,
            self.heartbeat_interval_seconds,
        ):
            if not 0 < value < float("inf"):
                raise ValueError("Device timeouts and intervals must be finite and positive")
