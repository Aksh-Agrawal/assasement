from dataclasses import replace

from app.config import AppConfig
from app.connectivity import record_cloud
from app.data.repo import Repository
from app.sync.locking import file_lock
from app.sync.scheduler import AutoSyncScheduler


def test_scheduler_window_backoff_reconnect_toggle_and_heartbeat(tmp_path):
    config = AppConfig(database_path=tmp_path / "pi.db", api_base_url="https://cloud.test")
    now = [0.0]
    calls = []
    state = ["Online"]
    def cycle(config, **kwargs):
        calls.append(kwargs)
        record_cloud(config.database_path, state[0])
    scheduler = AutoSyncScheduler(config, cycle=cycle, clock=lambda: now[0], jitter=lambda: 0)
    scheduler.tick()
    assert calls == [{"heartbeat": True, "refresh": True}]
    now[0] = 24
    scheduler.tick()
    assert len(calls) == 1
    now[0] = 25
    state[0] = "Offline"
    scheduler.tick()
    assert scheduler.next_due == 50
    now[0] = 50
    scheduler.tick()
    assert scheduler.next_due == 100
    now[0] = 51
    record_cloud(config.database_path, "Online")
    state[0] = "Online"
    scheduler.tick()
    assert scheduler.failures == 0 and scheduler.next_due == 76
    with Repository(config.database_path) as repo:
        repo.set_setting("automatic_sync", "0")
    now[0] = 80
    scheduler.tick()
    assert calls[-1] == {"heartbeat": True, "refresh": False}
    count = len(calls)
    now[0] = 100
    scheduler.tick()
    assert len(calls) == count
    with Repository(config.database_path) as repo:
        repo.set_setting("automatic_sync", "1")
    scheduler.tick()
    assert calls[-1]["refresh"]


def test_single_scheduler_and_cycle_os_lock(tmp_path):
    path = tmp_path / "sync.lock"
    with file_lock(path) as acquired:
        assert acquired
        with file_lock(path, blocking=False) as second:
            assert not second
    with file_lock(path, blocking=False) as acquired:
        assert acquired


def test_backoff_is_bounded_and_restart_is_immediate(tmp_path):
    config = AppConfig(database_path=tmp_path / "pi.db", api_base_url="https://cloud.test")
    now = [0.0]
    scheduler = AutoSyncScheduler(config, cycle=lambda config, **kwargs: record_cloud(config.database_path, "Offline"),
                                  clock=lambda: now[0], jitter=lambda: 0)
    for _ in range(9):
        scheduler.tick()
        assert scheduler.next_due - now[0] <= 300
        now[0] = scheduler.next_due
    restarted = AutoSyncScheduler(replace(config), cycle=lambda *a, **k: None)
    assert restarted.next_due == 0


def test_network_or_account_wakeup_bypasses_long_backoff(tmp_path):
    config = AppConfig(database_path=tmp_path / "pi.db", api_base_url="https://cloud.test")
    now = [0.0]
    calls = []
    def cycle(config, **kwargs):
        calls.append(kwargs)
        record_cloud(config.database_path, "Offline")
    scheduler = AutoSyncScheduler(config, cycle=cycle, clock=lambda: now[0], jitter=lambda: 0)
    scheduler.tick()
    scheduler.next_due = scheduler.next_heartbeat = 300
    now[0] = 2
    with Repository(config.database_path) as repo:
        repo.set_setting("sync_requested_at", "network-restored")
    scheduler.tick()
    assert len(calls) == 2
    assert calls[-1] == {"heartbeat": True, "refresh": True}


def test_partial_reconciliation_backs_off_even_when_cloud_is_online(tmp_path):
    config = AppConfig(database_path=tmp_path / "pi.db", api_base_url="https://cloud.test")
    now = [0.0]
    state = ["Partially synced"]
    def cycle(config, **kwargs):
        record_cloud(config.database_path, "Online")
        with Repository(config.database_path) as repo:
            repo.set_setting("connectivity_sync", state[0])
    scheduler = AutoSyncScheduler(config, cycle=cycle, clock=lambda: now[0], jitter=lambda: 0)
    scheduler.tick()
    now[0] = scheduler.next_due
    scheduler.tick()
    assert scheduler.failures == 2 and scheduler.next_due - now[0] == 50
    state[0] = "Up to date"
    now[0] = scheduler.next_due
    scheduler.tick()
    assert scheduler.failures == 0 and scheduler.next_due - now[0] == 25
