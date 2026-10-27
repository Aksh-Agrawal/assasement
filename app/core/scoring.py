"""Pure scoring behavior defined by the Phase 0 scoring contract."""

from collections.abc import Mapping, Sequence

from app.core.models import Confidence, MarkingScheme, Question, Response, ScoreResult


def score_attempt(
    responses: Sequence[Response],
    questions_by_id: Mapping[str, Question],
    marking: MarkingScheme,
) -> ScoreResult:
    """Score final current responses against the complete question universe.

    Questions are evaluated by ``(position, id)`` so insight lists are stable;
    the ID is a deterministic fallback if invalid input contains duplicate
    positions. Missing responses and explicit responses with no selection are
    both skipped. Unknown question references and duplicate current responses
    fail explicitly.
    """
    for question_id, question in questions_by_id.items():
        if question_id != question.id:
            raise ValueError(
                f"Question mapping key {question_id!r} does not match question ID {question.id!r}"
            )

    responses_by_question: dict[str, Response] = {}
    for response in responses:
        question_id = response.question_id
        if question_id not in questions_by_id:
            raise ValueError(f"Unknown question_id {question_id!r}")
        if question_id in responses_by_question:
            raise ValueError(f"Duplicate response for question {question_id!r}")
        responses_by_question[question_id] = response

    confidence_totals = dict.fromkeys(Confidence, 0)
    confidence_correct = dict.fromkeys(Confidence, 0)
    confidence_wrong = dict.fromkeys(Confidence, 0)
    sure_but_wrong: list[str] = []
    guessed_right: list[str] = []
    correct = 0
    wrong = 0
    skipped = 0

    ordered_questions = sorted(
        questions_by_id.values(), key=lambda question: (question.position, question.id)
    )
    for question in ordered_questions:
        response = responses_by_question.get(question.id)
        if response is None or response.selected_key is None:
            skipped += 1
            continue

        confidence = response.confidence
        if confidence is None:
            raise ValueError(
                f"Attempted response for question {question.id!r} has no confidence value"
            )

        confidence_totals[confidence] += 1
        if response.selected_key == question.correct_key:
            correct += 1
            confidence_correct[confidence] += 1
            if confidence is Confidence.GUESSING:
                guessed_right.append(question.id)
        else:
            wrong += 1
            confidence_wrong[confidence] += 1
            if confidence is Confidence.SURE:
                sure_but_wrong.append(question.id)

    attempted = correct + wrong
    accuracy = correct / attempted if attempted else 0.0
    score = correct * marking.correct + wrong * marking.wrong + skipped * marking.skip

    return ScoreResult(
        score=score,
        correct=correct,
        wrong=wrong,
        skipped=skipped,
        attempted=attempted,
        accuracy=accuracy,
        confidence_totals=confidence_totals,
        confidence_correct=confidence_correct,
        confidence_wrong=confidence_wrong,
        sure_but_wrong_question_ids=tuple(sure_but_wrong),
        guessed_right_question_ids=tuple(guessed_right),
    )

