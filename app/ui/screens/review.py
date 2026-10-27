"""Read-only completed answer review view."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, text
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    item = controller.review_items[controller.review_index]
    response = item.response
    outcome_color = {
        "correct": THEME.correct,
        "wrong": THEME.wrong,
        "skipped": THEME.disabled,
    }[item.outcome]
    pygame.draw.rect(surface, outcome_color, pygame.Rect(8, 4, 784, 40), border_radius=6)
    text(
        surface,
        f"Review {controller.review_index + 1}/{len(controller.review_items)} — "
        f"{item.outcome.upper()}",
        (16, 10),
        fonts.heading,
        color=THEME.accent,
    )
    paragraph(surface, item.question.question_text, Rect(16, 52, 768, 80), fonts.body, max_lines=4)
    selected = response.selected_key if response and response.selected_key else "Skipped"
    confidence = response.confidence.value if response and response.confidence else "—"
    text(surface, f"Selected: {selected}", (24, 145), fonts.body)
    text(surface, f"Correct: {item.question.correct_key}", (250, 145), fonts.body)
    text(surface, f"Confidence: {confidence}", (450, 145), fonts.body)
    text(
        surface,
        f"Response time: {response.response_time_ms if response else 0} ms",
        (24, 185),
        fonts.small,
    )
    text(
        surface,
        f"Review flag: {'yes' if response and response.marked_review else 'no'}",
        (280, 185),
        fonts.small,
    )
    paragraph(
        surface,
        "Explanation: " + (item.question.explanation or "No explanation provided."),
        Rect(24, 225, 752, 115),
        fonts.option,
        max_lines=6,
    )
    button(
        surface,
        controls,
        Rect(16, 395, 130, 55),
        "Previous",
        Action.PREV,
        fonts,
        enabled=controller.review_index > 0,
    )
    button(surface, controls, Rect(176, 395, 130, 55), "Full text", Action.CONFIRM, fonts)
    button(surface, controls, Rect(494, 395, 130, 55), "Exit Review", Action.BACK, fonts)
    button(
        surface,
        controls,
        Rect(654, 395, 130, 55),
        "Next",
        Action.NEXT,
        fonts,
        enabled=controller.review_index < len(controller.review_items) - 1,
    )
    return controls
