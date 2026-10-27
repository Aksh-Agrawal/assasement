"""Unit tests for monotonic response timing."""

import pytest

from app.core.timer import MonotonicTimer


class FakeClock:
    def __init__(self, value: float) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def test_timer_pauses_resumes_and_accumulates_revisits() -> None:
    clock = FakeClock(10)
    timer = MonotonicTimer(clock=clock)

    timer.start()
    clock.value = 15
    assert timer.pause() == 5_000
    assert timer.running is False

    clock.value = 20  # Five seconds of downtime must not count.
    timer.start()
    clock.value = 23
    assert timer.pause() == 8_000
    assert timer.elapsed_ms == 8_000


def test_timer_initial_value_and_repeated_calls_do_not_double_count() -> None:
    clock = FakeClock(4)
    timer = MonotonicTimer(initial_ms=1_250, clock=clock)

    timer.start()
    timer.start()
    clock.value = 5.5
    assert timer.elapsed_ms == 2_750
    assert timer.pause() == 2_750
    assert timer.pause() == 2_750


def test_timer_rejects_negative_initial_value_and_backwards_clock() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        MonotonicTimer(initial_ms=-1)

    clock = FakeClock(10)
    timer = MonotonicTimer(clock=clock)
    timer.start()
    clock.value = 9
    with pytest.raises(RuntimeError, match="moved backwards"):
        timer.pause()
