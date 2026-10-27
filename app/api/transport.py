"""Shared verified transport and safe failure vocabulary for device HTTP services.

Requests are single-shot: persistent attempt retry/backoff belongs to SyncWorker;
pairing claims and downloads are retried explicitly to avoid replaying mutations.
"""

from enum import StrEnum

import httpx


class FailureState(StrEnum):
    OFFLINE = "OFFLINE"
    TIMEOUT = "TIMEOUT"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    SERVER_ERROR = "SERVER_ERROR"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    CONTENT_VALIDATION_FAILED = "CONTENT_VALIDATION_FAILED"


def failure_state(error: Exception) -> FailureState:
    if isinstance(error.__cause__, Exception):
        return failure_state(error.__cause__)
    state = getattr(error, "state", None)
    if isinstance(state, FailureState):
        return state
    if isinstance(error, httpx.TimeoutException):
        return FailureState.TIMEOUT
    if isinstance(error, httpx.RequestError):
        return FailureState.OFFLINE
    if isinstance(error, httpx.HTTPStatusError):
        if error.response.status_code in {401, 403}:
            return FailureState.AUTH_REQUIRED
        if error.response.status_code >= 500:
            return FailureState.SERVER_ERROR
    # Domain clients retain their public error types for worker compatibility.
    name = type(error).__name__
    if name in {"PackValidationError", "DownloadSizeError", "IntegrityError"}:
        return FailureState.CONTENT_VALIDATION_FAILED
    if name in {"ContentAuthError", "AuthenticationError", "PairingRequired"}:
        return FailureState.AUTH_REQUIRED
    if name == "TransientSyncError":
        return FailureState.SERVER_ERROR
    if name == "ContentNetworkError":
        return FailureState.OFFLINE
    return FailureState.INVALID_RESPONSE


def response_failure(response: httpx.Response) -> FailureState | None:
    if 200 <= response.status_code < 300:
        return None
    if response.status_code in {401, 403}:
        return FailureState.AUTH_REQUIRED
    if response.status_code in {408, 425, 429} or response.status_code >= 500:
        return FailureState.SERVER_ERROR
    return FailureState.INVALID_RESPONSE


def create_client(
    base_url: str,
    *,
    auth_token: str | None = None,
    connect_timeout: float = 5.0,
    read_timeout: float = 15.0,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    from app.config import AppConfig

    AppConfig(api_base_url=base_url)
    return httpx.Client(
        base_url=base_url.rstrip("/"),
        headers={"Authorization": f"Bearer {auth_token}"} if auth_token else {},
        timeout=httpx.Timeout(connect=connect_timeout, read=read_timeout,
                              write=read_timeout, pool=connect_timeout),
        verify=True,
        follow_redirects=False,
        transport=transport,
    )


def json_object(response: httpx.Response) -> dict:
    body = response.json()
    if not isinstance(body, dict):
        raise ValueError("Expected a JSON object")
    return body
