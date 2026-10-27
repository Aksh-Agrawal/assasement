"""Explicit authenticated update metadata and bounded artifact download client."""

import base64
import logging
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.update.errors import IntegrityError, UpdateError
from app.update.manifest import UpdateManifest, canonical_manifest_bytes

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AvailableUpdate:
    manifest_bytes: bytes
    signature: bytes
    manifest: UpdateManifest


class UpdateClient:
    def __init__(
        self,
        base_url: str,
        credential: str,
        *,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("Update API base URL must not be empty")
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers={"Authorization": f"Bearer {credential}"},
        )

    def close(self) -> None:
        self._client.close()

    def check_for_update(self) -> AvailableUpdate:
        LOGGER.info("update check started")
        try:
            response = self._client.get("/api/v1/device-updates/latest")
            if response.status_code in {401, 403}:
                raise UpdateError("Update authentication required")
            response.raise_for_status()
            body = response.json()
            manifest_bytes = canonical_manifest_bytes(body["manifest"])
            update = AvailableUpdate(
                manifest_bytes,
                base64.b64decode(body["signature"], validate=True),
                UpdateManifest.parse(manifest_bytes),
            )
        except UpdateError:
            LOGGER.warning("update check rejected")
            raise
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as error:
            LOGGER.warning("update check failed: %s", type(error).__name__)
            raise UpdateError("Update metadata request failed") from error
        LOGGER.info("update available: version=%s", update.manifest.version)
        return update

    def download_update(
        self,
        update: AvailableUpdate,
        destination: Path,
        *,
        hard_max_bytes: int = 100_000_000,
    ) -> Path:
        expected = update.manifest.data["artifact"]["size_bytes"]
        if expected > hard_max_bytes:
            raise IntegrityError("Manifest artifact exceeds download size limit")
        LOGGER.info(
            "update download started: version=%s expected_bytes=%d",
            update.manifest.version,
            expected,
        )
        temporary = destination.with_suffix(destination.suffix + ".part")
        temporary.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        try:
            with self._client.stream(
                "GET", f"/api/v1/device-updates/{update.manifest.version}/artifact"
            ) as response:
                response.raise_for_status()
                with temporary.open("wb") as output:
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > expected or total > hard_max_bytes:
                            raise IntegrityError("Downloaded artifact exceeded declared size")
                        output.write(chunk)
            if total != expected:
                raise IntegrityError("Downloaded artifact is truncated")
            temporary.replace(destination)
            LOGGER.info(
                "update download completed: version=%s bytes=%d",
                update.manifest.version,
                total,
            )
            return destination
        except BaseException as error:
            temporary.unlink(missing_ok=True)
            LOGGER.warning("update download failed: %s", type(error).__name__)
            raise
