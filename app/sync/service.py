"""Systemd-friendly periodic sync; assessment runs independently in the UI process."""

import json
import logging
import shutil
import signal
import threading
from dataclasses import replace
from datetime import UTC, datetime

from app.api.client import DeviceApi
from app.api.heartbeat import Heartbeat
from app.config import AppConfig
from app.data.repo import Repository, SyncStatus
from app.sync.policy import SyncPolicy
from app.sync.worker import SyncWorker

LOGGER = logging.getLogger(__name__)


def _run_cycle(config: AppConfig, *, heartbeat: bool = True, refresh: bool = False):
    if not config.api_base_url:
        return
    started_at = datetime.now(UTC).isoformat()
    api = DeviceApi(config)
    if not api.store.load_safe():
        from app.connectivity import record_cloud
        record_cloud(config.database_path, "Authentication required")
        from app.sync.worker import SyncCycleResult
        with Repository(config.database_path) as repository:
            repository.set_setting("connectivity_sync", "Authentication required")
            repository.set_setting("last_full_sync", json.dumps({
                "at": started_at, "result": "Authentication required",
                "error_kind": "CredentialMissing"}))
        return SyncCycleResult(authentication_failures=1)
    with Repository(config.database_path) as repository:
        stages = {}
        repository.set_setting("last_sync_attempt", started_at)
        if refresh and (repository.get_student_account_context()
                        or not repository.list_profiles()
                        or any(p.id.startswith("cloud-") for p in repository.list_profiles())):
            from app.auth.account_device import sync_account
            # Verification/reconciliation precedes delivery. Failure preserves local work
            # and stops this cycle rather than uploading under stale relationships.
            sync_account(config, api.store, repository, transport=api.transport)
            stages["account"] = "OK"
        if not refresh and repository.get_setting("automatic_sync") == "0":
            from app.sync.worker import SyncCycleResult
            result = SyncCycleResult()
        else:
            with api.attempts() as client:
                result = SyncWorker(
                    repository,
                    client,
                    policy=SyncPolicy(
                        batch_size=config.sync_batch_size,
                        max_automatic_retries=config.sync_max_automatic_retries,
                        stale_syncing_seconds=config.sync_stale_after_seconds,
                    ),
                ).run_sync_once()
        if heartbeat:
            pending = sum(
                repository.count_attempts_by_sync_status(status)
                for status in (SyncStatus.PENDING, SyncStatus.FAILED, SyncStatus.SYNCING)
            )
            payload = Heartbeat(
                software_version=config.application_version,
                installed_pack_count=len(repository.list_question_sets()),
                pending_attempt_count=pending,
                free_storage_bytes=shutil.disk_usage(config.database_path.parent).free,
                diagnostic_summary=("ERROR" if not repository.quick_check().ok else
                    "ACTION_REQUIRED" if result.authentication_failures else
                    "DEGRADED" if result.transient_failures or result.permanent_failures
                    or json.loads(repository.get_setting("last_full_sync") or "{}").get("result")
                    in {"Failed", "Partially synced"}
                    else "OK"),
                auto_sync_enabled=repository.get_setting("automatic_sync") != "0",
            )
            try:
                with api.heartbeat() as client:
                    client.send(payload)
            except Exception as error:
                # Upload acknowledgements remain successful even if heartbeat is down.
                repository.set_setting("last_heartbeat_state", type(error).__name__)
                stages["heartbeat"] = type(error).__name__
            else:
                repository.set_setting("last_heartbeat_state", "OK")
                stages["heartbeat"] = "OK"
        if refresh:
            repository.set_setting("connectivity_sync", "Syncing")
        deliveries_ok = True
        if refresh:
            # Student delivery jobs run in this background worker, never the GUI thread.
            from app.content.profile_library import sync_profile_deliveries
            deliveries_ok = sync_profile_deliveries(repository, api, config) is not False
            stages["content"] = "OK" if deliveries_ok else "Delivery reconciliation failed"
            if not deliveries_ok:
                repository.set_setting("connectivity_sync", "Failed")
            from app.content.institute_work import sync_institute_work
            stages["institute"] = "OK" if sync_institute_work(repository, api, config) else "Unavailable"
            from app.sync.history import sync_history
            history_ok = sync_history(repository, api)
            stages["history"] = "OK" if history_ok else "History fetch failed"
            if not deliveries_ok or not history_ok:
                result = replace(result, stage_failures=result.stage_failures +
                                 int(not deliveries_ok) + int(not history_ok))
            # Refresh metadata only; content installation and update activation are explicit.
            for name, make_client, fetch in (() if not heartbeat else (
                ("catalogue", api.content, lambda client: client.fetch_catalog()),
                ("update", api.updates, lambda client: client.check_for_update()),
            )):
                client = None
                try:
                    client = make_client()
                    value = fetch(client)
                    state = "No update available" if name == "update" and value is None else "OK"
                    repository.set_setting(f"last_{name}_check", state)
                    stages[name] = state
                except Exception as error:
                    repository.set_setting(f"last_{name}_check", json.dumps(
                        {"state": "UNAVAILABLE", "kind": type(error).__name__}
                    ))
                    stages[name] = type(error).__name__
                finally:
                    if client is not None:
                        client.close()
        if refresh:
            repository.set_setting("connectivity_sync",
                "Authentication required" if result.authentication_failures else
                "Partially synced" if result.stage_failures or result.transient_failures or result.permanent_failures else
                "Up to date")
            stages["attempt_uploads"] = {
                "selected": result.selected, "uploaded": result.synced,
                "failed": result.transient_failures + result.permanent_failures + result.authentication_failures}
            repository.set_setting("last_full_sync", json.dumps(
                {"at": started_at, "result": repository.get_setting("connectivity_sync"),
                 "stages": stages,
                 "profiles": json.loads(repository.get_setting("last_profile_reconciliation") or "{}"),
                 "content": json.loads(repository.get_setting("last_delivery_summary") or "{}"),
                 "history": json.loads(repository.get_setting("last_history_summary") or "{}")}))
        from app.connectivity import cloud_state
        contact = cloud_state(repository)
        if ((refresh or repository.get_setting("automatic_sync") != "0")
                and deliveries_ok and contact.get("state") == "Online"
                and contact.get("last_cloud_success", "") >= started_at
                and not (result.authentication_failures or result.permanent_failures
                         or result.transient_failures or result.stage_failures)):
            repository.set_setting("last_sync_success", datetime.now(UTC).isoformat())
            if refresh:
                repository.set_setting("last_full_sync_success", datetime.now(UTC).isoformat())
        return result


def run_cycle(config: AppConfig, *, heartbeat: bool = True, refresh: bool = False):
    from app.sync.locking import file_lock
    with file_lock(str(config.database_path) + ".sync.lock"):
        try:
            return _run_cycle(config, heartbeat=heartbeat, refresh=refresh)
        except Exception as error:
            if config.database_path.exists():
                from app.api.transport import FailureState, failure_state
                from app.connectivity import cloud_label
                from app.content.client import ContentAuthError
                with Repository(config.database_path) as repository:
                    auth = isinstance(error, ContentAuthError) or failure_state(error) == FailureState.AUTH_REQUIRED
                    state = "Authentication required" if auth else "Failed"
                    repository.set_setting("connectivity_sync", state)
                    repository.set_setting("last_full_sync", json.dumps({
                        "at": datetime.now(UTC).isoformat(), "result": state,
                        "error_kind": type(error).__name__,
                        "http_status": getattr(getattr(error, "response", None), "status_code", None),
                        "cloud": cloud_label(repository)}))
                    LOGGER.warning("sync reconciliation failed kind=%s status=%s",
                        type(error).__name__, getattr(getattr(error, "response", None), "status_code", None))
            raise


def main() -> int:
    from app.sync.scheduler import AutoSyncScheduler
    config = AppConfig()
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_args: stop.set())
    AutoSyncScheduler(config).run(stop)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
