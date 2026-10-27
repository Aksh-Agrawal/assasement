"""Minimal developer-friendly expected-error view."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, title


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    return render_message(surface, controller.message, fonts)


def render_message(surface: pygame.Surface, message: str, fonts: Fonts) -> list[Control]:
    """Render an error even when controller/repository startup was impossible."""
    controls: list[Control] = []
    title(surface, "Unable to continue", fonts)
    paragraph(
        surface,
        message or "An expected application error occurred.",
        Rect(40, 100, 720, 180),
        fonts.body,
        max_lines=8,
    )
    button(surface, controls, Rect(260, 340, 280, 65), "Back to home", Action.BACK, fonts)
    return controls
