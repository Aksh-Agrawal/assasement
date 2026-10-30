"""Systemd-friendly periodic sync; assessment runs independently in the UI process."""

import json
import logging
import shutil
import signal
import threading
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
        return
    with Repository(config.database_path) as repository:
        if refresh and repository.get_student_account_context():
            from app.auth.account_device import sync_account
            # Verification/reconciliation precedes delivery. Failure preserves local work
            # and stops this cycle rather than uploading under stale relationships.
            sync_account(config, api.store, repository)
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
                diagnostic_summary="OK" if repository.quick_check().ok else "ERROR",
                auto_sync_enabled=repository.get_setting("automatic_sync") != "0",
            )
            try:
                with api.heartbeat() as client:
                    client.send(payload)
            except Exception as error:
                # Upload acknowledgements remain successful even if heartbeat is down.
                repository.set_setting("last_heartbeat_state", type(error).__name__)
            else:
                repository.set_setting("last_heartbeat_state", "OK")
        if refresh:
            repository.set_setting("connectivity_sync", "Syncing")
        deliveries_ok = True
        if refresh:
            # Student delivery jobs run in this background worker, never the GUI thread.
            from app.content.profile_library import sync_profile_deliveries
            deliveries_ok = sync_profile_deliveries(repository, api, config) is not False
            if not deliveries_ok:
                repository.set_setting("connectivity_sync", "Failed")
            from app.content.institute_work import sync_institute_work
            sync_institute_work(repository, api, config)
            # Refresh metadata only; content installation and update activation are explicit.
            for name, make_client, fetch in (() if not heartbeat else (
                ("catalogue", api.content, lambda client: client.fetch_catalog()),
                ("update", api.updates, lambda client: client.check_for_update()),
            )):
                client = None
                try:
                    client = make_client()
                    fetch(client)
                    repository.set_setting(f"last_{name}_check", "OK")
                except Exception as error:
                    repository.set_setting(f"last_{name}_check", json.dumps(
                        {"state": "UNAVAILABLE", "kind": type(error).__name__}
                    ))
                finally:
                    if client is not None:
                        client.close()
        if refresh:
            repository.set_setting("connectivity_sync",
                "Authentication required" if result.authentication_failures else
                "Failed" if not deliveries_ok or result.transient_failures or result.permanent_failures else
                "Up to date")
        from app.connectivity import cloud_state
        contact = cloud_state(repository)
        if ((refresh or repository.get_setting("automatic_sync") != "0")
                and deliveries_ok and contact.get("state") == "Online"
                and contact.get("last_cloud_success", "") >= started_at
                and not (result.authentication_failures or result.permanent_failures
                         or result.transient_failures)):
            repository.set_setting("last_sync_success", datetime.now(UTC).isoformat())
        return result


def run_cycle(config: AppConfig, *, heartbeat: bool = True, refresh: bool = False):
    from app.sync.locking import file_lock
    with file_lock(str(config.database_path) + ".sync.lock"):
        try:
            return _run_cycle(config, heartbeat=heartbeat, refresh=refresh)
        except Exception:
            if config.database_path.exists():
                from app.connectivity import cloud_label
                with Repository(config.database_path) as repository:
                    repository.set_setting("connectivity_sync", "Authentication required"
                        if cloud_label(repository) == "Authentication required" else "Failed")
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
