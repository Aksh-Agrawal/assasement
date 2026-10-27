"""Authenticated, timeout-bound HTTP client for remote question content."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from urllib.parse import quote

import httpx

from app.content.catalog import ContentCatalog, RemotePack


class ContentClientError(RuntimeError):
    pass


class ContentAuthError(ContentClientError):
    pass


class ContentNetworkError(ContentClientError):
    pass


class ContentProtocolError(ContentClientError):
    pass


class ContentApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        auth_token: str | None,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.strip():
            raise ValueError("API base URL must not be empty")
        self._paired = auth_token is not None
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {auth_token}"} if auth_token else None,
            timeout=httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=read_timeout,
                pool=connect_timeout,
            ),
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ContentApiClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def fetch_catalog(self) -> ContentCatalog:
        if not self._paired:
            raise ContentAuthError("Device pairing is required")
        try:
            response = self._client.get("/api/v1/content/catalog")
        except httpx.RequestError as error:
            raise ContentNetworkError(str(error)) from error
        self._check_response(response)
        try:
            body: Any = response.json()
            if not isinstance(body, dict):
                raise ValueError("Catalog must be an object")
            return ContentCatalog.from_dict(body)
        except (ValueError, TypeError) as error:
            raise ContentProtocolError(f"Invalid catalog response: {error}") from error

    @contextmanager
    def stream_pack(self, pack: RemotePack) -> Iterator[httpx.Response]:
        if not self._paired:
            raise ContentAuthError("Device pairing is required")
        path = f"/api/v1/content/packs/{quote(pack.set_id, safe='')}/{pack.version}"
        try:
            with self._client.stream("GET", path) as response:
                self._check_response(response)
                yield response
        except ContentClientError:
            raise
        except httpx.RequestError as error:
            raise ContentNetworkError(str(error)) from error

    @staticmethod
    def _check_response(response: httpx.Response) -> None:
        if response.status_code in {401, 403}:
            raise ContentAuthError(f"HTTP {response.status_code}: authentication rejected")
        if response.status_code in {408, 425, 429} or response.status_code >= 500:
            raise ContentNetworkError(f"HTTP {response.status_code}: backend unavailable")
        if not 200 <= response.status_code < 300:
            raise ContentProtocolError(f"HTTP {response.status_code}: content request rejected")
