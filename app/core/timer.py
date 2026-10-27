"""Injectable monotonic response timer with revisit accumulation."""

import time
from collections.abc import Callable


class MonotonicTimer:
    """Accumulate active elapsed time without using the wall clock."""

    def __init__(
        self,
        *,
        initial_ms: int = 0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if initial_ms < 0:
            raise ValueError("Initial timer value must not be negative")
        self._clock = clock
        self._accumulated_seconds = initial_ms / 1000
        self._started_at: float | None = None

    @property
    def running(self) -> bool:
        """Whether an active timing segment is currently open."""
        return self._started_at is not None

    @property
    def elapsed_ms(self) -> int:
        """Return accumulated time including the current active segment."""
        seconds = self._accumulated_seconds
        if self._started_at is not None:
            now = self._clock()
            if now < self._started_at:
                raise RuntimeError("Monotonic clock moved backwards")
            seconds += now - self._started_at
        return round(seconds * 1000)

    def start(self) -> None:
        """Start or resume timing; repeated starts do not double-count."""
        if self._started_at is None:
            self._started_at = self._clock()

    def pause(self) -> int:
        """Close the active segment and return total accumulated milliseconds."""
        if self._started_at is not None:
            now = self._clock()
            if now < self._started_at:
                raise RuntimeError("Monotonic clock moved backwards")
            self._accumulated_seconds += now - self._started_at
            self._started_at = None
        return round(self._accumulated_seconds * 1000)

