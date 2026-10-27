"""Platform-independent logical input actions."""

from enum import StrEnum


class Action(StrEnum):
    """Stable action names shared by touch and future physical inputs."""

    SELECT_A = "SELECT_A"
    SELECT_B = "SELECT_B"
    SELECT_C = "SELECT_C"
    SELECT_D = "SELECT_D"

    NEXT = "NEXT"
    PREV = "PREV"
    CONFIRM = "CONFIRM"

    MENU = "MENU"
    BACK = "BACK"

    SURE = "SURE"
    NOT_SURE = "NOT_SURE"
    GUESSING = "GUESSING"

    MARK_REVIEW = "MARK_REVIEW"

    SUBMIT = "SUBMIT"

