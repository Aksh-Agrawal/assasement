"""Minimal settings limited to supported software preferences."""

import pygame

from app.input.actions import Action
from app.ui.components import (
    choice_button,
    header,
)
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, status, text, top_bar
from app.ui.theme import THEME


def _legacy_render(
    surface: pygame.Surface, controller: UIController, fonts: Fonts
) -> list[Control]:
    controls: list[Control] = []
    top_bar(surface, controls, "Settings", fonts)
    current = controller.repository.get_setting("text_size") or "standard"
    text(surface, "Text size", (70, 105), fonts.body)
    text(surface, current.title(), (570, 105), fonts.body, color=THEME.muted)
    button(surface, controls, Rect(520, 150, 210, 56), "Change text size", Action.CONFIRM, fonts)
    text(surface, "Device status", (70, 250), fonts.body)
    text(
        surface,
        f"Assessment Device v{controller.software_version}",
        (70, 330),
        fonts.small,
        color=THEME.muted,
    )
    text(surface, "Press Back to return home", (70, 370), fonts.small, color=THEME.muted)
    status(surface, controller.message, fonts)
    return controls


def render(surface, c, fonts):
    if not c.student_flow:
        return _legacy_render(surface, c, fonts)
    controls = []
    header(surface, controls, "SETTINGS", c, fonts)
    for index in range(8):
        row, col = divmod(index, 2)
        choice_button(
            surface, controls, c, fonts, index, Rect(24 + col * 384, 80 + row * 84, 368, 72)
        )
    return controls
