"""Execute every normative Phase 0 scoring vector through core scoring."""

import json
from pathlib import Path
from typing import Any

import pytest

from app.core.models import Confidence, MarkingScheme, Option, Question, Response
from app.core.scoring import score_attempt

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "scoring_vectors.json"
FIXTURE_DOCUMENT = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
VECTORS = FIXTURE_DOCUMENT["vectors"]


def _question(question_id: str, position: int, correct_key: str) -> Question:
    options = tuple(
        Option(key=key, text=f"Option {key}") for key in ("A", "B", "C", "D")
    )
    return Question(
        id=question_id,
        position=position,
        topic="Scoring fixture",
        difficulty=1,
        question_text=f"Fixture question {question_id}",
        options=options,
        correct_key=correct_key,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize("vector", VECTORS, ids=[vector["id"] for vector in VECTORS])
def test_phase_zero_scoring_vector(vector: dict[str, Any]) -> None:
    questions: dict[str, Question] = {}
    responses: list[Response] = []
    for position, fixture_response in enumerate(vector["responses"], start=1):
        question_id = fixture_response["question_id"]
        questions[question_id] = _question(
            question_id,
            position,
            fixture_response["correct_key"],
        )
        selected_key = fixture_response["selected_key"]
        confidence_value = fixture_response["confidence"]
        responses.append(
            Response(
                id=f"{vector['id']}-response-{position}",
                attempt_id=f"{vector['id']}-attempt",
                question_id=question_id,
                selected_key=selected_key,
                confidence=Confidence(confidence_value) if confidence_value is not None else None,
            )
        )

    marking = MarkingScheme(**vector["marking"])
    result = score_attempt(responses, questions, marking)
    expected = vector["expected"]

    assert result.score == expected["score"]
    assert result.correct == expected["correct"]
    assert result.wrong == expected["wrong"]
    assert result.skipped == expected["skipped"]
    assert result.attempted == expected["attempted"]
    assert result.accuracy == pytest.approx(expected["accuracy"])

    for bucket_name, bucket_expected in expected["confidence"].items():
        bucket = Confidence(bucket_name)
        assert result.confidence_totals[bucket] == bucket_expected["responses"]
        assert result.confidence_correct[bucket] == bucket_expected["correct"]
        assert result.confidence_wrong[bucket] == bucket_expected["wrong"]

    assert len(result.sure_but_wrong_question_ids) == expected["sure_but_wrong"]
    assert len(result.guessed_right_question_ids) == expected["guessed_right"]
