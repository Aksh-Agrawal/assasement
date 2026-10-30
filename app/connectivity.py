"""One persisted canonical connectivity state, shared across GUI and background processes."""

import json
import logging
import socket
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import httpx

LOGGER = logging.getLogger(__name__)

CLOUD_KEY = "connectivity_cloud"
INTERNET_KEY = "connectivity_internet"
WIFI_KEY = "connectivity_wifi"


def _update_setting(database_path: Path | str, key: str, updates: dict) -> None:
    path = Path(database_path)
    if not path.is_file() or path.stat().st_size == 0:
        return
    try:
        with sqlite3.connect(path, timeout=5) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            value = json.loads(row[0]) if row and row[0] else {}
            if not isinstance(value, dict):
                value = {}
            value.update(updates)
            connection.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) "
                "DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )
    except (sqlite3.Error, ValueError):
        LOGGER.exception("Unable to persist connectivity setting key=%s", key)


def record_cloud(database_path: Path | str, state: str) -> None:
    """Record cloud reachability and readiness; never persist tokens or URLs."""
    now = datetime.now(UTC).isoformat()
    updates = {"state": state, "observed_at": now}
    if state == "Online":
        updates["last_cloud_success"] = now

    _update_setting(database_path, CLOUD_KEY, updates)

    # Any HTTP response from the cloud server confirms that Internet is available
    if state in {"Online", "Server unavailable", "Authentication required"}:
        record_internet(database_path, "Available")


def record_internet(
    database_path: Path | str,
    state: str,
    *,
    dns_ok: bool = True,
    details: str = "",
) -> None:
    """Record independent internet reachability without coupling to cloud server."""
    now = datetime.now(UTC).isoformat()
    updates = {
        "state": state,
        "observed_at": now,
        "dns_ok": dns_ok,
    }
    if details:
        updates["details"] = details
    if state == "Available":
        updates["last_internet_success"] = now

    _update_setting(database_path, INTERNET_KEY, updates)


def record_wifi(database_path: Path | str, state: str, *, ssid: str = "") -> None:
    """Record Wi-Fi association state and connected SSID."""
    updates = {
        "state": state,
        "ssid": ssid,
        "observed_at": datetime.now(UTC).isoformat(),
    }
    _update_setting(database_path, WIFI_KEY, updates)


def cloud_state(repository_or_path) -> dict:
    try:
        if hasattr(repository_or_path, "get_setting"):
            raw = repository_or_path.get_setting(CLOUD_KEY)
        else:
            with sqlite3.connect(Path(repository_or_path), timeout=3) as conn:
                row = conn.execute("SELECT value FROM settings WHERE key=?", (CLOUD_KEY,)).fetchone()
                raw = row[0] if row else None
        return json.loads(raw or "{}")
    except (ValueError, TypeError, sqlite3.Error):
        return {}


def cloud_label(repository_or_path) -> str:
    return cloud_state(repository_or_path).get("state", "Checking…")


def internet_state(repository_or_path) -> dict:
    try:
        if hasattr(repository_or_path, "get_setting"):
            raw = repository_or_path.get_setting(INTERNET_KEY)
        else:
            with sqlite3.connect(Path(repository_or_path), timeout=3) as conn:
                row = conn.execute("SELECT value FROM settings WHERE key=?", (INTERNET_KEY,)).fetchone()
                raw = row[0] if row else None
        return json.loads(raw or "{}")
    except (ValueError, TypeError, sqlite3.Error):
        return {}


def internet_label(repository_or_path) -> str:
    return internet_state(repository_or_path).get("state", "Checking…")


def wifi_state(repository_or_path) -> dict:
    try:
        if hasattr(repository_or_path, "get_setting"):
            raw = repository_or_path.get_setting(WIFI_KEY)
        else:
            with sqlite3.connect(Path(repository_or_path), timeout=3) as conn:
                row = conn.execute("SELECT value FROM settings WHERE key=?", (WIFI_KEY,)).fetchone()
                raw = row[0] if row else None
        return json.loads(raw or "{}")
    except (ValueError, TypeError, sqlite3.Error):
        return {}


def wifi_label(repository_or_path) -> str:
    return wifi_state(repository_or_path).get("state", "disconnected")


def sync_label(repository) -> str:
    state = repository.get_setting("connectivity_sync")
    if state == "Authentication required":
        return state
    if state == "Syncing":
        try:
            started = datetime.fromisoformat(repository.get_setting("last_sync_attempt") or "")
            if 0 <= (datetime.now(UTC) - started).total_seconds() < 600:
                return state
        except (ValueError, TypeError):
            pass
    from app.data.repo import SyncStatus

    pending = repository.count_attempts_by_sync_status(SyncStatus.PENDING)
    pending += repository.count_attempts_by_sync_status(SyncStatus.FAILED)
    if repository.sync_diagnostic_summary()["attention_required"] or state == "Failed":
        return "Failed"
    return f"{pending} pending" if pending else "Up to date"


def record_probe(database_path: Path | str, network, *, internet_state: str | None = None) -> None:
    """Record explicit probe results. Server 503 does NOT mean internet is offline."""
    state = (
        "Checking…"
        if not network.checked
        else "Offline"
        if not network.backend_reachable
        else "Authentication required"
        if network.auth_accepted is False
        else "Server unavailable"
        if not network.database_ready
        else "Online"
    )
    record_cloud(database_path, state)

    if internet_state:
        record_internet(database_path, internet_state)
    elif network.backend_reachable:
        record_internet(database_path, "Available")


def check_internet_reachability(
    *,
    timeout: float = 4.0,
    cloud_base_url: str | None = None,
) -> tuple[bool, bool]:
    """Lightweight dual-stack HTTPS/DNS check for independent internet reachability.

    Returns:
        (internet_available: bool, dns_ok: bool)
    """
    dns_ok = False

    # 1. Check DNS resolution for a trusted host using dual-stack IPv4/IPv6
    test_hosts = ["dns.google", "google.com", "cloudflare.com"]
    if cloud_base_url:
        from urllib.parse import urlsplit
        host = urlsplit(cloud_base_url).netloc.split(":")[0]
        if host:
            test_hosts.insert(0, host)

    for host in test_hosts:
        try:
            socket.getaddrinfo(host, 443, socket.AF_UNSPEC)
            dns_ok = True
            break
        except (socket.gaierror, OSError):
            continue

    if not dns_ok:
        return False, False

    # 2. Lightweight HTTP/HTTPS check
    # Try cloud /health first if configured (serves dual purpose)
    endpoints = []
    if cloud_base_url:
        clean = cloud_base_url.rstrip("/")
        endpoints.append(f"{clean}/health")
    endpoints.extend([
        "https://dns.google",
        "https://www.google.com",
        "https://1.1.1.1",
    ])

    for url in endpoints:
        try:
            with httpx.Client(timeout=timeout, verify=True, follow_redirects=True) as client:
                resp = client.get(url)
                if 200 <= resp.status_code < 400:
                    return True, True
        except (httpx.RequestError, OSError):
            continue

    return False, dns_ok


class ObservedTransport(httpx.BaseTransport):
    """Observe actual HTTP I/O at the shared device transport boundary."""

    def __init__(self, database_path: Path | str, transport: httpx.BaseTransport | None = None):
        self.database_path = database_path
        self.transport = transport or httpx.HTTPTransport(verify=True)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        authenticated = bool(request.headers.get("Authorization"))
        try:
            response = self.transport.handle_request(request)
        except httpx.RequestError:
            if authenticated:
                record_cloud(self.database_path, "Offline")
            raise

        code = response.status_code
        # A response from the remote origin proves internet is active
        if 200 <= code < 600:
            record_internet(self.database_path, "Available")

        if authenticated:
            if 200 <= code < 300:
                record_cloud(self.database_path, "Online")
            elif code in {401, 403}:
                record_cloud(self.database_path, "Authentication required")
            elif code >= 500:
                record_cloud(self.database_path, "Server unavailable")

        return response

    def close(self) -> None:
        self.transport.close()
