"""Authenticated, timeout-bound HTTP client for remote question content."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import httpx

from app.api.transport import FailureState, create_client, json_object, response_failure
from app.content.catalog import ContentCatalog, RemotePack


class ContentClientError(RuntimeError):
    pass


class ContentAuthError(ContentClientError):
    pass


class ContentNetworkError(ContentClientError):
    def __init__(self, message: str, state: FailureState = FailureState.OFFLINE):
        super().__init__(message)
        self.state = state


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
        self._client = create_client(base_url, auth_token=auth_token, connect_timeout=connect_timeout, read_timeout=read_timeout, transport=transport)

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
            raise ContentNetworkError("Cloud connection unavailable") from error
        self._check_response(response)
        try:
            body: Any = json_object(response)
            if not isinstance(body, dict):
                raise ValueError("Catalog must be an object")
            return ContentCatalog.from_dict(body)
        except (ValueError, TypeError) as error:
            raise ContentProtocolError("Invalid catalog response") from error

    @contextmanager
    def stream_pack(self, pack: RemotePack) -> Iterator[httpx.Response]:
        if not self._paired:
            raise ContentAuthError("Device pairing is required")
        path = pack.download_reference
        try:
            with self._client.stream("GET", path) as response:
                self._check_response(response)
                yield response
        except ContentClientError:
            raise
        except httpx.RequestError as error:
            raise ContentNetworkError("Cloud connection unavailable") from error

    @staticmethod
    def _check_response(response: httpx.Response) -> None:
        if response_failure(response) is FailureState.AUTH_REQUIRED:
            raise ContentAuthError(f"HTTP {response.status_code}: authentication rejected")
        if response_failure(response) is FailureState.SERVER_ERROR:
            raise ContentNetworkError(
                f"HTTP {response.status_code}: backend unavailable", FailureState.SERVER_ERROR
            )
        if not 200 <= response.status_code < 300:
            raise ContentProtocolError(f"HTTP {response.status_code}: content request rejected")
