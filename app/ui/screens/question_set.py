"""Installed chapter/question-set selection and start/resume screen."""

import pygame

from app.input.actions import Action
from app.ui.controller import UIController
from app.ui.layout import Rect
from app.ui.screens.common import Control, Fonts, button, paragraph, status, text, title
from app.ui.theme import THEME


def render(surface: pygame.Surface, controller: UIController, fonts: Fonts) -> list[Control]:
    controls: list[Control] = []
    title(surface, f"{controller.selected_subject or 'Subject'} assessments", fonts)
    selected = controller.selected_question_set
    resume = controller.resume_summary
    if selected is None:
        paragraph(surface, "No question sets are installed for this subject.", Rect(80, 130, 640, 70), fonts.body)
    else:
        text(surface, f"Set {controller.set_index + 1} of {len(controller.subject_question_sets)}", (340, 58), fonts.small, color=THEME.muted)
        card = pygame.Rect(80, 82, 640, 180)
        pygame.draw.rect(surface, THEME.surface, card, border_radius=THEME.corner_radius)
        pygame.draw.rect(surface, THEME.accent, card, THEME.border_width, border_radius=THEME.corner_radius)
        text(surface, selected.title, (105, 105), fonts.heading)
        paragraph(surface, selected.chapter, Rect(105, 145, 590, 50), fonts.body, max_lines=2)
        text(surface, f"{len(selected.questions)} questions  •  Version {selected.version}", (105, 215), fonts.small, color=THEME.muted)
    button(surface, controls, Rect(80, 280, 190, 52), "Previous set", Action.PREV, fonts)
    button(surface, controls, Rect(530, 280, 190, 52), "Next set", Action.NEXT, fonts)
    if resume:
        resume_title, answered, total = resume
        paragraph(surface, f"In progress: {resume_title} — {answered} of {total} answered. Resume it before starting another assessment.", Rect(190, 343, 580, 45), fonts.small, color=THEME.muted, max_lines=3)
        label = "Resume Assessment"
    else:
        label = "Start Assessment"
    button(surface, controls, Rect(30, 400, 140, 52), "Back", Action.BACK, fonts)
    button(surface, controls, Rect(500, 392, 270, 60), label, Action.CONFIRM, fonts, state="selected", enabled=selected is not None or resume is not None)
    status(surface, controller.message, fonts)
    return controls
