"""Client for QR-based mobile upload session orchestration."""

from dataclasses import dataclass
from datetime import datetime

import httpx

from app.api.transport import create_client, json_object


class MobileUploadClientError(RuntimeError):
    def __init__(self, message: str, code: str = "SESSION_CREATE_FAILED", status_code: int = 500):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class MobileUploadAuthError(MobileUploadClientError):
    def __init__(self, message: str, code: str = "DEVICE_NOT_LINKED"):
        super().__init__(message, code=code, status_code=403)


class MobileUploadProfileError(MobileUploadClientError):
    def __init__(self, message: str, code: str = "PROFILE_NOT_LINKED"):
        super().__init__(message, code=code, status_code=404)


class MobileUploadStorageError(MobileUploadClientError):
    def __init__(self, message: str, code: str = "QR_SESSION_STORAGE_UNAVAILABLE"):
        super().__init__(message, code=code, status_code=503)


@dataclass(frozen=True, slots=True)
class MobileSessionInfo:
    session_id: str
    token: str
    upload_url: str
    short_code: str
    expires_at: datetime
    status: str
    profile_name: str


@dataclass(frozen=True, slots=True)
class MobileSessionStatus:
    session_id: str
    status: str
    expires_at: datetime
    result_set_id: str | None
    pack_title: str | None
    question_count: int | None
    error_code: str | None
    error_message: str | None


class MobileUploadClient:
    def __init__(
        self,
        base_url: str,
        *,
        auth_token: str | None = None,
        transport: httpx.BaseTransport | None = None,
        connect_timeout: float = 5.0,
        read_timeout: float = 15.0,
    ):
        if not base_url.strip():
            raise ValueError("API base URL must not be empty")
        self._auth_token = auth_token
        self._client = create_client(
            base_url,
            auth_token=auth_token,
            transport=transport,
            connect_timeout=connect_timeout,
            read_timeout=read_timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "MobileUploadClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def create_session(self, local_profile_id: str) -> MobileSessionInfo:
        if not self._auth_token:
            raise MobileUploadAuthError("Device authentication required", code="DEVICE_NOT_LINKED")

        try:
            response = self._client.post(
                "/api/v1/mobile-upload-sessions",
                json={"local_profile_id": local_profile_id},
            )
        except httpx.RequestError as error:
            raise MobileUploadClientError("Cloud connection unavailable", code="CLOUD_UNAVAILABLE", status_code=503) from error

        if response.status_code in {401, 403}:
            code = "DEVICE_NOT_LINKED"
            msg = f"HTTP {response.status_code}: authentication rejected"
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    det = err_data.get("detail")
                    if isinstance(det, dict):
                        code = det.get("code") or code
                        msg = det.get("message") or det.get("code") or msg
                    elif isinstance(det, str):
                        msg = det
            except Exception:
                pass
            raise MobileUploadAuthError(msg, code=code)
        elif response.status_code == 404:
            code = "PROFILE_NOT_LINKED"
            msg = "Study profile is not linked to this device"
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    det = err_data.get("detail")
                    if isinstance(det, dict):
                        code = det.get("code") or code
                        msg = det.get("message") or det.get("code") or msg
                    elif isinstance(det, str):
                        msg = det
            except Exception:
                pass
            raise MobileUploadProfileError(msg, code=code)
        elif response.status_code == 503:
            code = "QR_SESSION_STORAGE_UNAVAILABLE"
            msg = "QR session storage service is temporarily unavailable"
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    det = err_data.get("detail")
                    if isinstance(det, dict):
                        code = det.get("code") or code
                        msg = det.get("message") or msg
                    elif isinstance(det, str):
                        msg = det
            except Exception:
                pass
            raise MobileUploadStorageError(msg, code=code)
        elif not response.is_success:
            code = "SESSION_CREATE_FAILED"
            msg = f"HTTP {response.status_code}: session creation failed"
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    det = err_data.get("detail")
                    if isinstance(det, dict):
                        code = det.get("code") or code
                        msg = det.get("message") or msg
                    elif isinstance(det, str):
                        msg = det
            except Exception:
                pass
            raise MobileUploadClientError(msg, code=code, status_code=response.status_code)

        body = json_object(response)
        expires = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
        return MobileSessionInfo(
            session_id=body["session_id"],
            token=body["token"],
            upload_url=body["upload_url"],
            short_code=body.get("short_code", ""),
            expires_at=expires,
            status=body.get("status", "WAITING_FOR_PHONE"),
            profile_name=body.get("profile_name", ""),
        )

    def get_status(self, session_id: str) -> MobileSessionStatus:
        if not self._auth_token:
            raise MobileUploadAuthError("Device authentication required")

        try:
            response = self._client.get(f"/api/v1/mobile-upload-sessions/{session_id}/status")
        except httpx.RequestError as error:
            raise MobileUploadClientError("Cloud connection unavailable") from error

        if response.status_code in (401, 403):
            raise MobileUploadAuthError(f"HTTP {response.status_code}: authentication rejected")
        if not response.is_success:
            raise MobileUploadClientError(f"HTTP {response.status_code}: status query failed")

        body = json_object(response)
        expires = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
        return MobileSessionStatus(
            session_id=body["session_id"],
            status=body["status"],
            expires_at=expires,
            result_set_id=body.get("result_set_id"),
            pack_title=body.get("pack_title"),
            question_count=body.get("question_count"),
            error_code=body.get("error_code"),
            error_message=body.get("error_message"),
        )

    def cancel_session(self, session_id: str) -> str:
        if not self._auth_token:
            raise MobileUploadAuthError("Device authentication required")

        try:
            response = self._client.post(f"/api/v1/mobile-upload-sessions/{session_id}/cancel")
        except httpx.RequestError as error:
            raise MobileUploadClientError("Cloud connection unavailable") from error

        if response.is_success:
            return str(json_object(response).get("status", "CANCELLED"))
        return "CANCELLED"
