"""Assessment instructions sourced from the selected local pack."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, text, top_bar
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    selected = controller.selected_question_set
    top_bar(surface, controls, "Assessment instructions", fonts, network=controller.network_label)
    if selected is None:
        return controls
    text(surface, selected.title, (48, 78), fonts.heading)
    paragraph(
        surface,
        selected.chapter,
        Rect(48, 112, 700, 38),
        fonts.body,
        color=THEME.muted,
        max_lines=1,
    )
    text(surface, f"{len(selected.questions)} questions", (48, 165), fonts.body)
    text(surface, f"About {len(selected.questions)} minutes", (300, 165), fonts.body)
    text(surface, "Single correct answer", (520, 165), fonts.body)
    text(surface, "Marking", (48, 225), fonts.heading)
    marking = selected.marking
    text(surface, f"+{marking.correct}  Correct", (48, 270), fonts.body, color=THEME.success)
    text(surface, f"{marking.wrong}  Incorrect", (265, 270), fonts.body, color=THEME.danger)
    text(surface, f"{marking.skip}  Skipped", (500, 270), fonts.body)
    paragraph(
        surface,
        "After each answer, choose Sure, Not Sure, or Guessing.",
        Rect(48, 320, 700, 35),
        fonts.body,
        color=THEME.muted,
    )
    label = "Resume Assessment" if controller.can_resume else "Start Assessment"
    button(
        surface, controls, Rect(480, 388, 280, 64), label, Action.CONFIRM, fonts, state="primary"
    )
    return controls
