"""Authenticated operational heartbeat with an explicit allowlist payload."""

from dataclasses import dataclass
from typing import Literal

import httpx

from app.api.transport import create_client, json_object


@dataclass(frozen=True, slots=True)
class Heartbeat:
    software_version: str
    installed_pack_count: int
    pending_attempt_count: int
    free_storage_bytes: int
    diagnostic_summary: Literal["OK", "DEGRADED", "ACTION_REQUIRED", "ERROR"] = "OK"

    def to_dict(self) -> dict[str, str | int]:
        if self.diagnostic_summary not in {"OK", "DEGRADED", "ACTION_REQUIRED", "ERROR"}:
            raise ValueError("Heartbeat diagnostic summary must be a safe health level")
        from packaging.version import Version

        Version(self.software_version)
        if any(
            type(value) is not int or value < 0
            for value in (
                self.installed_pack_count,
                self.pending_attempt_count,
                self.free_storage_bytes,
            )
        ):
            raise ValueError("Heartbeat counts must be non-negative integers")
        return {
            "software_version": self.software_version,
            "installed_pack_count": self.installed_pack_count,
            "pending_attempt_count": self.pending_attempt_count,
            "free_storage_bytes": self.free_storage_bytes,
            "diagnostic_summary": self.diagnostic_summary,
        }


class HeartbeatClient:
    def __init__(
        self,
        base_url: str,
        *,
        auth_token: str | None,
        timeout: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self._paired = bool(auth_token)
        self._client = create_client(base_url, auth_token=auth_token, connect_timeout=timeout, read_timeout=timeout, transport=transport)

    def send(self, heartbeat: Heartbeat) -> None:
        if not self._paired:
            raise ValueError("Device pairing is required")
        response = self._client.post("/api/v1/devices/heartbeat", json=heartbeat.to_dict())
        response.raise_for_status()
        if json_object(response) != {"status": "accepted"}:
            raise ValueError("Invalid heartbeat acknowledgement")

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
