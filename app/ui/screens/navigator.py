"""Compact question status navigator."""

import pygame

from app.input.actions import Action
from app.ui.components import (
    header,
)
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, text, top_bar
from app.ui.theme import THEME


def _legacy_render(
    surface: pygame.Surface, controller: UIController, fonts: Fonts
) -> list[Control]:
    controls: list[Control] = []
    top_bar(surface, controls, "Questions", fonts)
    responses = {r.question_id: r for r in controller.application.engine.responses()}
    ids = controller.application.engine.ordered_question_ids
    for index, question_id in enumerate(ids):
        col, row = index % 10, index // 10
        x, y = 35 + col * 73, 85 + row * 62
        response = responses.get(question_id)
        color = THEME.surface
        if response and response.selected_key:
            color = THEME.correct
        if response and response.marked_review:
            color = THEME.review
        if index == controller.navigator_index:
            color = THEME.selected
        rect = pygame.Rect(x, y, 52, 48)
        pygame.draw.rect(surface, color, rect, border_radius=8)
        pygame.draw.rect(
            surface,
            THEME.accent if index == controller.navigator_index else THEME.border,
            rect,
            3 if index == controller.navigator_index else 1,
            border_radius=8,
        )
        label = fonts.button.render(str(index + 1), True, THEME.foreground)
        surface.blit(label, (x + 26 - label.get_width() // 2, y + 24 - label.get_height() // 2))
    text(
        surface,
        "Green answered  |  Yellow marked  |  Blue current",
        (35, 345),
        fonts.small,
        color=THEME.muted,
    )
    button(
        surface,
        controls,
        Rect(200, 400, 120, 52),
        "< Previous",
        Action.PREV,
        fonts,
        enabled=controller.navigator_index > 0,
    )
    button(
        surface, controls, Rect(340, 400, 120, 52), "Open", Action.CONFIRM, fonts, state="primary"
    )
    button(
        surface,
        controls,
        Rect(480, 400, 120, 52),
        "Next >",
        Action.NEXT,
        fonts,
        enabled=controller.navigator_index < len(ids) - 1,
    )
    return controls


def render(surface, c, fonts):
    if not c.student_flow:
        return _legacy_render(surface, c, fonts)
    controls = []
    header(surface, controls, "QUESTION NAVIGATOR", c, fonts)
    ids = c.application.engine.ordered_question_ids
    responses = {r.question_id: r for r in c.application.engine.responses()}
    first = c.navigator_index // 40 * 40
    for i in range(first, min(first + 40, len(ids))):
        row, col = divmod(i - first, 10)
        response = responses.get(ids[i])
        state = (
            "*"
            if response and response.marked_review
            else "+"
            if response and response.selected_key
            else "-"
        )
        label = f"{i + 1}{state}" + (">" if i == c.application.engine.current_index else "")
        button(
            surface,
            controls,
            Rect(24 + col * 76, 94 + row * 62, 68, 54),
            label,
            Action.CONFIRM,
            fonts,
            state="focus"
            if i == c.navigator_index
            else "review"
            if state == "*"
            else "selected"
            if state == "+"
            else "normal",
            payload=("question", i),
        )
    text(
        surface,
        "+ Answered    - Unanswered    * Review    > Current",
        (24, 344),
        fonts.small,
        color=THEME.muted,
    )
    button(surface, controls, Rect(24, 366, 216, 48), "< Choose", Action.PREV, fonts)
    button(
        surface,
        controls,
        Rect(288, 366, 216, 48),
        "Open selected",
        Action.CONFIRM,
        fonts,
        state="primary",
    )
    button(surface, controls, Rect(560, 366, 216, 48), "Choose >", Action.NEXT, fonts)
    return controls
