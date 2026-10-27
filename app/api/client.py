"""Configuration-based construction of the existing HTTP domain clients.

No server code, network requests, or credential reads occur on import.
"""

import httpx

from app.api.heartbeat import HeartbeatClient
from app.auth.credentials import CredentialStore
from app.auth.pairing import PairingClient
from app.config import AppConfig
from app.content.client import ContentApiClient
from app.sync.client import SyncApiClient
from app.update.client import UpdateClient


class DeviceApi:
    def __init__(
        self,
        config: AppConfig,
        *,
        store: CredentialStore | None = None,
        transport: httpx.BaseTransport | None = None,
    ):
        if not config.api_base_url:
            raise ValueError("Set ASSESS_API_URL before using cloud services")
        self.config = config
        self.store = store or CredentialStore(config.credential_path)
        self.transport = transport

    def _token(self) -> str | None:
        credential = self.store.load_safe()
        return credential.token if credential else None

    def pairing(self) -> PairingClient:
        return PairingClient(
            self.config.api_base_url,
            timeout=self.config.sync_read_timeout,
            transport=self.transport,
        )

    def content(self) -> ContentApiClient:
        return ContentApiClient(
            self.config.api_base_url,
            auth_token=self._token(),
            connect_timeout=self.config.sync_connect_timeout,
            read_timeout=self.config.sync_read_timeout,
            transport=self.transport,
        )

    def attempts(self) -> SyncApiClient:
        return SyncApiClient(
            self.config.api_base_url,
            auth_token=self._token(),
            connect_timeout=self.config.sync_connect_timeout,
            read_timeout=self.config.sync_read_timeout,
            transport=self.transport,
        )

    def heartbeat(self) -> HeartbeatClient:
        return HeartbeatClient(
            self.config.api_base_url,
            auth_token=self._token(),
            timeout=self.config.sync_read_timeout,
            transport=self.transport,
        )

    def updates(self) -> UpdateClient:
        token = self._token()
        if not token:
            raise ValueError("Device pairing is required")
        return UpdateClient(
            self.config.api_base_url,
            token,
            timeout=self.config.sync_read_timeout,
            transport=self.transport,
        )
