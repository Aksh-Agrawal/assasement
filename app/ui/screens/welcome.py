"""Student welcome screen."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, text
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    pygame.draw.circle(surface, THEME.accent, (400, 105), 38)
    text(surface, "A", (391, 85), fonts.heading, color=THEME.accent_text)
    heading = fonts.title.render("Welcome", True, THEME.foreground)
    surface.blit(heading, (400 - heading.get_width() // 2, 165))
    sub = fonts.body.render("Ready for your assessment?", True, THEME.muted)
    surface.blit(sub, (400 - sub.get_width() // 2, 220))
    button(
        surface,
        controls,
        Rect(265, 285, 270, 68),
        "Get Started",
        Action.CONFIRM,
        fonts,
        state="primary",
    )
    color = THEME.success if controller.network_label == "Online" else THEME.warning
    text(surface, controller.network_label, (680, 440), fonts.small, color=color)
    return controls
