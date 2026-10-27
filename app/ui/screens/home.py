"""Student home dashboard."""

import pygame

from app.input.actions import Action
from app.ui.components import (
    choice_button,
    header,
)
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, text, top_bar
from app.ui.theme import THEME


def _legacy_render(
    surface: pygame.Surface, controller: UIController, fonts: Fonts
) -> list[Control]:
    controls: list[Control] = []
    profile = controller.selected_profile
    top_bar(
        surface,
        controls,
        f"Hi, {profile.display_name if profile else 'Student'}",
        fonts,
        back=False,
        network=controller.network_label,
    )
    text(surface, "What would you like to do?", (28, 70), fonts.body, color=THEME.muted)
    cards = (
        ("Start Test", "New assessment", Action.SELECT_A, True),
        ("Resume Test", "Continue where you left off", Action.SELECT_B, controller.can_resume),
        ("Results", "Past attempts", Action.SELECT_C, True),
        ("Device Status", "Sync and content", Action.SELECT_D, True),
    )
    for index, (heading, sub, action, enabled) in enumerate(cards):
        col, row = index % 2, index // 2
        rect = Rect(28 + col * 382, 110 + row * 130, 360, 108)
        state = "focus" if controller.dashboard_index == index else "normal"
        button(
            surface,
            controls,
            rect,
            f"{heading}\n{sub}",
            action,
            fonts,
            state=state,
            enabled=enabled,
        )
        if not enabled:
            paragraph(
                surface,
                "No assessment to continue",
                Rect(rect.x + 12, rect.y + 74, rect.width - 24, 24),
                fonts.small,
                color=THEME.muted,
                max_lines=1,
            )
    button(surface, controls, Rect(28, 390, 150, 52), "Settings", Action.MENU, fonts)
    text(surface, "A-D choose  |  Enter opens", (285, 407), fonts.small, color=THEME.muted)
    button(surface, controls, Rect(650, 390, 122, 52), "Switch", Action.BACK, fonts)
    return controls


def render(surface, c, fonts):
    if not c.student_flow:
        return _legacy_render(surface, c, fonts)
    controls = []
    header(surface, controls, "ASSESS", c, fonts, back=False)
    name = c.selected_profile.display_name if c.selected_profile else "Student"
    paragraph(surface, f"{c.greeting}, {name}", Rect(24, 82, 752, 42), fonts.title, max_lines=1)
    text(surface, "Ready to practise?", (24, 128), fonts.body, color=THEME.muted)
    choice_button(surface, controls, c, fonts, 0, Rect(24, 180, 364, 136))
    resume = c.resume_summary
    if resume:
        text(
            surface,
            f"{resume[1]} / {resume[2]} answered and saved",
            (40, 284),
            fonts.small,
            color=THEME.muted,
        )
    choice_button(surface, controls, c, fonts, 1, Rect(408, 180, 368, 136), primary=True)
    for index in range(2, 5):
        choice_button(
            surface, controls, c, fonts, index, Rect(24 + (index - 2) * 256, 342, 240, 64)
        )
    return controls
