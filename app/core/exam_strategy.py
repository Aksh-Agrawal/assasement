"""Post-assessment scoring simulations with held-out historical calibration."""

from collections import Counter, defaultdict
from dataclasses import dataclass

from app.core.reliability import group_key

EXPLICIT_LEVELS = ("sure", "not_sure", "guessing")
STRATEGIES = ("attempt_all", "above_break_even", "skip_uncertain", "revisit")


@dataclass(frozen=True)
class CalibrationPolicy:
    minimum: int = 6
    prior_correct: int = 1
    prior_incorrect: int = 1


DEFAULT_POLICY = CalibrationPolicy()


def break_even(marks):
    correct, wrong, skip = (marks[key] for key in ("correct", "wrong", "skip"))
    if correct == wrong:
        return {"threshold": None, "rule": "tie" if correct == skip else
                "always_attempt" if correct > skip else "always_skip"}
    threshold = (skip - wrong) / (correct - wrong)
    if threshold < 0:
        return {"threshold": None, "rule": "always_attempt"}
    if threshold > 1:
        return {"threshold": None, "rule": "always_skip"}
    return {"threshold": threshold, "rule": "threshold"}


def expected_marks(marks, probability):
    return marks["correct"] * probability + marks["wrong"] * (1 - probability)


def calibration_keys(row):
    level = row.get("confidence")
    if level not in EXPLICIT_LEVELS:
        return
    if all(row.get(key) for key in ("subject", "chapter", "topic")):
        topic = group_key(row)
        if row.get("difficulty") is not None:
            yield ("topic_and_difficulty", level, topic, row["difficulty"])
        yield ("topic", level, topic)
    if row.get("subject"):
        yield ("subject", level, row["subject"].casefold())
    yield ("confidence", level)


def calibration_counts(rows):
    groups = defaultdict(Counter)
    for row in rows:
        if row["outcome"] in {"correct", "wrong"}:
            for key in calibration_keys(row):
                groups[key][row["outcome"]] += 1
    return groups


def estimate(count, policy):
    observations = count["correct"] + count["wrong"]
    probability = None
    if observations >= policy.minimum:
        probability = ((count["correct"] + policy.prior_correct)
                       / (observations + policy.prior_correct + policy.prior_incorrect))
    return {"observations": observations, "probability": probability, "correct": count["correct"]}


def estimate_row(row, groups, policy):
    for key in calibration_keys(row):
        view = estimate(groups.get(key, Counter()), policy)
        if view["probability"] is not None:
            return {"group": key[0], **view}
    return None


def simulate(rows, target, attempts, *, marking=None, by_type=None, exceptions=None, budget_ms=None,
             policy=DEFAULT_POLICY):
    identity = target["attempt_id"]
    ids = [item["attempt_id"] for item in attempts]
    # Attempts are in newest-to-oldest order. Equal completion timestamps cannot
    # establish that a calibration attempt preceded the target.
    older = {item["attempt_id"] for item in attempts[ids.index(identity) + 1:]
             if item["completed_at"] < target["completed_at"]}
    groups = calibration_counts(row for row in rows if row["attempt_id"] in older)
    current = [row for row in rows if row["attempt_id"] == identity]
    marks = marking or target["marking"]
    by_type = by_type or {}
    exceptions = exceptions or {}
    excluded = Counter()
    modelled = []
    for row in current:
        if row["outcome"] not in {"correct", "wrong"}:
            excluded[row["outcome"]] += 1
            continue
        predicted = estimate_row(row, groups, policy)
        if predicted is None:
            excluded["unrated" if row.get("confidence") not in EXPLICIT_LEVELS else "sparse"] += 1
            continue
        scheme = exceptions.get(row["question_id"], by_type.get(row.get("question_type"), marks))
        modelled.append({
            **row, **predicted, "expected": expected_marks(scheme, predicted["probability"]),
            "skip_marks": scheme["skip"],
        })

    comparisons = []
    for strategy in STRATEGIES:
        ordered = modelled
        if strategy == "revisit":
            ordered = sorted(modelled, key=lambda row: (
                row["marked_review"], row["difficulty"] is None,
                row["difficulty"] or 0, -row["probability"], row["question_id"],
            ))
        score = elapsed = attempted = missing_time = 0
        for row in ordered:
            attempt = True
            if strategy in {"above_break_even", "revisit"}:
                attempt = row["expected"] > row["skip_marks"]
            elif strategy == "skip_uncertain":
                attempt = row["confidence"] == "sure"
            time = row.get("response_time_ms")
            if strategy == "revisit" and budget_ms is not None:
                attempt = attempt and time is not None and elapsed + time <= budget_ms
            if attempt:
                score += row["expected"]
                elapsed += time or 0
                attempted += 1
                missing_time += time is None
            else:
                score += row["skip_marks"]
        comparisons.append({
            "strategy": strategy, "attempted": attempted, "skipped": len(modelled) - attempted,
            "expected_marks": round(score, 3) if modelled else None,
            "known_time_ms": elapsed, "missing_time": missing_time,
        })

    timing = defaultdict(list)
    for row in current:
        if row.get("difficulty") is not None and row.get("response_time_ms"):
            timing[row["difficulty"]].append(row["response_time_ms"])
    return {
        "schema_version": 1,
        "marking": marks,
        "break_even": break_even(marks),
        "type_rules": {key: {"marking": value, "break_even": break_even(value)}
                       for key, value in by_type.items()},
        "exception_count": len(exceptions),
        "calibration": {level: estimate(groups.get(("confidence", level), Counter()), policy)
                        for level in EXPLICIT_LEVELS},
        "minimum_sample": policy.minimum,
        "available_attempts": attempts,
        "selected_attempt_id": identity,
        "recorded_questions": len(current),
        "modelled_questions": len(modelled),
        "modelled_groups": dict(Counter(row["group"] for row in modelled)),
        "excluded": dict(excluded),
        "comparisons": comparisons,
        "difficulty_timing": [{"difficulty": level, "observations": len(times),
                               "average_ms": round(sum(times) / len(times))}
                              for level, times in sorted(timing.items())],
        "questions": [{"id": row["question_id"], "type": row.get("question_type")}
                      for row in current],
    }
