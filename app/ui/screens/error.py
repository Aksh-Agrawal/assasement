"""Minimal developer-friendly expected-error view."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, title


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    return render_message(surface, controller.message, fonts, support_code=controller.error_code)


def render_message(
    surface: pygame.Surface, message: str, fonts: Fonts, *, support_code: str = "APP-001"
) -> list[Control]:
    """Render an error even when controller/repository startup was impossible."""
    controls: list[Control] = []
    title(surface, "Something went wrong", fonts)
    paragraph(
        surface,
        message or "Your assessment is safe. Please try again.",
        Rect(40, 100, 720, 180),
        fonts.body,
        max_lines=8,
    )
    paragraph(surface, f"Support code: {support_code}", Rect(40, 285, 720, 35), fonts.small)
    button(surface, controls, Rect(120, 340, 250, 65), "Try Again", Action.CONFIRM, fonts)
    button(surface, controls, Rect(430, 340, 250, 65), "Back to home", Action.BACK, fonts)
    return controls
