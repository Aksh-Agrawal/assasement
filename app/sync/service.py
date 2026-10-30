"""Systemd-friendly periodic sync; assessment runs independently in the UI process."""

import json
import logging
import shutil
import signal
import threading
import time

from app.api.client import DeviceApi
from app.api.heartbeat import Heartbeat
from app.config import AppConfig
from app.data.repo import Repository, SyncStatus
from app.sync.policy import SyncPolicy
from app.sync.worker import SyncWorker

LOGGER = logging.getLogger(__name__)


def run_cycle(config: AppConfig, *, heartbeat: bool = True, refresh: bool = False):
    if not config.api_base_url:
        return
    api = DeviceApi(config)
    if not api.store.load_safe():
        return
    with Repository(config.database_path) as repository:
        if refresh and repository.get_student_account_context():
            from app.auth.account_device import sync_account
            # Verification/reconciliation precedes delivery. Failure preserves local work
            # and stops this cycle rather than uploading under stale relationships.
            sync_account(config, api.store, repository)
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
                diagnostic_summary="OK" if repository.integrity_check().ok else "ERROR",
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
            # Student delivery jobs run in this background worker, never the GUI thread.
            from app.content.profile_library import sync_profile_deliveries
            sync_profile_deliveries(repository, api, config)
            from app.content.institute_work import sync_institute_work
            sync_institute_work(repository, api, config)
            # Refresh metadata only; content installation and update activation are explicit.
            for name, make_client, fetch in (
                ("catalogue", api.content, lambda client: client.fetch_catalog()),
                ("update", api.updates, lambda client: client.check_for_update()),
            ):
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
        return result


def main() -> int:
    config = AppConfig()
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_args: stop.set())
    next_heartbeat = 0.0
    while not stop.is_set():
        now = time.monotonic()
        due = now >= next_heartbeat
        try:
            run_cycle(config, heartbeat=due, refresh=due)
        except Exception as error:
            # Exception messages may contain URLs or credentials; emit only the class.
            LOGGER.warning("Background cloud cycle unavailable (%s)", type(error).__name__)
        if due:
            next_heartbeat = now + config.heartbeat_interval_seconds
        stop.wait(config.sync_interval_seconds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
