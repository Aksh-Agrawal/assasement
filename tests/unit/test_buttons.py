"""Laptop-safe contract tests for the planned GPIO button adapter."""

import builtins

import pytest

from app.input.actions import Action
from app.input.buttons import (
    BOUNCE_SECONDS,
    BUTTON_PINS,
    ButtonControl,
    ButtonHardwareUnavailable,
    ButtonInput,
)


def test_bcm_plan_and_default_actions_are_stable() -> None:
    assert BUTTON_PINS == {
        ButtonControl.A: 5,
        ButtonControl.B: 6,
        ButtonControl.C: 13,
        ButtonControl.D: 19,
        ButtonControl.PREV: 26,
        ButtonControl.NEXT: 20,
        ButtonControl.MENU: 21,
    }
    assert BOUNCE_SECONDS == 0.04
    adapter = ButtonInput(lambda _action: None)
    assert adapter.action_for(ButtonControl.A) is Action.SELECT_A
    assert adapter.action_for(ButtonControl.NEXT) is Action.NEXT
    assert adapter.action_for(ButtonControl.MENU) is Action.MENU


def test_context_resolver_can_map_shared_controls_without_gpio() -> None:
    adapter = ButtonInput(
        lambda _action: None,
        resolve=lambda control: (
            Action.CONFIRM if control is ButtonControl.NEXT else Action.BACK
        ),
    )
    assert adapter.action_for(ButtonControl.NEXT) is Action.CONFIRM
    assert adapter.action_for(ButtonControl.MENU) is Action.BACK


def test_gpiozero_is_loaded_only_when_hardware_start_is_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import = builtins.__import__

    def reject_gpiozero(name: str, *args: object, **kwargs: object) -> object:
        if name == "gpiozero":
            raise ImportError("simulated laptop")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_gpiozero)
    adapter = ButtonInput(lambda _action: None)
    with pytest.raises(ButtonHardwareUnavailable, match="configured Raspberry Pi"):
        adapter.start()
