"""Primary assessment question view."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, status, text
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    app = controller.application
    question = app.current_question()
    response = app.current_response()
    question_set = app.engine.question_set
    index = app.engine.current_index
    total = len(app.engine.ordered_question_ids)
    heading = f"{question_set.subject} • {question_set.title}" if question_set else "Assessment"
    text(surface, heading, (16, 8), fonts.small, color=THEME.muted)
    if question_set:
        text(surface, question_set.chapter, (16, 25), fonts.small, color=THEME.muted)
    text(surface, f"Question {index + 1} / {total}", (650, 10), fonts.small)
    paragraph(surface, question.question_text, Rect(16, 46, 768, 66), fonts.body, max_lines=3)

    for option_index, option in enumerate(question.options):
        rect = Rect(16, 116 + option_index * 61, 768, 53)
        action = (Action.SELECT_A, Action.SELECT_B, Action.SELECT_C, Action.SELECT_D)[option_index]
        selected = bool(response and response.selected_key == option.key)
        button(
            surface,
            controls,
            rect,
            f"{'[SELECTED] ' if selected else ''}{option.key}. {option.text}",
            action,
            fonts,
            state="selected" if selected else "normal",
        )

    marked = bool(response and response.marked_review)
    confidence = response.confidence.value if response and response.confidence else "—"
    answer = response.selected_key if response and response.selected_key else "—"
    answered = sum(
        item.selected_key is not None for item in controller.application.engine.responses()
    )
    text(
        surface,
        f"Answer: {answer}  •  Confidence: {confidence}  •  Answered {answered}/{total}",
        (16, 366),
        fonts.small,
    )
    if marked:
        text(surface, "MARKED FOR REVIEW", (625, 366), fonts.small, color=THEME.foreground)
    button(surface, controls, Rect(16, 397, 96, 48), "Full text", Action.CONFIRM, fonts)
    button(
        surface,
        controls,
        Rect(120, 397, 96, 48),
        "Previous",
        Action.PREV,
        fonts,
        enabled=index > 0,
    )
    button(
        surface,
        controls,
        Rect(224, 397, 170, 48),
        "Unmark review" if marked else "Mark review",
        Action.MARK_REVIEW,
        fonts,
        state="review" if marked else "normal",
    )
    button(surface, controls, Rect(550, 397, 110, 48), "Next", Action.NEXT, fonts)
    button(surface, controls, Rect(670, 397, 114, 48), "Submit", Action.SUBMIT, fonts)
    status(surface, controller.message, fonts)
    return controls
