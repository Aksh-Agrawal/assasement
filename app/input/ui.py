"""Input messages for keyboard, touch and GPIO at the UI boundary."""

from dataclasses import dataclass

from app.input.actions import Action
from app.input.keyboard import KeyboardInput


@dataclass(frozen=True)
class UIInput:
    action: Action
    payload: object = None


def keyboard_input(key, *, character="", text_entry=False):
    """Text-entry keys produce the same messages as the on-screen keyboard."""
    if text_entry:
        if key == "backspace":
            return UIInput(Action.CONFIRM, ("command", "delete"))
        if key in {"return", "enter"}:
            return UIInput(Action.CONFIRM, ("command", "text_submit"))
        if character and character.isprintable():
            return UIInput(Action.CONFIRM, ("text", character))
    action = KeyboardInput().translate(key)
    return UIInput(action) if action else None
