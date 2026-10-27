"""Environment-backed backend configuration."""

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class Settings:
    """Small configuration surface for the development backend."""

    database_url: str
    pairing_code_ttl_seconds: int = 600
    update_catalog_directory: Path = BACKEND_ROOT / "releases"
    content_storage_path: Path = BACKEND_ROOT / "runtime" / "content"

    @classmethod
    def from_environment(cls) -> "Settings":
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            database_url = f"sqlite:///{(BACKEND_ROOT / 'dev.db').as_posix()}"
        return cls(
            database_url=database_url,
            pairing_code_ttl_seconds=int(os.environ.get("ASSESS_PAIRING_CODE_TTL_SECONDS", "600")),
            update_catalog_directory=Path(
                os.environ.get("ASSESS_UPDATE_CATALOG", str(BACKEND_ROOT / "releases"))
            ),
            content_storage_path=Path(
                os.environ.get("CONTENT_STORAGE_PATH", str(BACKEND_ROOT / "runtime" / "content"))
            ),
        )
