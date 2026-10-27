"""Optional named fault hooks used only by deterministic development tests."""

from collections.abc import Callable
from typing import TypeAlias

FaultHook: TypeAlias = Callable[[str], None]


def no_fault(_point: str) -> None:
    """Production default: named fault points have zero behavior."""
