"""Confidence choice shown after durable answer selection."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, title
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    title(surface, "How confident are you?", fonts)
    response = controller.application.current_response()
    paragraph(
        surface,
        f"Answer {response.selected_key if response else '—'} is already saved.",
        Rect(24, 65, 752, 40),
        fonts.body,
    )
    button(surface, controls, Rect(80, 135, 280, 68), "Sure (S)", Action.SURE, fonts)
    button(surface, controls, Rect(440, 135, 280, 68), "Not Sure (N)", Action.NOT_SURE, fonts)
    button(surface, controls, Rect(80, 235, 280, 68), "Guessing (G)", Action.GUESSING, fonts)
    button(
        surface,
        controls,
        Rect(440, 235, 280, 68),
        "Continue Unrated",
        Action.CONFIRM,
        fonts,
        state="selected",
    )
    paragraph(
        surface,
        "Escape also continues with confidence stored as unrated.",
        Rect(180, 350, 500, 30),
        fonts.small,
        color=THEME.muted,
    )
    return controls
