"""Explicit submit confirmation view."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, text, title
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    answered, unanswered, marked = controller.submit_counts
    title(surface, "Submit assessment?", fonts)
    total = answered + unanswered
    text(surface, f"Total questions: {total}", (120, 90), fonts.body)
    text(surface, f"Answered: {answered}", (120, 130), fonts.body)
    text(surface, f"Unanswered: {unanswered}", (120, 170), fonts.body)
    text(surface, f"Marked for review: {marked}", (120, 210), fonts.body)
    if unanswered:
        text(
            surface,
            f"{unanswered} unanswered question{'s' if unanswered != 1 else ''} will count as skipped.",
            (120, 255),
            fonts.option,
            color=THEME.danger,
        )
    button(
        surface,
        controls,
        Rect(100, 320, 270, 70),
        "Continue Assessment",
        Action.BACK,
        fonts,
    )
    button(
        surface,
        controls,
        Rect(430, 320, 270, 70),
        "Submit Assessment",
        Action.SUBMIT,
        fonts,
        state="danger",
    )
    return controls
