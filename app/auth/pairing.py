"""HTTP pairing client; it never logs or displays the issued credential."""

import time
from dataclasses import dataclass
from datetime import datetime

import httpx

from app.auth.credentials import CredentialStore, DeviceCredential


@dataclass(frozen=True, slots=True)
class PairingRequest:
    session_id: str
    code: str
    claim_secret: str
    expires_at: datetime


class PairingClient:
    def __init__(self, base_url: str, *, timeout: float = 15.0) -> None:
        self._client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "PairingClient":
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()

    def request(self, device_id: str, device_name: str | None = None) -> PairingRequest:
        response = self._client.post(
            "/api/v1/pairing/request",
            json={"device_id": device_id, "device_name": device_name},
        )
        response.raise_for_status()
        body = response.json()
        return PairingRequest(
            session_id=body["session_id"],
            code=body["pairing_code"],
            claim_secret=body["claim_secret"],
            expires_at=datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00")),
        )

    def status(self, pairing: PairingRequest) -> str:
        response = self._client.get(
            f"/api/v1/pairing/{pairing.session_id}/status",
            headers={"X-Pairing-Claim": pairing.claim_secret},
        )
        response.raise_for_status()
        return str(response.json()["status"])

    def claim(self, pairing: PairingRequest, store: CredentialStore, device_id: str) -> None:
        response = self._client.post(
            f"/api/v1/pairing/{pairing.session_id}/claim",
            headers={"X-Pairing-Claim": pairing.claim_secret},
        )
        response.raise_for_status()
        store.save(DeviceCredential(device_id=device_id, token=response.json()["credential"]))

    def wait_and_claim(
        self,
        pairing: PairingRequest,
        store: CredentialStore,
        device_id: str,
        *,
        interval: float = 2.0,
        timeout: float = 600.0,
    ) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.status(pairing)
            if state == "approved":
                self.claim(pairing, store, device_id)
                return
            if state in {"expired", "consumed"}:
                raise RuntimeError(f"Pairing session is {state}")
            time.sleep(interval)
        raise TimeoutError("Pairing approval timed out")
