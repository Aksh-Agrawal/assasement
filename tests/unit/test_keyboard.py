"""Laptop-safe tests for canonical keyboard input translation."""

import pytest

from app.input.actions import Action
from app.input.keyboard import KeyboardInput


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("a", Action.SELECT_A),
        ("A", Action.SELECT_A),
        ("1", Action.SELECT_A),
        ("b", Action.SELECT_B),
        ("B", Action.SELECT_B),
        ("2", Action.SELECT_B),
        ("c", Action.SELECT_C),
        ("C", Action.SELECT_C),
        ("3", Action.SELECT_C),
        ("d", Action.SELECT_D),
        ("D", Action.SELECT_D),
        ("4", Action.SELECT_D),
        ("left", Action.PREV),
        ("LEFT", Action.PREV),
        ("right", Action.NEXT),
        ("RIGHT", Action.NEXT),
        ("enter", Action.CONFIRM),
        ("ENTER", Action.CONFIRM),
        ("escape", Action.BACK),
        ("ESCAPE", Action.BACK),
        ("s", Action.SURE),
        ("S", Action.SURE),
        ("n", Action.NOT_SURE),
        ("N", Action.NOT_SURE),
        ("g", Action.GUESSING),
        ("G", Action.GUESSING),
        ("r", Action.MARK_REVIEW),
        ("R", Action.MARK_REVIEW),
        ("t", Action.SUBMIT),
        ("T", Action.SUBMIT),
        ("m", Action.MENU),
        ("M", Action.MENU),
        ("  left  ", Action.PREV),
    ],
)
def test_keyboard_mapping(key: str, expected: Action) -> None:
    assert KeyboardInput().translate(key) is expected


@pytest.mark.parametrize("key", ["", "   ", "unknown", "q", "5"])
def test_unknown_or_empty_keyboard_input_is_ignored(key: str) -> None:
    assert KeyboardInput().translate(key) is None
