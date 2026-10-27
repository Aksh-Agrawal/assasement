"""Terminal engineering runner for the real offline assessment vertical slice."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, cast

from app.assessment import AssessmentApplication
from app.config import AppConfig
from app.core.engine import InvalidTransition, NavigationBoundary, ReviewItem
from app.core.models import (
    Confidence,
    MarkingScheme,
    Option,
    OptionKey,
    Profile,
    Question,
    QuestionSet,
    ScoreResult,
)
from app.data.repo import DuplicateQuestionSetVersion, Repository

DEVELOPMENT_PROFILE = Profile(
    id="550e8400-e29b-41d4-a716-446655440000",
    display_name="Development Student",
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(os.environ.get("ASSESSDEV_DATABASE", AppConfig().database_path)),
        help="development SQLite path (or set ASSESSDEV_DATABASE)",
    )
    parser.add_argument(
        "--seed-sample",
        action="store_true",
        help="explicitly add the development profile and sample Biology pack",
    )
    return parser.parse_args()


def _load_sample(path: Path) -> tuple[QuestionSet, str]:
    raw_bytes = path.read_bytes()
    data: dict[str, Any] = json.loads(raw_bytes)
    metadata = data["set"]
    marking = metadata["marking"]
    questions = tuple(
        Question(
            id=item["id"],
            position=item["position"],
            topic=item["topic"],
            difficulty=item["difficulty"],
            question_text=item["question_text"],
            options=tuple(
                Option(key=cast(OptionKey, option["key"]), text=option["text"])
                for option in item["options"]
            ),
            correct_key=cast(OptionKey, item["correct_key"]),
            explanation=item.get("explanation"),
            media_ref=item.get("media_ref"),
        )
        for item in data["questions"]
    )
    question_set = QuestionSet(
        id=metadata["id"],
        version=metadata["version"],
        title=metadata["title"],
        subject=metadata["subject"],
        chapter=metadata["chapter"],
        marking=MarkingScheme(
            correct=marking["correct"], wrong=marking["wrong"], skip=marking["skip"]
        ),
        questions=questions,
    )
    return question_set, hashlib.sha256(raw_bytes).hexdigest()


def seed_development_fixture(repository: Repository) -> None:
    """Idempotently install explicitly requested non-production fixtures."""
    if repository.get_profile(DEVELOPMENT_PROFILE.id) is None:
        repository.create_profile(DEVELOPMENT_PROFILE)
    question_set, content_hash = _load_sample(Path("content/sample_biology.json"))
    try:
        repository.import_question_set(
            question_set,
            content_hash=f"sha256:{content_hash}",
            is_active=True,
        )
    except DuplicateQuestionSetVersion:
        pass
    print("Development fixtures are available; existing data was not reset.")


def _choose(prompt: str, count: int) -> int:
    while True:
        value = input(prompt).strip()
        if value.isdigit() and 1 <= int(value) <= count:
            return int(value) - 1
        print(f"Enter a number from 1 to {count}.")


def _select_profile(repository: Repository) -> Profile | None:
    profiles = repository.list_profiles()
    if not profiles:
        print("No local profiles. Run with --seed-sample to add development fixtures.")
        return None
    print("\nLocal profiles:")
    for index, profile in enumerate(profiles, start=1):
        print(f"{index}. {profile.display_name}")
    return profiles[_choose("Select profile: ", len(profiles))]


def _start_or_resume(
    repository: Repository, app: AssessmentApplication, profile: Profile
) -> bool:
    active = repository.find_in_progress_attempt(profile.id)
    if active is not None:
        question_set = repository.get_question_set(active.set_id, active.set_version)
        responses = repository.get_attempt_responses(active.id)
        answered = sum(response.selected_key is not None for response in responses)
        title = question_set.title if question_set else active.set_id
        print(f"\nIncomplete assessment found: {title} ({answered} answered).")
        while True:
            choice = input("[R] Resume  [A] Abandon  [Q] Quit: ").strip().upper()
            if choice == "R":
                app.resume_attempt(profile.id)
                return True
            if choice == "A":
                app.resume_attempt(profile.id)
                app.abandon()
                print("Attempt marked abandoned; history was retained.")
                break
            if choice == "Q":
                return False

    question_sets = repository.list_question_sets()
    if not question_sets:
        print("No local question sets. Run with --seed-sample to add development fixtures.")
        return False
    print("\nInstalled question sets:")
    for index, question_set in enumerate(question_sets, start=1):
        print(
            f"{index}. {question_set.subject} — {question_set.title} "
            f"(v{question_set.version}, {len(question_set.questions)} questions)"
        )
    selected = question_sets[_choose("Select question set: ", len(question_sets))]
    app.start_test(profile.id, selected.id, selected.version)
    return True


def _format_time(milliseconds: int) -> str:
    seconds = milliseconds // 1000
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _show_question(app: AssessmentApplication) -> None:
    question = app.current_question()
    response = app.current_response()
    question_set = app.engine.question_set
    assert question_set is not None
    answer = response.selected_key if response and response.selected_key else "—"
    confidence = response.confidence.value if response and response.confidence else "—"
    marked = "Yes" if response and response.marked_review else "No"
    print(
        f"\n{question_set.subject} — {question_set.title}\n"
        f"Question {app.engine.current_index + 1} / {len(app.engine.ordered_question_ids)}\n\n"
        f"{question.question_text}\n"
    )
    for option in question.options:
        print(f"{option.key}. {option.text}")
    print(
        f"\nAnswer: {answer}  Confidence: {confidence}  Review: {marked}  "
        f"Time: {_format_time(app.current_time_ms())}\n"
        "A/B/C/D answer | N next | P previous | R review flag | S submit | Q quit"
    )


def _confidence_step(app: AssessmentApplication) -> None:
    print("\nHow confident are you?\n1. Sure\n2. Not Sure\n3. Guessing\n4. Unrated")
    mapping = {
        "1": Confidence.SURE,
        "2": Confidence.NOT_SURE,
        "3": Confidence.GUESSING,
    }
    while True:
        choice = input("Confidence: ").strip()
        if choice in mapping:
            app.set_confidence(mapping[choice])
            return
        if choice == "4":
            app.continue_unrated()
            return
        print("Enter 1, 2, 3, or 4.")


def _confirm_submit(app: AssessmentApplication) -> ScoreResult | None:
    responses = app.engine.responses()
    total = len(app.engine.ordered_question_ids)
    answered = sum(response.selected_key is not None for response in responses)
    marked = sum(response.marked_review for response in responses)
    app.request_submit()
    print(
        f"\nAnswered: {answered}\nUnanswered: {total - answered}\n"
        f"Marked for review: {marked}"
    )
    while True:
        choice = input("Submit assessment? [Y] Submit  [N] Continue: ").strip().upper()
        if choice == "Y":
            return app.submit()
        if choice == "N":
            app.cancel_submit()
            return None


def _assessment_loop(app: AssessmentApplication) -> ScoreResult | None:
    while True:
        _show_question(app)
        try:
            command = input("Command: ").strip().upper()
        except EOFError:
            command = "Q"
        try:
            if command in {"A", "B", "C", "D"}:
                app.select_answer(cast(OptionKey, command))
                _confidence_step(app)
            elif command == "N":
                if app.next_question() is None:
                    app.cancel_submit()
                    result = _confirm_submit(app)
                    if result is not None:
                        return result
            elif command == "P":
                app.previous_question()
            elif command == "R":
                response = app.current_response()
                app.set_marked_review(not (response and response.marked_review))
            elif command == "S":
                result = _confirm_submit(app)
                if result is not None:
                    return result
            elif command == "Q":
                app.pause()
                print("Attempt saved. You can resume later.")
                return None
            else:
                print("Unknown command.")
        except (InvalidTransition, NavigationBoundary) as error:
            print(error)


def _show_result(result: ScoreResult, maximum: int | float) -> None:
    print(
        f"\nTEST COMPLETE\nScore: {result.score} / {maximum}\n"
        f"Correct: {result.correct}\nWrong: {result.wrong}\nSkipped: {result.skipped}\n"
        f"Accuracy: {result.accuracy:.1%}\n\nConfidence:"
    )
    for confidence in Confidence:
        print(
            f"{confidence.value}: correct {result.confidence_correct[confidence]}, "
            f"wrong {result.confidence_wrong[confidence]}"
        )
    print(
        f"\nPriority Review:\nSure but wrong: {len(result.sure_but_wrong_question_ids)}\n"
        f"Guessed right: {len(result.guessed_right_question_ids)}"
    )


def _show_review_item(item: ReviewItem, total: int) -> None:
    response = item.response
    answer = response.selected_key if response and response.selected_key else "—"
    confidence = response.confidence.value if response and response.confidence else "—"
    duration = response.response_time_ms if response else 0
    marked = "Yes" if response and response.marked_review else "No"
    print(
        f"\nReview {item.position} / {total}\n{item.question.question_text}\n"
        f"Selected: {answer}\nCorrect: {item.question.correct_key}\n"
        f"Outcome: {item.outcome}\nConfidence: {confidence}\n"
        f"Time: {_format_time(duration)}\nMarked: {marked}"
    )
    if item.question.explanation:
        print(f"Explanation: {item.question.explanation}")


def _review_loop(app: AssessmentApplication) -> None:
    items = app.open_review()
    index = 0
    while True:
        _show_review_item(items[index], len(items))
        command = input("[N] Next  [P] Previous  [X] Exit review: ").strip().upper()
        if command == "N" and index < len(items) - 1:
            index += 1
        elif command == "P" and index > 0:
            index -= 1
        elif command == "X":
            app.close_review()
            return


def main() -> int:
    args = _arguments()
    with Repository(args.database) as repository:
        if args.seed_sample:
            seed_development_fixture(repository)
        profile = _select_profile(repository)
        if profile is None:
            return 1
        app = AssessmentApplication(repository)
        if not _start_or_resume(repository, app, profile):
            return 0
        result = _assessment_loop(app)
        if result is None:
            return 0
        question_set = app.engine.question_set
        assert question_set is not None
        maximum = len(question_set.questions) * question_set.marking.correct
        _show_result(result, maximum)
        if input("[V] Review answers  [X] Exit: ").strip().upper() == "V":
            _review_loop(app)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
