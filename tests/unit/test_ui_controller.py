"""Canonical Action to controller-command routing without a graphical window."""

from unittest.mock import Mock

from app.core.models import MarkingScheme, Option, Profile, Question, QuestionSet
from app.input.actions import Action
from app.ui.controller import UIController, UIScreen


def question_set() -> QuestionSet:
    return QuestionSet(
        id="biology-ui-unit-01",
        version=1,
        title="UI unit set",
        subject="Biology",
        chapter="Testing",
        marking=MarkingScheme(),
        questions=(
            Question(
                id="bio-ui-unit-q0001",
                position=1,
                topic="Testing",
                difficulty=1,
                question_text="A question?",
                options=tuple(Option(key=key, text=key) for key in ("A", "B", "C", "D")),
                correct_key="A",
            ),
        ),
    )


def make_controller() -> tuple[UIController, Mock]:
    profile = Profile(id="550e8400-e29b-41d4-a716-446655440000", display_name="Student")
    repository = Mock()
    repository.list_profiles.return_value = (profile,)
    repository.list_question_sets.return_value = (question_set(),)
    repository.find_in_progress_attempt.return_value = None
    application = Mock()
    application.next_question.return_value = application.current_question.return_value
    application.current_response.return_value = None
    application.engine.responses.return_value = ()
    application.engine.ordered_question_ids = ("bio-ui-unit-q0001",)
    controller = UIController(repository, application_factory=lambda _repo: application)
    return controller, application


def route_to_question(controller: UIController) -> None:
    controller.handle(Action.CONFIRM)
    assert controller.screen is UIScreen.SUBJECT
    controller.handle(Action.CONFIRM)
    assert controller.screen is UIScreen.QUESTION_SET
    controller.handle(Action.CONFIRM)
    assert controller.screen is UIScreen.QUESTION


def test_profile_subject_and_question_set_routes_are_distinct() -> None:
    controller, _application = make_controller()
    assert controller.screen is UIScreen.PROFILE
    assert controller.selected_subject == "Biology"
    route_to_question(controller)


def test_answer_and_confidence_actions_route_to_application() -> None:
    controller, application = make_controller()
    route_to_question(controller)
    application.start_test.assert_called_once()

    controller.handle(Action.SELECT_A)
    application.select_answer.assert_called_once_with("A")
    assert controller.screen is UIScreen.CONFIDENCE

    controller.handle(Action.SURE)
    application.set_confidence.assert_called_once()
    assert controller.screen is UIScreen.QUESTION


def test_navigation_review_and_submit_cancel_actions_route_to_application() -> None:
    controller, application = make_controller()
    route_to_question(controller)
    controller.handle(Action.NEXT)
    application.next_question.assert_called_once()
    controller.handle(Action.PREV)
    application.previous_question.assert_called_once()
    controller.handle(Action.MARK_REVIEW)
    application.set_marked_review.assert_called_once_with(True)

    controller.handle(Action.SUBMIT)
    assert controller.screen is UIScreen.SUBMIT_CONFIRM
    controller.handle(Action.BACK)
    application.cancel_submit.assert_called_once()
    assert controller.screen is UIScreen.QUESTION


def test_submit_result_review_and_resume_transitions() -> None:
    controller, application = make_controller()
    controller.repository.find_in_progress_attempt.return_value = object()
    route_to_question(controller)
    application.resume_attempt.assert_called_once()
    controller.handle(Action.SUBMIT)
    application.submit.return_value = Mock()
    controller.handle(Action.CONFIRM)
    assert controller.screen is UIScreen.RESULT
    application.open_review.return_value = (Mock(),)
    controller.handle(Action.CONFIRM)
    assert controller.screen is UIScreen.REVIEW
    controller.handle(Action.BACK)
    application.close_review.assert_called_once()
    assert controller.screen is UIScreen.RESULT


def test_all_answer_and_confidence_actions_use_the_same_application_boundary() -> None:
    for action, answer in (
        (Action.SELECT_A, "A"),
        (Action.SELECT_B, "B"),
        (Action.SELECT_C, "C"),
        (Action.SELECT_D, "D"),
    ):
        controller, application = make_controller()
        route_to_question(controller)
        controller.handle(action)
        application.select_answer.assert_called_once_with(answer)

    for action in (Action.SURE, Action.NOT_SURE, Action.GUESSING):
        controller, application = make_controller()
        route_to_question(controller)
        controller.handle(Action.SELECT_A)
        controller.handle(action)
        application.set_confidence.assert_called_once()

    controller, application = make_controller()
    route_to_question(controller)
    controller.handle(Action.SELECT_A)
    controller.handle(Action.CONFIRM)
    application.continue_unrated.assert_called_once()


def test_menu_and_back_routes_do_not_bypass_safe_pause() -> None:
    controller, application = make_controller()
    route_to_question(controller)
    controller.handle(Action.MENU)
    application.pause.assert_called_once()
    assert controller.screen is UIScreen.PROFILE
