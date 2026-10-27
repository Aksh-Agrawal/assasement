"""Explicit, side-effect-free HTTP client for attempt upload."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx

from app.sync.errors import (
    AlreadySynced,
    AuthenticationError,
    PairingRequired,
    PermanentSyncError,
    TransientSyncError,
)

_ALREADY_ACCEPTED_CODES = {"already_uploaded", "attempt_already_exists", "duplicate_attempt"}


@dataclass(frozen=True, slots=True)
class UploadResult:
    """Successful acknowledgement metadata returned to the worker."""

    status_code: int
    already_synced: bool = False


class SyncApiClient:
    """Synchronous Phase 9A client; construction and import perform no I/O."""

    def __init__(
        self,
        base_url: str,
        *,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
        auth_token: str | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("API base URL must not be empty")
        timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=read_timeout,
            pool=connect_timeout,
        )
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else None
        self._paired = auth_token is not None
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            transport=transport,
            headers=headers,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SyncApiClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def upload_attempt(self, payload: dict[str, Any], idempotency_key: str) -> UploadResult:
        """Upload once and classify HTTP/transport outcomes for worker policy."""
        if not self._paired:
            raise PairingRequired("PAIRING_REQUIRED")
        path = f"/api/v1/attempts/{quote(idempotency_key, safe='')}"
        try:
            response = self._client.put(
                path,
                json=payload,
                headers={
                    "Idempotency-Key": idempotency_key,
                    "X-Attempt-Payload-Version": str(payload.get("payload_version", "")),
                },
            )
        except httpx.TimeoutException as error:
            raise TransientSyncError(f"timeout: {error}") from error
        except httpx.RequestError as error:
            raise TransientSyncError(f"network: {error}") from error

        if 200 <= response.status_code < 300:
            return UploadResult(response.status_code)
        if response.status_code in {401, 403}:
            raise AuthenticationError(f"HTTP {response.status_code}: authentication rejected")
        if response.status_code == 409 and self._proves_already_accepted(response, idempotency_key):
            raise AlreadySynced(f"Attempt {idempotency_key} was already accepted")
        if response.status_code in {408, 425, 429} or 500 <= response.status_code <= 599:
            raise TransientSyncError(f"HTTP {response.status_code}: server temporarily unavailable")
        raise PermanentSyncError(f"HTTP {response.status_code}: upload rejected")

    @staticmethod
    def _proves_already_accepted(response: httpx.Response, attempt_id: str) -> bool:
        try:
            body = response.json()
        except ValueError:
            return False
        if not isinstance(body, dict) or body.get("attempt_id") != attempt_id:
            return False
        return body.get("code") in _ALREADY_ACCEPTED_CODES or body.get("status") in {
            "accepted",
            "synced",
        }
