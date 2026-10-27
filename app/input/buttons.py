"""Planned seven-button GPIO adapter with laptop-safe lazy hardware loading."""

from collections.abc import Callable
from enum import StrEnum
from typing import Any

from app.input.actions import Action

BOUNCE_SECONDS = 0.04


class ButtonControl(StrEnum):
    """Physical labels; these are not a second logical Action enum."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    PREV = "PREV"
    NEXT = "NEXT"
    MENU = "MENU"


BUTTON_PINS: dict[ButtonControl, int] = {
    ButtonControl.A: 5,
    ButtonControl.B: 6,
    ButtonControl.C: 13,
    ButtonControl.D: 19,
    ButtonControl.PREV: 26,
    ButtonControl.NEXT: 20,
    ButtonControl.MENU: 21,
}

DEFAULT_BUTTON_ACTIONS: dict[ButtonControl, Action] = {
    ButtonControl.A: Action.SELECT_A,
    ButtonControl.B: Action.SELECT_B,
    ButtonControl.C: Action.SELECT_C,
    ButtonControl.D: Action.SELECT_D,
    ButtonControl.PREV: Action.PREV,
    ButtonControl.NEXT: Action.NEXT,
    ButtonControl.MENU: Action.MENU,
}


class ButtonHardwareUnavailable(RuntimeError):
    """Raised when GPIO construction is attempted without usable gpiozero."""


class ButtonInput:
    """Emit Actions for active-low, pull-up BCM buttons when started on a Pi.

    ``resolve`` is the future screen-context boundary for shared NEXT/CONFIRM and
    MENU/BACK controls. The default mapping contains no assessment business logic.
    """

    def __init__(
        self,
        emit: Callable[[Action], None],
        *,
        resolve: Callable[[ButtonControl], Action] | None = None,
    ) -> None:
        self._emit = emit
        self._resolve = resolve or DEFAULT_BUTTON_ACTIONS.__getitem__
        self._buttons: list[Any] = []

    def action_for(self, control: ButtonControl) -> Action:
        return self._resolve(control)

    def start(self) -> None:
        """Construct gpiozero buttons lazily; safe modules import on laptops."""
        if self._buttons:
            return
        try:
            from gpiozero import Button
        except (ImportError, OSError) as error:
            raise ButtonHardwareUnavailable(
                "gpiozero is unavailable; run this adapter on a configured Raspberry Pi"
            ) from error

        try:
            for control, pin in BUTTON_PINS.items():
                button = Button(pin, pull_up=True, bounce_time=BOUNCE_SECONDS)
                button.when_pressed = self._callback(control)
                self._buttons.append(button)
        except Exception as error:
            self.close()
            raise ButtonHardwareUnavailable(
                f"Could not initialize Raspberry Pi GPIO buttons: {error}"
            ) from error

    def _callback(self, control: ButtonControl) -> Callable[[], None]:
        def emit_action() -> None:
            self._emit(self.action_for(control))

        return emit_action

    def close(self) -> None:
        """Release any constructed gpiozero devices."""
        for button in self._buttons:
            button.close()
        self._buttons.clear()

    def __enter__(self) -> "ButtonInput":
        self.start()
        return self

    def __exit__(self, *_exc_info: object) -> None:
        self.close()
