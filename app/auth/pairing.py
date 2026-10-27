"""HTTP pairing client; it never logs or displays the issued credential."""

import time
from dataclasses import dataclass, field
from datetime import datetime

import httpx

from app.api.transport import create_client, json_object
from app.auth.credentials import CredentialStore, DeviceCredential


@dataclass(frozen=True, slots=True)
class PairingRequest:
    session_id: str
    code: str
    claim_secret: str = field(repr=False)
    expires_at: datetime


class PairingClient:
    def __init__(self, base_url: str, *, timeout: float = 15.0,
                 transport: httpx.BaseTransport | None = None) -> None:
        self._client = create_client(base_url, connect_timeout=timeout, read_timeout=timeout, transport=transport)

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
        body = json_object(response)
        if any(not isinstance(body.get(key), str) or not body[key].strip()
               for key in ("session_id", "pairing_code", "claim_secret", "expires_at")):
            raise ValueError("Invalid pairing response")
        expires = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
        if expires.tzinfo is None:
            raise ValueError("Pairing expiry must include timezone")
        return PairingRequest(
            session_id=body["session_id"],
            code=body["pairing_code"],
            claim_secret=body["claim_secret"],
            expires_at=expires,
        )

    def status(self, pairing: PairingRequest) -> str:
        response = self._client.get(
            f"/api/v1/pairing/{pairing.session_id}/status",
            headers={"X-Pairing-Claim": pairing.claim_secret},
        )
        response.raise_for_status()
        return str(json_object(response)["status"])

    def claim(self, pairing: PairingRequest, store: CredentialStore, device_id: str) -> None:
        response = self._client.post(
            f"/api/v1/pairing/{pairing.session_id}/claim",
            headers={"X-Pairing-Claim": pairing.claim_secret},
        )
        response.raise_for_status()
        token = json_object(response).get("credential")
        if not isinstance(token, str) or not token.strip():
            raise ValueError("Invalid device credential response")
        store.save(DeviceCredential(device_id=device_id, token=token))

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
            if state in {"expired", "consumed", "denied"}:
                raise RuntimeError(f"Pairing session is {state}")
            time.sleep(interval)
        raise TimeoutError("Pairing approval timed out")
