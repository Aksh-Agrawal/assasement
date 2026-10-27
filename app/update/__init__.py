"""Signed application-update verification, staging, and simulated activation."""

from app.update.errors import UpdateError
from app.update.manifest import UpdateManifest

__all__ = ["UpdateError", "UpdateManifest"]
