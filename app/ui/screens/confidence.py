"""Confidence choice shown after durable answer selection."""

import pygame

from app.input.actions import Action
from app.ui.components import (
    header,
)
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, text, title
from app.ui.theme import THEME


def _legacy_render(
    surface: pygame.Surface, controller: UIController, fonts: Fonts
) -> list[Control]:
    controls: list[Control] = []
    title(surface, "How confident are you?", fonts)
    response = controller.application.current_response()
    paragraph(
        surface,
        f"Answer {response.selected_key if response else '-'} is already saved.",
        Rect(24, 65, 752, 40),
        fonts.body,
    )
    button(surface, controls, Rect(80, 135, 280, 68), "Sure", Action.SURE, fonts, state="primary")
    button(surface, controls, Rect(440, 135, 280, 68), "? Not Sure", Action.NOT_SURE, fonts)
    button(surface, controls, Rect(80, 235, 280, 68), "~ Guessing", Action.GUESSING, fonts)
    button(
        surface,
        controls,
        Rect(440, 235, 280, 68),
        "Skip confidence",
        Action.CONFIRM,
        fonts,
        state="selected",
    )
    paragraph(
        surface,
        "Escape also continues with confidence stored as unrated.",
        Rect(180, 350, 500, 30),
        fonts.small,
        color=THEME.muted,
    )
    return controls


def render(surface, c, fonts):
    if not c.student_flow:
        return _legacy_render(surface, c, fonts)
    controls = []
    header(surface, controls, "HOW CONFIDENT ARE YOU?", c, fonts)
    response, q = c.application.current_response(), c.application.current_question()
    selected = next((o for o in q.options if response and o.key == response.selected_key), None)
    value = (
        f"Your answer: {selected.key} - {selected.text}"
        if selected
        else "Your answer is saved locally."
    )
    paragraph(surface, value, Rect(24, 82, 752, 74), fonts.body, max_lines=3)
    for i, (label, action) in enumerate(
        (("SURE", Action.SURE), ("NOT SURE", Action.NOT_SURE), ("GUESSING", Action.GUESSING))
    ):
        button(surface, controls, Rect(24 + i * 256, 192, 240, 80), label, action, fonts)
    text(surface, "Your answer is already saved locally.", (24, 310), fonts.body, color=THEME.muted)
    button(surface, controls, Rect(24, 366, 280, 48), "Back to options", Action.BACK, fonts)
    button(surface, controls, Rect(496, 366, 280, 48), "Continue unrated", Action.CONFIRM, fonts)
    return controls
