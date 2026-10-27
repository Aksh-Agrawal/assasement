"""Headless GUI-controller integration against the real engine and SQLite."""

from dataclasses import replace
from pathlib import Path

from app.content.importer import import_pack
from app.core.engine import AssessmentState
from app.core.models import Confidence
from app.core.scoring import score_attempt
from app.data.repo import Repository
from app.input.actions import Action
from app.ui.controller import UIController, UIScreen


def seed_pack(repository: Repository) -> None:
    import_pack(Path("content/sample_biology.json"), repository, make_active=True)


def start_controller(repository: Repository) -> UIController:
    controller = UIController(repository)
    assert not controller.profiles
    controller.handle(Action.CONFIRM)
    assert controller.selected_profile is not None
    controller.handle(Action.CONFIRM)
    assert controller.screen is UIScreen.SUBJECT
    controller.handle(Action.CONFIRM)
    assert controller.screen is UIScreen.QUESTION_SET
    controller.handle(Action.CONFIRM)
    assert controller.screen is UIScreen.QUESTION
    return controller


def test_real_controller_flow_through_result_and_answer_review(tmp_path: Path) -> None:
    with Repository(tmp_path / "ui-flow.db") as repository:
        seed_pack(repository)
        controller = start_controller(repository)

        controller.handle(Action.SELECT_A)
        assert controller.screen is UIScreen.CONFIDENCE
        controller.handle(Action.SURE)
        assert controller.application.current_response().confidence is Confidence.SURE  # type: ignore[union-attr]
        controller.handle(Action.NEXT)
        controller.handle(Action.MARK_REVIEW)
        assert controller.application.current_response().marked_review is True  # type: ignore[union-attr]
        controller.handle(Action.PREV)
        controller.handle(Action.SELECT_B)
        controller.handle(Action.NOT_SURE)
        controller.handle(Action.SUBMIT)
        assert controller.screen is UIScreen.SUBMIT_CONFIRM
        controller.handle(Action.BACK)
        assert controller.screen is UIScreen.QUESTION
        controller.handle(Action.NEXT)
        for index in range(1, 20):
            controller.handle(Action.SELECT_A)
            controller.handle(Action.GUESSING if index == 1 else Action.SURE)
            controller.handle(Action.NEXT)
        assert controller.screen is UIScreen.SUBMIT_CONFIRM
        controller.handle(Action.CONFIRM)
        assert controller.screen is UIScreen.RESULT
        assert controller.result is not None
        assert controller.application.engine.state is AssessmentState.RESULT
        question_set = controller.application.engine.question_set
        attempt = controller.application.engine.attempt
        assert question_set is not None and attempt is not None
        expected = score_attempt(
            repository.get_attempt_responses(attempt.id),
            {question.id: question for question in question_set.questions},
            question_set.marking,
        )
        assert controller.result == expected
        controller.handle(Action.CONFIRM)
        assert controller.screen is UIScreen.REVIEW
        assert len(controller.review_items) == 20
        assert controller.review_items[0].response is not None
        before = repository.get_attempt_responses(attempt.id)
        controller.handle(Action.SELECT_D)
        controller.handle(Action.MARK_REVIEW)
        assert repository.get_attempt_responses(attempt.id) == before
        controller.handle(Action.BACK)
        controller.handle(Action.BACK)
        assert controller.screen is UIScreen.PROFILE
        assert repository.find_in_progress_attempt(controller.selected_profile.id) is None  # type: ignore[union-attr]


def test_controller_close_restart_resume_and_finish(tmp_path: Path) -> None:
    database_path = tmp_path / "ui-resume.db"
    with Repository(database_path) as repository:
        seed_pack(repository)
        controller = start_controller(repository)
        profile_id = controller.selected_profile.id  # type: ignore[union-attr]
        question_id = controller.application.current_question().id
        original_order = controller.application.engine.ordered_question_ids
        original_set = controller.application.engine.question_set
        assert original_set is not None
        controller.handle(Action.SELECT_C)
        controller.handle(Action.GUESSING)
        controller.handle(Action.MARK_REVIEW)
        controller.handle(Action.NEXT)
        pending_question_id = controller.application.current_question().id
        controller.handle(Action.SELECT_B)
        assert controller.screen is UIScreen.CONFIDENCE
        repository.import_question_set(
            replace(original_set, version=2, title="Newer local version"),
            content_hash="phase8-version-2",
            is_active=True,
        )
        controller.close()

    with Repository(database_path) as repository:
        controller = UIController(repository)
        assert controller.can_resume
        controller.handle(Action.CONFIRM)
        controller.handle(Action.CONFIRM)
        controller.handle(Action.CONFIRM)
        assert controller.screen is UIScreen.QUESTION
        assert controller.selected_profile.id == profile_id  # type: ignore[union-attr]
        assert controller.application.engine.question_set.version == 1  # type: ignore[union-attr]
        assert controller.application.engine.ordered_question_ids == original_order
        stored = repository.get_response(
            controller.application.engine.attempt.id, question_id  # type: ignore[union-attr]
        )
        assert stored is not None
        assert stored.selected_key == "C"
        assert stored.confidence is Confidence.GUESSING
        assert stored.marked_review
        pending = repository.get_response(
            controller.application.engine.attempt.id, pending_question_id  # type: ignore[union-attr]
        )
        assert pending is not None
        assert pending.selected_key == "B"
        assert pending.confidence is Confidence.UNRATED
        controller.handle(Action.SUBMIT)
        controller.handle(Action.SUBMIT)
        assert controller.screen is UIScreen.RESULT
        assert controller.result is not None

    with Repository(database_path) as repository:
        controller = UIController(repository)
        assert not controller.can_resume
