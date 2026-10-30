"""Single bounded automatic synchronization scheduler; no Qt dependencies."""
import json
import logging
import random
import threading
import time
from datetime import UTC, datetime, timedelta

from app.data.repo import Repository
from app.data.scheduler_state import read_scheduler_state, set_next_sync
from app.sync.locking import file_lock

LOGGER = logging.getLogger(__name__)


class AutoSyncScheduler:
    def __init__(self, config, *, cycle=None, clock=time.monotonic, jitter=None):
        from app.sync.service import run_cycle
        self.config, self.cycle, self.clock = config, cycle or run_cycle, clock
        self.jitter = jitter or (lambda: random.uniform(0, 2))
        self.next_due = 0.0
        self.next_heartbeat = 0.0
        self.failures = 0
        self.previous_cloud = None
        self.previous_internet = None
        self.enabled = None
        self.stop = threading.Event()
        self.thread = None
        self.initialized = False
        self.request_seen = None

    def tick(self):
        now = self.clock()
        if not self.config.api_base_url:
            return
        if not self.initialized:
            with Repository(self.config.database_path):
                pass
            self.initialized = True
        # Local wake-up checks read only settings, without reopening/validating all packs.
        values = read_scheduler_state(self.config.database_path)
        request = values.get("sync_requested_at")
        if request and request != self.request_seen:
            self.next_due = self.next_heartbeat = now
        self.request_seen = request
        enabled = values.get("automatic_sync") != "0"
        cloud = json.loads(values.get("connectivity_cloud", "{}")).get("state", "Checking…")
        internet = json.loads(values.get("connectivity_internet", "{}")).get("state", "Checking…")

        # When cloud comes Online OR internet returns Available after being unavailable: trigger sync immediately
        if (((cloud == "Online" and self.previous_cloud != "Online")
                or (internet == "Available" and self.previous_internet not in {"Available", None}))
                or (enabled and self.enabled is False)):
            self.next_due = now
        self.previous_cloud, self.previous_internet, self.enabled = cloud, internet, enabled

        heartbeat = now >= self.next_heartbeat
        refresh = enabled and now >= self.next_due
        if not heartbeat and not refresh:
            return
        try:
            self.cycle(self.config, heartbeat=heartbeat, refresh=refresh)
            values = read_scheduler_state(self.config.database_path)
            cloud = json.loads(values.get("connectivity_cloud", "{}")).get("state", "Checking…")
            # HTTP reachability alone does not establish reconciliation success.
            success = cloud == "Online" and (not refresh or values.get(
                "connectivity_sync", "Up to date") == "Up to date")
        except Exception as error:
            LOGGER.warning("Automatic sync unavailable kind=%s", type(error).__name__)
            success = False
        self.failures = 0 if success else min(self.failures + 1, 5)
        interval = min(300, self.config.sync_interval_seconds * (2 ** max(0, self.failures - 1)))
        if refresh:
            self.next_due = self.clock() + interval + self.jitter()
        elif success and enabled and self.previous_cloud != "Online":
            self.next_due = self.clock()
        if heartbeat:
            self.next_heartbeat = self.clock() + (min(self.config.heartbeat_interval_seconds, 60)
                                                   if success else max(60, interval))
        self.previous_cloud = cloud
        self.previous_internet = json.loads(read_scheduler_state(
            self.config.database_path).get("connectivity_internet", "{}")).get("state", "Checking…")
        value = (datetime.now(UTC) + timedelta(
            seconds=max(0, self.next_due - self.clock()))).isoformat() if enabled else ""
        set_next_sync(self.config.database_path, value)

    def run(self, stop=None):
        stop = stop or self.stop
        with file_lock(str(self.config.database_path) + ".scheduler.lock", blocking=False) as owner:
            if not owner:
                return
            while not stop.is_set():
                try:
                    self.tick()
                except Exception as error:
                    LOGGER.warning("Scheduler recovery kind=%s", type(error).__name__)
                stop.wait(2)  # Local wake-up check only, never a two-second cloud poll.

    def start(self):
        self.thread = threading.Thread(target=self.run, name="automatic-sync", daemon=True)
        self.thread.start()

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=2)
