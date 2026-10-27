"""Deterministic bounded retry policy; it never sleeps."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SyncPolicy:
    """Configuration for one-shot batching, retries, and stale recovery."""

    batch_size: int = 10
    max_automatic_retries: int = 5
    initial_retry_seconds: int = 5
    retry_multiplier: int = 3
    maximum_retry_seconds: int = 300
    stale_syncing_seconds: int = 300

    def __post_init__(self) -> None:
        values = (
            self.batch_size,
            self.max_automatic_retries,
            self.initial_retry_seconds,
            self.retry_multiplier,
            self.maximum_retry_seconds,
            self.stale_syncing_seconds,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            raise ValueError("Sync policy values must be integers")
        if self.batch_size < 1 or self.max_automatic_retries < 1:
            raise ValueError("Batch size and maximum retries must be positive")
        if self.initial_retry_seconds < 1 or self.retry_multiplier < 1:
            raise ValueError("Retry delay and multiplier must be positive")
        if self.maximum_retry_seconds < self.initial_retry_seconds:
            raise ValueError("Maximum retry delay must not be below the initial delay")
        if self.stale_syncing_seconds < 0:
            raise ValueError("Stale syncing threshold must not be negative")

    def next_retry_delay(self, attempt_number: int) -> int:
        """Return bounded exponential delay after a one-based failed attempt."""
        if attempt_number < 1:
            raise ValueError("Attempt number must be positive")
        delay = self.initial_retry_seconds * self.retry_multiplier ** (attempt_number - 1)
        return min(delay, self.maximum_retry_seconds)


def next_retry_delay(attempt_number: int) -> int:
    """Return the default deterministic retry delay for a one-based failure count."""
    return SyncPolicy().next_retry_delay(attempt_number)
