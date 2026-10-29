"""Shared 800 x 480 device chrome, lists, full-content scrolling and keyboard."""

import math
from functools import lru_cache

import pygame

from app.input.actions import Action
from app.ui.layout import Rect, wrap_text
from app.ui.router import UIScreen
from app.ui.screens.common import button, paragraph, text
from app.ui.theme import THEME

CONTENT = Rect(24, 96, 752, 258)


def header(surface, controls, heading, controller, fonts, *, back=True):
    if back:
        button(surface, controls, Rect(16, 4, 88, 48), "< Back", Action.BACK, fonts)
    x = 120 if back else 24
    paragraph(surface, heading, Rect(x, 16, 545 - x, 32), fonts.heading, max_lines=1)
    label = controller.network_label
    text(surface, label, (790 - fonts.small.size(label)[0], 22), fonts.small, color=THEME.muted)
    pygame.draw.line(surface, THEME.disabled, (16, 57), (784, 57))


def footer(surface, controller, fonts):
    labels = {
        UIScreen.QUESTION: "A/B/C/D Answer   LEFT Previous   RIGHT Next   R Review   MENU",
        UIScreen.CONFIDENCE: "A Sure   B Not Sure   C Guessing   MENU Back to options",
        UIScreen.QUESTION_NAV: "LEFT / RIGHT Choose   A Open   MENU Assessment menu",
        UIScreen.REVIEW: "LEFT Previous   RIGHT Next   A Full text   MENU Done",
        UIScreen.QUESTION_DETAIL: "LEFT / RIGHT Page   A Return   MENU Back",
        UIScreen.PROGRESS: "LEFT / RIGHT History   MENU Back   Esc Back",
        UIScreen.LINK_PROFILE: "LEFT / RIGHT Character   A Type   B Delete   D Review link   MENU Back",
        UIScreen.PIN: "LEFT / RIGHT Digit   A Type   B Delete   D Unlock   MENU Back",
        UIScreen.SUBMIT_CONFIRM: "A Continue test   T Submit   MENU Question navigator",
        UIScreen.ADD_PROFILE: "LEFT / RIGHT Character   A Type   B Delete   C Keys   D Save   MENU Back",
    }
    value = labels.get(controller.screen, "LEFT / RIGHT Choose   A Select   MENU Back   Esc Back")
    if controller.screen is UIScreen.HOME:
        value = "LEFT / RIGHT Choose   A Select   MENU Settings   Esc Switch profile"
    if controller.screen is UIScreen.WIFI and controller.selected_wifi:
        value = "LEFT / RIGHT Character   A Type   B Delete   C Keys   D Connect   MENU Back"
    pygame.draw.rect(surface, THEME.surface, pygame.Rect(0, 446, 800, 34))
    pygame.draw.line(surface, THEME.disabled, (16, 446), (784, 446))
    text(surface, value, (20, 457), fonts.small, color=THEME.muted)
    if controller.message:
        paragraph(
            surface,
            controller.message,
            Rect(24, 422, 752, 22),
            fonts.small,
            color=THEME.warning,
            max_lines=1,
        )


def choice_button(surface, controls, controller, fonts, index, rect, *, primary=False):
    choices = controller.choices
    if index >= len(choices):
        return
    choice = choices[index]
    button(
        surface,
        controls,
        rect,
        choice.label,
        Action.CONFIRM,
        fonts,
        enabled=choice.enabled,
        state="focus" if controller.focus == index else "primary" if primary else "normal",
        payload=("choice", index),
    )


def choice_list(surface, controls, controller, fonts, *, top=108, rows=3, height=72):
    choices = controller.choices
    page = controller.focus // rows
    first = page * rows
    for row, index in enumerate(range(first, min(first + rows, len(choices)))):
        choice_button(
            surface,
            controls,
            controller,
            fonts,
            index,
            Rect(24, top + row * (height + 8), 752, height),
        )
    if not choices:
        text(surface, "No local content available.", (24, top + 20), fonts.body, color=THEME.muted)
    if len(choices) > rows:
        button(surface, controls, Rect(24, 366, 144, 48), "< Choose", Action.PREV, fonts)
        text(surface, f"{controller.focus + 1} / {len(choices)}", (365, 382), fonts.small)
        button(surface, controls, Rect(632, 366, 144, 48), "Choose >", Action.NEXT, fonts)


def document_lines(value, font, width=724):
    return wrap_text(value, lambda line: font.size(line)[0], width)


def scroll_text(surface, controls, controller, fonts, value, *, rect=CONTENT):
    lines = document_lines(value, fonts.body, rect.width - 20)
    line_height = fonts.body.get_linesize()
    visible = max(1, rect.height // line_height)
    maximum = max(0, len(lines) - visible)
    controller.scroll = min(controller.scroll, maximum)
    old = surface.get_clip()
    surface.set_clip(pygame.Rect(rect.x, rect.y, rect.width, rect.height))
    for i, line in enumerate(lines[controller.scroll : controller.scroll + visible]):
        text(surface, line, (rect.x, rect.y + i * line_height), fonts.body)
    surface.set_clip(old)
    if maximum:
        scroll_controls(
            surface, controls, controller, fonts, controller.scroll > 0, controller.scroll < maximum
        )


def scroll_controls(surface, controls, controller, fonts, up, down):
    button(
        surface,
        controls,
        Rect(24, 366, 104, 48),
        "Scroll up",
        Action.CONFIRM,
        fonts,
        enabled=up,
        payload=("scroll", -5),
    )
    button(
        surface,
        controls,
        Rect(136, 366, 104, 48),
        "Scroll down",
        Action.CONFIRM,
        fonts,
        enabled=down,
        payload=("scroll", 5),
    )


@lru_cache(maxsize=12)
def media_image(path_string, stamp):
    image = pygame.image.load(path_string)
    width, height = image.get_size()
    if width * height > 4_000_000:
        raise ValueError("Diagram exceeds device limits")
    factor = min(1, 680 / width, 180 / height)
    return pygame.transform.smoothscale(
        image, (max(1, int(width * factor)), max(1, int(height * factor)))
    )


def question_media(controller, question):
    if not question.media_ref or not controller.device:
        return None
    root = controller.device.config.media_directory.resolve()
    path = (root / question.media_ref).resolve()
    if not path.is_relative_to(root):
        return None
    try:
        if path.stat().st_size > 5_000_000:
            return None
        return media_image(str(path), path.stat().st_mtime_ns)
    except (OSError, ValueError, pygame.error):
        return None


def full_content(controller):
    if controller.detail_return_screen is UIScreen.REVIEW:
        if not controller.review_items:
            return "No questions match this review filter."
        item = controller.review_items[controller.review_index]
        question, response = item.question, item.response
    else:
        question = controller.application.current_question()
        response = controller.application.current_response()
    value = (
        question.question_text
        + "\n\n"
        + "\n\n".join(f"{o.key} - {o.text}" for o in question.options)
    )
    if controller.detail_return_screen is UIScreen.REVIEW:
        value += f"\n\nYour answer: {response.selected_key if response else 'Skipped'}\nCorrect: {question.correct_key}\n\nExplanation\n{question.explanation or 'No explanation provided.'}"
    return value


def keyboard(surface, controls, controller, fonts, *, pin=False):
    chars = controller.keyboard_characters
    columns = 10
    page_start = controller.keyboard_index // 40 * 40
    chars = chars[page_start : page_start + 40]
    for index, char in enumerate(chars):
        x, y = 24 + index % columns * 56, 164 + index // columns * 52
        button(
            surface,
            controls,
            Rect(x, y, 48, 48),
            char,
            Action.CONFIRM,
            fonts,
            state="focus" if index + page_start == controller.keyboard_index else "normal",
            payload=("text", char),
        )
    button(
        surface,
        controls,
        Rect(608, 164, 168, 48),
        "Delete",
        Action.CONFIRM,
        fonts,
        payload=("command", "delete"),
    )
    if not pin and controller.screen is not UIScreen.LINK_PROFILE:
        button(
            surface,
            controls,
            Rect(608, 216, 168, 48),
            "abc / ABC / 123",
            Action.CONFIRM,
            fonts,
            payload=("command", "case"),
        )
        button(
            surface,
            controls,
            Rect(608, 268, 168, 48),
            "Space",
            Action.CONFIRM,
            fonts,
            payload=("command", "space"),
        )
        if len(controller.keyboard_characters) > 40:
            button(
                surface,
                controls,
                Rect(608, 316, 168, 48),
                "More keys",
                Action.CONFIRM,
                fonts,
                payload=("command", "more_keys"),
            )
    button(
        surface,
        controls,
        Rect(608, 366, 168, 48),
        "Unlock" if pin else "Review link" if controller.screen is UIScreen.LINK_PROFILE
        else "Connect" if controller.screen is UIScreen.WIFI else "Save profile",
        Action.CONFIRM,
        fonts,
        state="primary",
        payload=("command", "text_submit"),
    )


def detail_pages(controller, fonts):
    lines = document_lines(full_content(controller), fonts.body)
    per_page = 300 // fonts.body.get_linesize()
    controller.page_count = max(1, math.ceil(len(lines) / per_page))
    controller.detail_page = min(controller.detail_page, controller.page_count - 1)
    first = controller.detail_page * per_page
    return lines[first : first + per_page]
