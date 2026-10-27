"""Page-like full-content view for long assessment and review text."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController, UIScreen
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, text, title
from app.ui.theme import THEME


def _current_content(controller: UIController) -> tuple[str, object, object | None]:
    if controller.detail_return_screen is UIScreen.REVIEW:
        item = controller.review_items[controller.review_index]
        return f"Review {item.position}", item.question, item.response
    return "Question full text", controller.application.current_question(), controller.application.current_response()


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    heading, question, response = _current_content(controller)
    title(surface, f"{heading} — page {controller.detail_page + 1}/3", fonts)
    if controller.detail_page == 0:
        text(surface, "Question", (24, 58), fonts.small, color=THEME.muted)
        paragraph(surface, question.question_text, Rect(24, 82, 752, 300), fonts.option, max_lines=17)
    elif controller.detail_page == 1:
        for index, option in enumerate(question.options[:2]):
            selected = bool(response and response.selected_key == option.key)
            text(surface, f"{'Selected — ' if selected else ''}{option.key}", (24, 62 + index * 160), fonts.body, color=THEME.accent if selected else THEME.foreground)
            paragraph(surface, option.text, Rect(60, 92 + index * 160, 716, 120), fonts.option, max_lines=7)
    else:
        if controller.detail_return_screen is UIScreen.REVIEW:
            text(surface, "Explanation", (24, 62), fonts.body)
            paragraph(surface, question.explanation or "No explanation provided.", Rect(24, 96, 752, 280), fonts.option, max_lines=16)
        else:
            for index, option in enumerate(question.options[2:]):
                selected = bool(response and response.selected_key == option.key)
                text(surface, f"{'Selected — ' if selected else ''}{option.key}", (24, 62 + index * 160), fonts.body, color=THEME.accent if selected else THEME.foreground)
                paragraph(surface, option.text, Rect(60, 92 + index * 160, 716, 120), fonts.option, max_lines=7)
    button(surface, controls, Rect(24, 405, 140, 52), "Previous page", Action.PREV, fonts, enabled=controller.detail_page > 0)
    button(surface, controls, Rect(330, 405, 140, 52), "Back", Action.BACK, fonts)
    button(surface, controls, Rect(636, 405, 140, 52), "Next page", Action.NEXT, fonts, enabled=controller.detail_page < 2)
    return controls
