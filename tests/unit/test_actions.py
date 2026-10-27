"""Contract tests for canonical input actions."""

from app.input.actions import Action

EXPECTED_ACTION_VALUES = (
    "SELECT_A",
    "SELECT_B",
    "SELECT_C",
    "SELECT_D",
    "NEXT",
    "PREV",
    "CONFIRM",
    "MENU",
    "BACK",
    "SURE",
    "NOT_SURE",
    "GUESSING",
    "MARK_REVIEW",
    "SUBMIT",
)


def test_all_phase_zero_actions_exist_with_stable_values() -> None:
    assert tuple(action.name for action in Action) == EXPECTED_ACTION_VALUES
    assert tuple(action.value for action in Action) == EXPECTED_ACTION_VALUES


def test_action_values_have_no_duplicates() -> None:
    values = [action.value for action in Action]

    assert len(Action.__members__) == len(Action)
    assert len(values) == len(set(values))

