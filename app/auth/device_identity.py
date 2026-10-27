"""Stable privacy-preserving device identity."""

from app.data.repo import Repository


def get_or_create_device_id(repository: Repository) -> str:
    """Return the UUIDv4 stored in the device database across restarts."""
    return repository.get_or_create_device_id()
