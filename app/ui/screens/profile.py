"""Touch-friendly local student profile selection."""

import pygame

from app.input.actions import Action
from app.ui.components import (
    choice_button,
    header,
)
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, empty_state, text, top_bar
from app.ui.theme import THEME


def _initials(name: str) -> str:
    words = name.split()
    return "".join(word[0] for word in words[:2]).upper() or "S"


def _legacy_render(
    surface: pygame.Surface, controller: UIController, fonts: Fonts
) -> list[Control]:
    controls: list[Control] = []
    top_bar(
        surface, controls, "Who's taking the assessment?", fonts, network=controller.network_label
    )
    profile = controller.selected_profile
    if profile is None:
        empty_state(
            surface,
            "No student profiles",
            "Create a local student profile to begin. It remains available offline.",
            fonts,
        )
        button(
            surface,
            controls,
            Rect(260, 320, 280, 64),
            "+ Add Profile",
            Action.CONFIRM,
            fonts,
            state="primary",
        )
        return controls
    card = pygame.Rect(230, 95, 340, 220)
    pygame.draw.rect(surface, THEME.surface, card, border_radius=16)
    pygame.draw.rect(surface, THEME.accent, card, 3, border_radius=16)
    pygame.draw.circle(surface, THEME.selected, (400, 165), 50)
    initials = fonts.title.render(_initials(profile.display_name), True, THEME.accent)
    surface.blit(initials, (400 - initials.get_width() // 2, 165 - initials.get_height() // 2))
    name = fonts.heading.render(profile.display_name, True, THEME.foreground)
    surface.blit(name, (400 - name.get_width() // 2, 235))
    text(
        surface,
        f"Profile {controller.profile_index + 1} of {len(controller.profiles)}",
        (337, 280),
        fonts.small,
        color=THEME.muted,
    )
    button(
        surface,
        controls,
        Rect(70, 150, 120, 60),
        "< Previous",
        Action.PREV,
        fonts,
        enabled=len(controller.profiles) > 1,
    )
    button(
        surface,
        controls,
        Rect(610, 150, 120, 60),
        "Next >",
        Action.NEXT,
        fonts,
        enabled=len(controller.profiles) > 1,
    )
    button(
        surface,
        controls,
        Rect(270, 365, 260, 64),
        "Continue",
        Action.CONFIRM,
        fonts,
        state="primary",
    )
    return controls


def render(surface, c, fonts):
    if not c.student_flow:
        return _legacy_render(surface, c, fonts)
    controls = []
    header(surface, controls, "ASSESS", c, fonts, back=False)
    text(surface, "Who is using this device?", (24, 74), fonts.title)
    count = len(c.profiles)
    page = min(c.focus, max(0, count - 1)) // 2
    for i in range(page * 2, min(page * 2 + 2, count)):
        x = 24 + (i % 2) * 384
        choice_button(surface, controls, c, fonts, i, Rect(x, 124, 368, 156))
        pygame.draw.circle(surface, THEME.selected, (x + 184, 158), 26)
        initials = _initials(c.profiles[i].display_name)
        rendered = fonts.heading.render(initials, True, THEME.accent)
        surface.blit(rendered, (x + 184 - rendered.get_width() // 2, 147))
    if not count:
        text(
            surface,
            "Add a local profile to begin practising offline.",
            (24, 170),
            fonts.body,
            color=THEME.muted,
        )
    if count > 2:
        button(surface, controls, Rect(24, 288, 144, 48), "< Choose", Action.PREV, fonts)
        text(
            surface,
            f"Profiles {page * 2 + 1}-{min(page * 2 + 2, count)} of {count}",
            (280, 304),
            fonts.small,
        )
        button(surface, controls, Rect(632, 288, 144, 48), "Choose >", Action.NEXT, fonts)
    for i in range(2):
        choice_button(surface, controls, c, fonts, count + i, Rect(24 + i * 384, 350, 368, 64))
    return controls
