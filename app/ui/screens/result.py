"""Final ScoreResult presentation without UI-side recalculation."""

import pygame

from app.core.models import Confidence
from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, text, title
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    result = controller.result
    title(surface, "Assessment result", fonts)
    if result is None:
        text(surface, "No result is available.", (30, 80), fonts.body)
        return controls
    text(surface, f"Score: {result.score}", (40, 65), fonts.result, color=THEME.accent)
    text(surface, f"Correct: {result.correct}", (40, 115), fonts.body)
    text(surface, f"Wrong: {result.wrong}", (220, 115), fonts.body)
    text(surface, f"Skipped: {result.skipped}", (390, 115), fonts.body)
    text(surface, f"Attempted: {result.attempted}", (570, 115), fonts.body)
    text(surface, f"Accuracy: {result.accuracy:.1%}", (40, 155), fonts.body)
    text(surface, "Confidence responses", (40, 210), fonts.body)
    labels = {
        Confidence.SURE: "Sure",
        Confidence.NOT_SURE: "Not Sure",
        Confidence.GUESSING: "Guessing",
        Confidence.UNRATED: "Unrated",
    }
    for index, confidence in enumerate(Confidence):
        text(
            surface,
            f"{labels[confidence]}: {result.confidence_totals[confidence]}",
            (50 + (index % 2) * 250, 250 + (index // 2) * 35),
            fonts.option,
        )
    text(
        surface,
        f"Sure but wrong: {len(result.sure_but_wrong_question_ids)}    "
        f"Guessed right: {len(result.guessed_right_question_ids)}",
        (40, 330),
        fonts.body,
    )
    button(surface, controls, Rect(100, 395, 260, 55), "Return Home", Action.BACK, fonts)
    button(surface, controls, Rect(440, 395, 260, 55), "Review answers", Action.CONFIRM, fonts)
    return controls
