"""Deterministic retry-policy tests."""

import pytest

from app.sync.policy import SyncPolicy, next_retry_delay


def test_default_backoff_is_bounded_and_deterministic() -> None:
    assert [next_retry_delay(number) for number in range(1, 7)] == [5, 15, 45, 135, 300, 300]


def test_policy_rejects_invalid_attempt_number() -> None:
    with pytest.raises(ValueError, match="positive"):
        SyncPolicy().next_retry_delay(0)
