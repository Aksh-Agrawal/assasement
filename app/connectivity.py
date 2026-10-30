"""One persisted cloud state, shared across GUI and background processes."""

import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import httpx

LOGGER = logging.getLogger(__name__)
CLOUD_KEY = "connectivity_cloud"


def record_cloud(database_path, state):
    """Record evidence only; never persist URLs, headers, tokens or response bodies."""
    path = Path(database_path)
    if not path.is_file() or path.stat().st_size == 0:
        return
    try:
        with sqlite3.connect(path, timeout=5) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT value FROM settings WHERE key=?", (CLOUD_KEY,)).fetchone()
            value = json.loads(row[0]) if row else {}
            if not isinstance(value, dict):
                value = {}
            value.update(state=state, observed_at=datetime.now(UTC).isoformat())
            if state == "Online":
                value["last_cloud_success"] = value["observed_at"]
            connection.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) "
                               "DO UPDATE SET value=excluded.value", (CLOUD_KEY, json.dumps(value)))
    except (sqlite3.Error, ValueError):
        LOGGER.exception("Unable to persist cloud contact state")


def cloud_state(repository):
    try:
        return json.loads(repository.get_setting(CLOUD_KEY) or "{}")
    except (ValueError, TypeError):
        return {}


def cloud_label(repository):
    return cloud_state(repository).get("state", "Checking…")


def sync_label(repository):
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


def record_probe(database_path, network):
    state = ("Checking…" if not network.checked else
             "Offline" if not network.backend_reachable else
             "Authentication required" if network.auth_accepted is False else
             "Server unavailable" if not network.database_ready else "Online")
    record_cloud(database_path, state)


class ObservedTransport(httpx.BaseTransport):
    """Observe actual authenticated I/O at the shared device transport boundary."""

    def __init__(self, database_path, transport=None):
        self.database_path = database_path
        self.transport = transport or httpx.HTTPTransport(verify=True)

    def handle_request(self, request):
        authenticated = bool(request.headers.get("Authorization"))
        try:
            response = self.transport.handle_request(request)
        except httpx.RequestError:
            if authenticated:
                record_cloud(self.database_path, "Offline")
            raise
        if authenticated:
            code = response.status_code
            if 200 <= code < 300:
                record_cloud(self.database_path, "Online")
            elif code in {401, 403}:
                record_cloud(self.database_path, "Authentication required")
            elif code >= 500:
                record_cloud(self.database_path, "Server unavailable")
        return response

    def close(self):
        self.transport.close()
