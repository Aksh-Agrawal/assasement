"""Read-only completed answer review view."""

import pygame

from app.input.actions import Action
from app.ui.components import (
    header,
    scroll_text,
)
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, text
from app.ui.theme import THEME


def _legacy_render(
    surface: pygame.Surface, controller: UIController, fonts: Fonts
) -> list[Control]:
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
        f"Review {controller.review_index + 1}/{len(controller.review_items)} - "
        f"{item.outcome.upper()}",
        (16, 10),
        fonts.heading,
        color=THEME.accent,
    )
    paragraph(surface, item.question.question_text, Rect(16, 52, 768, 80), fonts.body, max_lines=4)
    selected = response.selected_key if response and response.selected_key else "Skipped"
    selected_option = next(
        (option.text for option in item.question.options if option.key == selected), ""
    )
    correct_option = next(
        option.text for option in item.question.options if option.key == item.question.correct_key
    )
    confidence = response.confidence.value if response and response.confidence else "-"
    paragraph(
        surface,
        f"Your answer: {selected} - {selected_option}"
        if selected_option
        else "Your answer: Skipped",
        Rect(24, 145, 740, 42),
        fonts.body,
        max_lines=2,
    )
    paragraph(
        surface,
        f"Correct answer: {item.question.correct_key} - {correct_option}",
        Rect(24, 190, 740, 42),
        fonts.body,
        max_lines=2,
    )
    text(surface, f"Confidence: {confidence}", (24, 235), fonts.small)
    text(
        surface,
        f"Response time: {response.response_time_ms if response else 0} ms",
        (280, 235),
        fonts.small,
    )
    text(
        surface,
        f"Review flag: {'yes' if response and response.marked_review else 'no'}",
        (510, 235),
        fonts.small,
    )
    paragraph(
        surface,
        "Explanation: " + (item.question.explanation or "No explanation provided."),
        Rect(24, 275, 752, 80),
        fonts.option,
        max_lines=4,
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


def render(surface, c, fonts):
    if not c.student_flow:
        return _legacy_render(surface, c, fonts)
    controls = []
    header(surface, controls, f"REVIEW / {c.review_filter.replace('_', ' ')}", c, fonts)
    if not c.review_items:
        text(surface, "No questions match this filter.", (24, 110), fonts.heading)
        return controls
    item = c.review_items[c.review_index]
    response, q = item.response, item.question
    text(
        surface,
        f"{c.review_index + 1} / {len(c.review_items)}   |   {item.outcome.upper()}",
        (24, 72),
        fonts.body,
    )
    selected = response.selected_key if response and response.selected_key else "Skipped"
    selected_text = next((o.text for o in q.options if o.key == selected), "")
    correct_text = next(o.text for o in q.options if o.key == q.correct_key)
    content = (
        f"{q.question_text}\n\nYour answer: {selected} {selected_text}\n\nCorrect answer: {q.correct_key} {correct_text}\n\n"
        f"Confidence: {response.confidence.value if response else 'unrated'}\n\nExplanation\n{q.explanation or 'No explanation provided.'}"
    )
    scroll_text(surface, controls, c, fonts, content, rect=Rect(24, 112, 752, 240))
    button(
        surface,
        controls,
        Rect(256, 366, 120, 48),
        "< Previous",
        Action.PREV,
        fonts,
        enabled=c.review_index > 0,
    )
    button(surface, controls, Rect(392, 366, 120, 48), "Full text", Action.CONFIRM, fonts)
    button(
        surface,
        controls,
        Rect(528, 366, 112, 48),
        "Next >",
        Action.NEXT,
        fonts,
        enabled=c.review_index < len(c.review_items) - 1,
    )
    button(surface, controls, Rect(656, 366, 120, 48), "Done", Action.BACK, fonts)
    return controls
