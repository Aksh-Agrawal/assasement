"""Subject selection derived exclusively from installed question sets."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, status, text, title
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    title(surface, "Choose subject", fonts)
    profile = controller.selected_profile
    text(
        surface,
        f"Student: {profile.display_name if profile else '-'}",
        (24, 52),
        fonts.small,
        color=THEME.muted,
    )
    subject = controller.selected_subject
    if subject is None:
        paragraph(
            surface,
            "No subjects are installed. Import a validated local question pack, then return to this screen.",
            Rect(90, 130, 620, 100),
            fonts.body,
            max_lines=5,
        )
        button(surface, controls, Rect(30, 390, 150, 55), "Back", Action.BACK, fonts)
    else:
        count = len(controller.subject_question_sets)
        text(
            surface,
            f"Subject {controller.subject_index + 1} of {len(controller.subjects)}",
            (325, 110),
            fonts.small,
            color=THEME.muted,
        )
        button(
            surface,
            controls,
            Rect(155, 145, 490, 105),
            f"{subject}\n{count} local question set{'s' if count != 1 else ''}",
            Action.CONFIRM,
            fonts,
            state="selected",
        )
        button(surface, controls, Rect(80, 285, 190, 58), "Previous subject", Action.PREV, fonts)
        button(surface, controls, Rect(530, 285, 190, 58), "Next subject", Action.NEXT, fonts)
        button(surface, controls, Rect(30, 390, 150, 55), "Back", Action.BACK, fonts)
        button(
            surface,
            controls,
            Rect(520, 380, 250, 65),
            "Choose question set",
            Action.CONFIRM,
            fonts,
            state="selected",
        )
    status(surface, controller.message, fonts)
    return controls
