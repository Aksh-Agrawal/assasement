"""Final ScoreResult presentation without UI-side recalculation."""

import pygame

from app.core.models import Confidence
from app.input.actions import Action
from app.ui.components import (
    choice_button,
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
    result = controller.result
    title(surface, "Assessment complete", fonts)
    if result is None:
        text(surface, "No result is available.", (30, 80), fonts.body)
        return controls
    question_set = controller.application.engine.question_set
    maximum = len(question_set.questions) * question_set.marking.correct if question_set else "-"
    text(surface, f"{result.score} / {maximum}", (40, 65), fonts.result, color=THEME.accent)
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
    if controller.network_label == "Offline":
        text(
            surface,
            "Saved on this device - will sync when online",
            (40, 360),
            fonts.small,
            color=THEME.warning,
        )
    button(surface, controls, Rect(100, 395, 260, 55), "Return Home", Action.BACK, fonts)
    button(surface, controls, Rect(440, 395, 260, 55), "Review answers", Action.CONFIRM, fonts)
    return controls


def render(surface, c, fonts):
    if not c.student_flow:
        return _legacy_render(surface, c, fonts)
    controls = []
    header(surface, controls, "TEST COMPLETE", c, fonts)
    r, qs = c.result, c.application.engine.question_set
    if r is None or qs is None:
        text(surface, "No result available.", (24, 100), fonts.body)
        return controls
    paragraph(surface, f"{qs.subject} / {qs.title}", Rect(24, 70, 752, 30), fonts.body, max_lines=1)
    text(
        surface,
        f"{r.score:g} / {len(qs.questions) * qs.marking.correct:g}",
        (24, 110),
        fonts.result,
        color=THEME.accent,
    )
    elapsed = sum(item.response_time_ms for item in c.application.engine.responses()) // 1000
    text(
        surface,
        f"Accuracy {r.accuracy:.0%}   |   Time {elapsed // 60}m {elapsed % 60:02}s",
        (350, 126),
        fonts.body,
    )
    text(
        surface,
        f"Correct {r.correct}      Wrong {r.wrong}      Skipped {r.skipped}",
        (24, 166),
        fonts.body,
    )
    text(
        surface,
        "CONFIDENCE                  Correct       Wrong",
        (24, 210),
        fonts.small,
        color=THEME.muted,
    )
    for i, confidence_value in enumerate(Confidence):
        text(
            surface,
            confidence_value.value.replace("_", " ").title(),
            (24, 236 + i * 29),
            fonts.body,
        )
        text(surface, str(r.confidence_correct[confidence_value]), (258, 236 + i * 29), fonts.body)
        text(surface, str(r.confidence_wrong[confidence_value]), (366, 236 + i * 29), fonts.body)
    for i in range(len(c.choices)):
        choice_button(
            surface, controls, c, fonts, i, Rect(446 + i % 2 * 170, 204 + i // 2 * 68, 160, 64)
        )
    sync = c.repository.get_attempt_sync_state(c.application.engine.attempt.id).status.value
    text(surface, f"Saved locally | Sync: {sync}", (24, 382), fonts.small, color=THEME.muted)
    return controls
