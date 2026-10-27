"""Small-screen rendering checks for long and empty local content."""

from pathlib import Path

import pygame

from app.core.models import MarkingScheme, Option, Question, QuestionSet
from app.data.repo import Repository
from app.input.actions import Action
from app.ui.controller import UIController, UIScreen
from app.ui.layout import LOGICAL_HEIGHT, LOGICAL_WIDTH
from app.ui.screens import detail, error, home, question, review, subject
from app.ui.screens.common import Control, make_fonts


def _assert_controls_fit(controls: list[Control]) -> None:
    for control in controls:
        assert 0 <= control.rect.x < LOGICAL_WIDTH
        assert 0 <= control.rect.y < LOGICAL_HEIGHT
        assert control.rect.x + control.rect.width <= LOGICAL_WIDTH
        assert control.rect.y + control.rect.height <= LOGICAL_HEIGHT
        assert min(control.rect.width, control.rect.height) >= 48


def _long_set() -> QuestionSet:
    long_option = (
        "This intentionally long answer discusses organelles, membrane transport, "
        "homeostasis, concentration gradients, and molecular interactions in detail. "
    ) * 2
    return QuestionSet(
        id="biology-long-ui-01",
        version=1,
        title="Long Content Fixture",
        subject="Biology",
        chapter="Cell Structure and Function with Extended Development Text",
        marking=MarkingScheme(),
        questions=(
            Question(
                id="bio-long-ui-q0001",
                position=1,
                topic="Long content",
                difficulty=2,
                question_text=(
                    "A student studies a cell under several experimental conditions and "
                    "compares membrane permeability, organelle function, energy transfer, "
                    "and homeostatic responses. Which conclusion best integrates all of "
                    "these observations without contradicting the fluid-mosaic model? "
                ) * 2,
                options=tuple(
                    Option(key=key, text=f"{long_option} Choice {key}.")
                    for key in ("A", "B", "C", "D")
                ),
                correct_key="A",
                explanation=(
                    "The correct choice is consistent with selective permeability and the "
                    "dynamic arrangement of membrane proteins and phospholipids. "
                ) * 5,
            ),
        ),
    )


def test_long_content_and_empty_states_render_inside_800_by_480(tmp_path: Path) -> None:
    pygame.font.init()
    surface = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT))
    fonts = make_fonts()

    with Repository(tmp_path / "empty.db") as repository:
        empty = UIController(repository)
        _assert_controls_fit(home.render(surface, empty, fonts))
        empty.handle(Action.CONFIRM)
        empty.handle(Action.CONFIRM)
        assert empty.screen is UIScreen.SUBJECT
        _assert_controls_fit(subject.render(surface, empty, fonts))
        _assert_controls_fit(error.render_message(surface, "Database unavailable", fonts))

    with Repository(tmp_path / "long.db") as repository:
        repository.import_question_set(_long_set(), content_hash="long-ui", is_active=True)
        controller = UIController(repository)
        controller.handle(Action.CONFIRM)
        controller.handle(Action.CONFIRM)
        controller.handle(Action.CONFIRM)
        controller.handle(Action.CONFIRM)
        assert controller.screen is UIScreen.QUESTION
        _assert_controls_fit(question.render(surface, controller, fonts))

        controller.handle(Action.CONFIRM)
        for page in range(3):
            controller.detail_page = page
            _assert_controls_fit(detail.render(surface, controller, fonts))
        controller.handle(Action.BACK)
        controller.handle(Action.SELECT_A)
        controller.handle(Action.SURE)
        controller.handle(Action.NEXT)
        controller.handle(Action.CONFIRM)
        controller.handle(Action.CONFIRM)
        assert controller.screen is UIScreen.REVIEW
        _assert_controls_fit(review.render(surface, controller, fonts))
        controller.handle(Action.CONFIRM)
        controller.detail_page = 2
        _assert_controls_fit(detail.render(surface, controller, fonts))
