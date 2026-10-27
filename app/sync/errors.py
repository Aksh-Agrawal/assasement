"""Small, actionable error taxonomy for attempt synchronization."""


class SyncError(RuntimeError):
    """Base class for expected synchronization failures."""


class TransientSyncError(SyncError):
    """A network or server condition that can be retried later."""


class PermanentSyncError(SyncError):
    """A request the server rejected and should not be retried automatically."""


class AuthenticationError(SyncError):
    """Authentication or authorization must be repaired before another upload."""


class PairingRequired(AuthenticationError):
    """No local credential exists; pairing is required before synchronization."""


class AlreadySynced(SyncError):
    """The server proved that this exact attempt UUID was already accepted."""
