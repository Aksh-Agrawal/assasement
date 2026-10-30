"""Small scheduler settings reads/writes without full repository validation."""
import sqlite3
from datetime import UTC, datetime


def read_scheduler_state(path):
    with sqlite3.connect(path, timeout=5) as connection:
        return dict(connection.execute("SELECT key,value FROM settings WHERE key IN "
                    "('automatic_sync','connectivity_cloud','connectivity_internet',"
                    "'connectivity_sync','sync_requested_at')"))


def _write(path, key, value):
    with sqlite3.connect(path, timeout=5) as connection:
        connection.execute("INSERT INTO settings(key,value) VALUES(?,?) "
                           "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def request_sync(path):
    _write(path, "sync_requested_at", datetime.now(UTC).isoformat())


def set_next_sync(path, value):
    _write(path, "next_automatic_sync", value)
