"""Primary assessment question view."""

import pygame

from app.input.actions import Action
from app.ui.components import (
    question_media,
)
from app.ui.controller import UIController
from app.ui.layout import Rect, wrap_text
from app.ui.screens.common import Control, Fonts, button, paragraph, progress_bar, status, text
from app.ui.theme import THEME


def _legacy_render(
    surface: pygame.Surface, controller: UIController, fonts: Fonts
) -> list[Control]:
    controls: list[Control] = []
    app = controller.application
    question = app.current_question()
    response = app.current_response()
    question_set = app.engine.question_set
    index = app.engine.current_index
    total = len(app.engine.ordered_question_ids)
    heading = f"{question_set.subject} - {question_set.title}" if question_set else "Assessment"
    text(surface, heading, (16, 7), fonts.small, color=THEME.muted)
    if question_set:
        text(surface, question_set.chapter, (16, 25), fonts.small, color=THEME.muted)
    text(surface, f"Q {index + 1} / {total}", (700, 8), fonts.small)
    progress_bar(surface, Rect(16, 42, 768, 7), (index + 1) / total)
    paragraph(surface, question.question_text, Rect(16, 58, 768, 68), fonts.body, max_lines=3)

    for option_index, option in enumerate(question.options):
        rect = Rect(16, 132 + option_index * 57, 768, 50)
        action = (Action.SELECT_A, Action.SELECT_B, Action.SELECT_C, Action.SELECT_D)[option_index]
        selected = bool(response and response.selected_key == option.key)
        button(
            surface,
            controls,
            rect,
            f"{'Selected - ' if selected else ''}{option.key}   {option.text}",
            action,
            fonts,
            state="selected" if selected else "normal",
        )

    marked = bool(response and response.marked_review)
    confidence = response.confidence.value if response and response.confidence else "-"
    answer = response.selected_key if response and response.selected_key else "-"
    answered = sum(
        item.selected_key is not None for item in controller.application.engine.responses()
    )
    text(
        surface,
        f"Answer: {answer}  |  Confidence: {confidence}  |  Answered {answered}/{total}",
        (16, 365),
        fonts.small,
    )
    if marked:
        text(surface, "REVIEW", (700, 365), fonts.small, color=THEME.warning)
    button(surface, controls, Rect(16, 397, 100, 52), "Questions", Action.MENU, fonts)
    button(
        surface,
        controls,
        Rect(124, 397, 100, 52),
        "< Prev",
        Action.PREV,
        fonts,
        enabled=index > 0,
    )
    button(
        surface,
        controls,
        Rect(232, 397, 170, 52),
        "Unmark" if marked else "Mark Review",
        Action.MARK_REVIEW,
        fonts,
        state="review" if marked else "normal",
    )
    button(surface, controls, Rect(540, 397, 110, 52), "Next >", Action.NEXT, fonts)
    button(
        surface, controls, Rect(658, 397, 126, 52), "Submit", Action.SUBMIT, fonts, state="primary"
    )
    status(surface, controller.message, fonts)
    return controls


def render(surface, c, fonts):
    if not c.student_flow:
        return _legacy_render(surface, c, fonts)
    controls = []
    app = c.application
    q, response, question_set = (
        app.current_question(),
        app.current_response(),
        app.engine.question_set,
    )
    total, index = len(app.engine.ordered_question_ids), app.engine.current_index
    heading = f"{question_set.subject} / {question_set.chapter}" if question_set else "Assessment"
    paragraph(surface, heading, Rect(24, 12, 440, 32), fonts.heading, max_lines=1)
    elapsed = (
        sum(r.response_time_ms for r in app.engine.responses() if r.question_id != q.id)
        + app.current_time_ms()
    )
    seconds = elapsed // 1000
    text(
        surface,
        f"Q {index + 1} of {total}   {seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}",
        (520, 18),
        fonts.body,
    )
    answered = sum(r.selected_key is not None for r in app.engine.responses())
    progress_bar(surface, Rect(24, 60, 570, 8), answered / total)
    text(surface, f"{answered * 100 // total}% saved", (610, 54), fonts.small, color=THEME.muted)
    # Measure the complete document before drawing. Every answer gets its full text.
    y = 84
    q_lines = wrap_text(q.question_text, lambda v: fonts.body.size(v)[0], 724)
    blocks = [("text", q_lines, y, len(q_lines) * fonts.body.get_linesize())]
    y += blocks[-1][3] + 8
    media = question_media(c, q)
    if q.media_ref:
        if media:
            blocks.append(("image", media, y, media.get_height()))
            y += media.get_height() + 16
        else:
            blocks.append(
                ("text", ["Diagram unavailable on this device."], y, fonts.body.get_linesize())
            )
            y += fonts.body.get_linesize() + 16
    for i, option in enumerate(q.options):
        lines = wrap_text(f"{option.key}   {option.text}", lambda v: fonts.body.size(v)[0], 700)
        height = max(50, len(lines) * fonts.body.get_linesize() + 16)
        blocks.append(("option", (i, option, lines), y, height))
        y += height + 8
    max_scroll = max(0, y - 8 - 354)
    c.scroll = min(c.scroll, max_scroll)
    old = surface.get_clip()
    surface.set_clip(pygame.Rect(24, 80, 752, 274))
    for kind, content, block_y, height in blocks:
        top = block_y - c.scroll
        if kind == "text":
            for i, line in enumerate(content):
                text(surface, line, (32, top + i * fonts.body.get_linesize()), fonts.body)
        elif kind == "image":
            surface.blit(content, (40, top))
        else:
            i, option, lines = content
            selected = bool(response and response.selected_key == option.key)
            rect = pygame.Rect(24, top, 752, height)
            pygame.draw.rect(
                surface, THEME.selected if selected else THEME.surface, rect, border_radius=8
            )
            pygame.draw.rect(
                surface,
                THEME.accent if selected else THEME.border,
                rect,
                3 if selected else 1,
                border_radius=8,
            )
            for line_index, line in enumerate(lines):
                text(
                    surface,
                    line,
                    (40, top + 10 + line_index * fonts.body.get_linesize()),
                    fonts.body,
                )
            # A clipped card is not a smaller touch target. Scroll to make it visible.
            visible_top, visible_bottom = max(80, top), min(354, top + height)
            if visible_bottom - visible_top >= 48:
                from app.ui.screens.common import Control

                controls.append(
                    Control(
                        Rect(24, visible_top, 752, visible_bottom - visible_top),
                        (Action.SELECT_A, Action.SELECT_B, Action.SELECT_C, Action.SELECT_D)[i],
                        option.key,
                    )
                )
    surface.set_clip(old)
    if max_scroll:
        button(
            surface,
            controls,
            Rect(24, 366, 72, 48),
            "Up",
            Action.CONFIRM,
            fonts,
            enabled=c.scroll > 0,
            payload=("scroll", -180),
        )
        button(
            surface,
            controls,
            Rect(104, 366, 72, 48),
            "Down",
            Action.CONFIRM,
            fonts,
            enabled=c.scroll < max_scroll,
            payload=("scroll", 180),
        )
    else:
        button(
            surface,
            controls,
            Rect(24, 366, 152, 48),
            "< Previous",
            Action.PREV,
            fonts,
            enabled=index > 0,
        )
    button(
        surface,
        controls,
        Rect(192, 366, 184, 48),
        "* Review" if response and response.marked_review else "Mark review",
        Action.MARK_REVIEW,
        fonts,
        state="review" if response and response.marked_review else "normal",
    )
    button(surface, controls, Rect(392, 366, 120, 48), "Full text", Action.CONFIRM, fonts)
    button(surface, controls, Rect(528, 366, 112, 48), "Next >", Action.NEXT, fonts)
    button(surface, controls, Rect(656, 366, 120, 48), "Menu", Action.MENU, fonts)
    return controls
