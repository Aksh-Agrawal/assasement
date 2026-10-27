"""Hardware-independent keyboard translation into canonical logical actions."""

from app.input.actions import Action

KEY_ACTIONS: dict[str, Action] = {
    "a": Action.SELECT_A,
    "1": Action.SELECT_A,
    "b": Action.SELECT_B,
    "2": Action.SELECT_B,
    "c": Action.SELECT_C,
    "3": Action.SELECT_C,
    "d": Action.SELECT_D,
    "4": Action.SELECT_D,
    "left": Action.PREV,
    "arrowleft": Action.PREV,
    "right": Action.NEXT,
    "arrowright": Action.NEXT,
    "enter": Action.CONFIRM,
    "return": Action.CONFIRM,
    "escape": Action.BACK,
    "esc": Action.BACK,
    "s": Action.SURE,
    "n": Action.NOT_SURE,
    "g": Action.GUESSING,
    "r": Action.MARK_REVIEW,
    "t": Action.SUBMIT,
    "m": Action.MENU,
}


class KeyboardInput:
    """Translate key names only; assessment context remains outside the adapter."""

    def translate(self, key: str) -> Action | None:
        """Return a canonical action, or None for empty/unknown input."""
        return KEY_ACTIONS.get(key.strip().casefold())
