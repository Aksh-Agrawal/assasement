"""Root profile-selection and development-profile creation screen."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, status, text, title
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    title(surface, "Choose student profile", fonts)
    text(surface, "Profiles are stored only on this device.", (24, 52), fonts.small, color=THEME.muted)
    profile = controller.selected_profile
    if profile is None:
        paragraph(
            surface,
            "No local student profiles are available. Create the development profile to "
            "continue. Custom names and PIN authentication are deferred.",
            Rect(80, 120, 640, 100),
            fonts.body,
            max_lines=5,
        )
        button(surface, controls, Rect(220, 280, 360, 72), "Create Development Student", Action.CONFIRM, fonts, state="selected")
    else:
        text(surface, f"Profile {controller.profile_index + 1} of {len(controller.profiles)}", (325, 105), fonts.small, color=THEME.muted)
        card = pygame.Rect(130, 135, 540, 100)
        pygame.draw.rect(surface, THEME.surface, card, border_radius=THEME.corner_radius)
        pygame.draw.rect(surface, THEME.accent, card, THEME.focus_width, border_radius=THEME.corner_radius)
        text(surface, profile.display_name, (170, 172), fonts.heading)
        button(surface, controls, Rect(80, 275, 190, 58), "Previous profile", Action.PREV, fonts)
        button(surface, controls, Rect(530, 275, 190, 58), "Next profile", Action.NEXT, fonts)
        button(surface, controls, Rect(250, 365, 300, 64), "Continue", Action.CONFIRM, fonts, state="selected")
    status(surface, controller.message, fonts)
    return controls
