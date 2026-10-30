"""Read-only device status, health evaluation, safe logging, and network probes."""

import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass
from enum import StrEnum
from hashlib import sha256
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import httpx

from app import __version__
from app.api.transport import create_client, json_object
from app.auth.credentials import CredentialStore
from app.data.repo import Repository, SyncStatus
from app.update.activation import ActivationManager


class HealthLevel(StrEnum):
    OK = "OK"
    DEGRADED = "DEGRADED"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    ERROR = "ERROR"


class SupportCode(StrEnum):
    DB_ERROR = "DB-001"
    SYNC_UNAVAILABLE = "SYNC-001"
    SYNC_BACKLOG = "SYNC-002"
    AUTH_MISSING = "AUTH-001"
    AUTH_REJECTED = "AUTH-002"
    CONTENT_ERROR = "CONTENT-001"
    UPDATE_ERROR = "UPDATE-001"
    BACKEND_UNAVAILABLE = "BACKEND-001"


@dataclass(frozen=True, slots=True)
class AttemptSummary:
    attempt_ref: str
    status: str
    question_set_id: str
    version: int
    sync_state: str
    started_at: str
    completed_at: str | None


@dataclass(frozen=True, slots=True)
class NetworkStatus:
    checked: bool = False
    backend_reachable: bool | None = None
    database_ready: bool | None = None
    auth_accepted: bool | None = None
    catalog_reachable: bool | None = None
    update_endpoint_reachable: bool | None = None
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class DeviceStatus:
    diagnostic_schema_version: int
    schema_version: int
    health: HealthLevel
    error_codes: tuple[str, ...]
    app_version: str
    local_db_status: str
    database_size_bytes: int
    device_id_present: bool
    paired: bool
    credential_present: bool
    device_revoked: bool | None
    in_progress_attempts: int
    completed_pending_sync: int
    failed_sync_count: int
    syncing_count: int
    auth_required_count: int
    last_sync_attempt: str | None
    last_sync_success: str | None
    last_sync_failure: str | None
    last_sync_error_code: str | None
    last_auth_failure: str | None
    last_recoverable_error_code: str | None
    installed_content_count: int
    installed_content_versions: tuple[str, ...]
    active_content_versions: tuple[str, ...]
    last_content_sync: dict[str, Any] | None
    current_release: str
    previous_release: str | None
    staged_release: str | None
    last_update_status: str
    last_update_check: str | None
    last_rollback_event: str | None
    trusted_signing_key_id: str
    offline_assessment_ready: bool
    attempts: tuple[AttemptSummary, ...]
    network: NetworkStatus
    cloud_status: str = "Checking…"
    network_manager_ok: bool = True
    wifi_connected: bool = False
    wifi_ssid: str | None = None
    ip_assigned: bool = True
    dns_ok: bool = True
    internet_status: str = "Checking…"
    full_sync: dict[str, Any] | None = None
    last_full_sync_success: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["health"] = self.health.value
        return value


_PATTERNS = (
    (re.compile(r"(?i)([\"']?(?:password|password_hash|pin_hash|pin_salt|token|access_token|refresh_token|api_key|service_role_key|supabase_service_role_key|supabase_secret_key|wifi_password|psk|admin_auth_secret|link_code|enrollment_code)[\"']?\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;}]+)"), r"\1[REDACTED]"),
    (re.compile(r"ENR-[A-Za-z0-9_-]+"), "[REDACTED_ENROLLMENT_CODE]"),
    (re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)\S+"), r"\1[REDACTED]"),
    (re.compile(r"device_[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[REDACTED_DEVICE_CREDENTIAL]"),
    (re.compile(r"(?i)((?:postgresql|postgres)\+?[^:]*://[^:/\s]+:)[^@\s]+@"), r"\1[REDACTED]@"),
    (re.compile(r"(?i)((?:DATABASE_URL|TEST_DATABASE_URL)\s*[:=]\s*)\S+"), r"\1[REDACTED]"),
    (re.compile(r"(?i)(pairing(?:_|\s+)code\s*[:=]\s*)\d{6}"), r"\1[REDACTED]"),
    (re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", re.S), "[REDACTED_PRIVATE_KEY]"),
)


def redact_text(value: str, *, secrets: tuple[str, ...] = ()) -> str:
    result = value
    for secret in secrets:
        if secret:
            result = result.replace(secret, "[REDACTED]")
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result


class SecretRedactionFilter(logging.Filter):
    def __init__(self, *, secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.secrets = secrets

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_text(record.getMessage(), secrets=self.secrets)
        record.args = ()
        return True


class SecretRedactingFormatter(logging.Formatter):
    """Redact the final rendered record, including exception and stack text."""

    def __init__(self, fmt: str, *, secrets: tuple[str, ...] = ()) -> None:
        super().__init__(fmt)
        self.secrets = secrets

    def format(self, record: logging.LogRecord) -> str:
        return redact_text(super().format(record), secrets=self.secrets)


def configure_logging(
    directory: Path, *, max_bytes: int = 1_000_000, backup_count: int = 3
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "assessment-device.log"
    handler = RotatingFileHandler(
        path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    handler.addFilter(SecretRedactionFilter())
    handler.setFormatter(
        SecretRedactingFormatter(
            "%(asctime)s level=%(levelname)s component=%(name)s event=%(message)s"
        )
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(
        isinstance(item, RotatingFileHandler)
        and item.baseFilename == str(path.resolve())
        for item in root.handlers
    ):
        root.addHandler(handler)
    return path


def _attempt_ref(identifier: str) -> str:
    return sha256(identifier.encode()).hexdigest()[:12]


def _parse_json(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        parsed = json.loads(value)
    except ValueError:
        return {"status": "UNKNOWN"}
    return parsed if isinstance(parsed, dict) else {"status": "UNKNOWN"}


def collect_device_status(
    repository: Repository,
    *,
    database_path: Path,
    credential_store: CredentialStore,
    update_manager: ActivationManager,
    trusted_signing_key_id: str,
    network: NetworkStatus | None = None,
) -> DeviceStatus:
    """Collect a read-only snapshot from existing repository/service APIs."""
    quick = repository.quick_check()
    metadata = repository.get_schema_meta()
    credential = credential_store.load_safe()
    sync = repository.sync_diagnostic_summary()
    installed = repository.list_question_sets()
    active = tuple(
        f"{item.id}:v{item.version}"
        for item in installed
        if repository.get_question_set_persistence(item.id, item.version).is_active
    )
    attempt_rows = repository.diagnostic_attempt_summary()
    attempts = tuple(
        AttemptSummary(
            attempt_ref=_attempt_ref(str(row["id"])),
            status=str(row["status"]),
            question_set_id=str(row["set_id"]),
            version=int(row["set_version"]),
            sync_state=str(row["sync_status"]),
            started_at=str(row["started_at"]),
            completed_at=str(row["completed_at"]) if row["completed_at"] else None,
        )
        for row in attempt_rows
    )
    counts = sync["counts"]
    update = update_manager.metadata()
    content = _parse_json(repository.get_setting("last_content_sync_status"))
    persisted_failure = _parse_json(repository.get_setting("last_sync_failure"))
    full_sync = _parse_json(repository.get_setting("last_full_sync"))
    from app.connectivity import cloud_label, internet_label, internet_state, wifi_state

    selected_network = network or NetworkStatus()
    auth_required = int(sync["auth_required"])
    codes: list[str] = []
    if not quick.ok:
        codes.append(SupportCode.DB_ERROR.value)
    if credential is None:
        codes.append(SupportCode.AUTH_MISSING.value)
    if selected_network.auth_accepted is False:
        codes.append(SupportCode.AUTH_REJECTED.value)
    if int(counts[SyncStatus.PENDING.value]) or int(counts[SyncStatus.FAILED.value]):
        codes.append(SupportCode.SYNC_BACKLOG.value)
    if full_sync and full_sync.get("result") in {"Failed", "Partially synced"}:
        codes.append(SupportCode.SYNC_UNAVAILABLE.value)
    if full_sync and full_sync.get("result") == "Authentication required":
        codes.append(SupportCode.AUTH_REJECTED.value)
    if selected_network.checked and selected_network.backend_reachable is False:
        codes.append(SupportCode.BACKEND_UNAVAILABLE.value)
    if content and content.get("status") not in {"COMPLETE", None}:
        codes.append(SupportCode.CONTENT_ERROR.value)
    if update.get("status") == "rolled_back":
        codes.append(SupportCode.UPDATE_ERROR.value)
    if not quick.ok:
        health = HealthLevel.ERROR
    elif selected_network.auth_accepted is False or credential is None or SupportCode.AUTH_REJECTED.value in codes:
        health = HealthLevel.ACTION_REQUIRED
    elif codes:
        health = HealthLevel.DEGRADED
    else:
        health = HealthLevel.OK

    nm_ok = shutil.which("nmcli") is not None
    w_info = wifi_state(repository)
    wifi_is_conn = w_info.get("state") == "connected"
    wifi_active_ssid = w_info.get("ssid") or None
    inet_info = internet_state(repository)
    dns_status = inet_info.get("dns_ok", True)
    inet_label = internet_label(repository)

    return DeviceStatus(
        diagnostic_schema_version=1,
        schema_version=repository.schema_version,
        health=health,
        error_codes=tuple(dict.fromkeys(codes)),
        app_version=__version__,
        local_db_status="ok" if quick.ok else "error",
        database_size_bytes=database_path.stat().st_size if database_path.exists() else 0,
        device_id_present=bool(metadata.get("device_id")),
        paired=credential is not None,
        credential_present=credential is not None,
        device_revoked=True if selected_network.auth_accepted is False else None,
        in_progress_attempts=int(sync["in_progress"]),
        completed_pending_sync=int(counts[SyncStatus.PENDING.value]),
        failed_sync_count=int(counts[SyncStatus.FAILED.value]),
        syncing_count=int(counts[SyncStatus.SYNCING.value]),
        auth_required_count=auth_required,
        last_sync_attempt=repository.get_setting("last_sync_attempt"),
        last_sync_success=repository.get_setting("last_sync_success") or sync["last_success"],
        last_sync_failure=(
            str(persisted_failure.get("at"))
            if persisted_failure and persisted_failure.get("at")
            else sync["last_failure"]
        ),
        last_sync_error_code=(
            str(persisted_failure.get("error_code"))
            if persisted_failure and persisted_failure.get("error_code")
            else SupportCode.AUTH_REJECTED.value
            if sync["last_error_kind"] == "authentication"
            else SupportCode.SYNC_UNAVAILABLE.value
            if sync["last_error_kind"]
            else None
        ),
        last_auth_failure=(
            str(persisted_failure.get("at"))
            if persisted_failure and persisted_failure.get("kind") == "authentication"
            else None
        ),
        last_recoverable_error_code=(codes[-1] if codes else None),
        installed_content_count=len({item.id for item in installed}),
        installed_content_versions=tuple(f"{item.id}:v{item.version}" for item in installed),
        active_content_versions=active,
        last_content_sync=content,
        current_release=str(update.get("current") or __version__),
        previous_release=update.get("previous"),
        staged_release=update.get("staged"),
        last_update_status=str(update.get("status", "idle")),
        last_update_check=update.get("checked_at"),
        last_rollback_event=("recorded" if update.get("status") == "rolled_back" else None),
        trusted_signing_key_id=trusted_signing_key_id,
        offline_assessment_ready=quick.ok and bool(installed),
        attempts=attempts,
        network=selected_network,
        cloud_status=cloud_label(repository),
        network_manager_ok=nm_ok,
        wifi_connected=wifi_is_conn,
        wifi_ssid=wifi_active_ssid,
        ip_assigned=True,
        dns_ok=bool(dns_status),
        internet_status=inet_label,
        full_sync=full_sync,
        last_full_sync_success=repository.get_setting("last_full_sync_success"),
    )


def collect_network_status(
    base_url: str | None,
    *,
    auth_token: str | None,
    connect_timeout: float = 5.0,
    read_timeout: float = 10.0,
) -> NetworkStatus:
    if not base_url:
        return NetworkStatus(checked=False)
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
    backend_reachable = False
    database_ready = False
    catalog_reachable = False
    update_reachable = False
    auth_ok = None

    try:
        with create_client(base_url, connect_timeout=connect_timeout, read_timeout=read_timeout) as client:
            try:
                health = client.get("/health")
                backend_reachable = (health.status_code == 200)
            except httpx.RequestError:
                return NetworkStatus(checked=True, backend_reachable=False, error_code="BACKEND-001")

            if not backend_reachable:
                return NetworkStatus(checked=True, backend_reachable=False, error_code="BACKEND-001")

            try:
                ready = client.get("/ready")
                database_ready = (ready.status_code == 200 and json_object(ready).get("database") == "ok")
            except (httpx.RequestError, ValueError, TypeError):
                database_ready = False

            if auth_token:
                try:
                    catalog = client.get("/api/v1/content/catalog", headers=headers)
                    catalog_reachable = (catalog.status_code == 200)
                    if catalog.status_code in {200, 401, 403}:
                        auth_ok = (catalog.status_code == 200)
                except httpx.RequestError:
                    catalog_reachable = False

                try:
                    update = client.get("/api/v1/device-updates/latest", headers=headers)
                    update_reachable = update.status_code in {200, 404}
                except httpx.RequestError:
                    update_reachable = False

    except httpx.RequestError:
        return NetworkStatus(checked=True, backend_reachable=False, error_code="BACKEND-001")

    return NetworkStatus(
        checked=True,
        backend_reachable=backend_reachable,
        database_ready=database_ready,
        auth_accepted=auth_ok,
        catalog_reachable=catalog_reachable,
        update_endpoint_reachable=update_reachable,
        error_code=SupportCode.AUTH_REJECTED.value if auth_ok is False else None,
    )
