"""One-shot sync worker over committed local assessment data."""

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.data.repo import Repository
from app.faults import FaultHook, no_fault
from app.sync.client import SyncApiClient
from app.sync.errors import (
    AlreadySynced,
    AuthenticationError,
    PermanentSyncError,
    TransientSyncError,
)
from app.sync.payloads import build_upload_payload
from app.sync.policy import SyncPolicy

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class SyncCycleResult:
    """Non-sensitive summary of one explicit worker cycle."""

    recovered_stale: int = 0
    selected: int = 0
    synced: int = 0
    already_synced: int = 0
    transient_failures: int = 0
    permanent_failures: int = 0
    authentication_failures: int = 0


class SyncWorker:
    """Select bounded local work and upload each attempt independently."""

    def __init__(
        self,
        repository: Repository,
        client: SyncApiClient,
        *,
        policy: SyncPolicy | None = None,
        clock: Callable[[], datetime] | None = None,
        fault_hook: FaultHook = no_fault,
    ) -> None:
        self.repository = repository
        self.client = client
        self.policy = policy or SyncPolicy()
        self.clock = clock or (lambda: datetime.now(UTC))
        self.fault_hook = fault_hook

    def run_sync_once(self) -> SyncCycleResult:
        """Recover stale work and process at most one configured batch without sleeping."""
        self.repository.set_setting("connectivity_sync", "Syncing")
        now = self.clock()
        self.repository.set_setting("last_sync_attempt", now.isoformat())
        recovered = self.repository.recover_stale_syncing(
            now=now,
            stale_after=timedelta(seconds=self.policy.stale_syncing_seconds),
        )
        attempts = self.repository.get_sync_eligible_attempts(
            now=now,
            limit=self.policy.batch_size,
            max_attempts=self.policy.max_automatic_retries,
        )
        counts = {
            "synced": 0,
            "already_synced": 0,
            "transient_failures": 0,
            "permanent_failures": 0,
            "authentication_failures": 0,
        }
        LOGGER.info("sync cycle started selected=%d recovered_stale=%d", len(attempts), recovered)

        for attempt in attempts:
            LOGGER.info("sync attempt selected attempt_id=%s", attempt.id)
            self.repository.mark_attempt_syncing(attempt.id, started_at=self.clock())
            self.fault_hook("AFTER_SYNC_MARKED_SYNCING")
            state = self.repository.get_attempt_sync_state(attempt.id)
            try:
                payload = build_upload_payload(self.repository, attempt.id)
                self.client.upload_attempt(payload, attempt.id)
                self.fault_hook("BEFORE_LOCAL_SYNC_ACK")
            except AlreadySynced:
                synced_at = self.clock()
                self.repository.mark_attempt_synced(attempt.id, synced_at=synced_at)
                self.repository.set_setting("last_sync_success", synced_at.isoformat())
                counts["synced"] += 1
                counts["already_synced"] += 1
                LOGGER.info("sync idempotent success attempt_id=%s", attempt.id)
            except AuthenticationError as error:
                self._record_failure(attempt.id, error, "authentication", state.attempts + 1)
                counts["authentication_failures"] += 1
                LOGGER.warning("sync authentication failure attempt_id=%s", attempt.id)
                break
            except PermanentSyncError as error:
                self._record_failure(attempt.id, error, "permanent", state.attempts + 1)
                counts["permanent_failures"] += 1
                LOGGER.warning("sync permanent failure attempt_id=%s", attempt.id)
            except TransientSyncError as error:
                self._record_failure(attempt.id, error, "transient", state.attempts + 1)
                counts["transient_failures"] += 1
                LOGGER.warning("sync retryable failure attempt_id=%s", attempt.id)
            except Exception as error:  # Defensive: preserve data on unexpected local failure.
                wrapped = PermanentSyncError(f"local payload failure: {error}")
                self._record_failure(attempt.id, wrapped, "permanent", state.attempts + 1)
                counts["permanent_failures"] += 1
                LOGGER.exception("unexpected sync failure attempt_id=%s", attempt.id)
            else:
                synced_at = self.clock()
                self.repository.mark_attempt_synced(attempt.id, synced_at=synced_at)
                self.repository.set_setting("last_sync_success", synced_at.isoformat())
                counts["synced"] += 1
                LOGGER.info("sync upload success attempt_id=%s", attempt.id)

        self.repository.set_setting("connectivity_sync",
            "Authentication required" if counts["authentication_failures"] else
            "Failed" if counts["permanent_failures"] or counts["transient_failures"] else
            "Up to date")
        return SyncCycleResult(
            recovered_stale=recovered,
            selected=len(attempts),
            **counts,
        )

    def _record_failure(
        self,
        attempt_id: str,
        error: Exception,
        error_kind: str,
        attempt_number: int,
    ) -> None:
        failure_at = self.clock()
        retry_at = None
        if error_kind == "transient" and attempt_number < self.policy.max_automatic_retries:
            retry_at = failure_at + timedelta(
                seconds=self.policy.next_retry_delay(attempt_number)
            )
        self.repository.mark_attempt_sync_failed(
            attempt_id,
            error=str(error),
            error_kind=error_kind,
            next_sync_at=retry_at,
        )
        code = "AUTH-002" if error_kind == "authentication" else "SYNC-001"
        self.repository.set_setting(
            "last_sync_failure",
            json.dumps(
                {"at": failure_at.isoformat(), "error_code": code, "kind": error_kind},
                separators=(",", ":"),
                sort_keys=True,
            ),
        )


def run_sync_once(
    repository: Repository,
    client: SyncApiClient,
    *,
    policy: SyncPolicy | None = None,
) -> SyncCycleResult:
    """Convenience entry point for schedulers and development tooling."""
    return SyncWorker(repository, client, policy=policy).run_sync_once()
