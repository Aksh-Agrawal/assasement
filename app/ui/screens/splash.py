"""Fast, non-network-blocking startup surface."""

import pygame

from app.ui.controller import UIController
from app.ui.screens.common import Control, Fonts, text
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    pygame.draw.circle(surface, THEME.accent, (400, 165), 48)
    text(surface, "A", (388, 140), fonts.title, color=THEME.accent_text)
    label = fonts.title.render("Assessment Device", True, THEME.foreground)
    surface.blit(label, (400 - label.get_width() // 2, 230))
    loading = fonts.body.render("Loading...", True, THEME.muted)
    surface.blit(loading, (400 - loading.get_width() // 2, 290))
    text(surface, f"v{controller.software_version}", (16, 445), fonts.small, color=THEME.muted)
    return []
