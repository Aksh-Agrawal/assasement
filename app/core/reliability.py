"""Question-level reliability contract shared by cloud and device (version 1)."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from unicodedata import normalize

LEVELS = ("sure", "not_sure", "guessing", "unrated")
QUADRANTS = ("confident_correct", "confident_wrong", "uncertain_correct", "uncertain_wrong")


@dataclass(frozen=True)
class ReliabilityPolicy:
    repeated_questions: int = 2
    repeated_attempts: int = 2
    minimum_graded: int = 3
    evidence_limit: int = 8


DEFAULT_POLICY = ReliabilityPolicy()


def normalized(value):
    return " ".join(normalize("NFKC", value).casefold().split())


def group_key(row):
    return tuple(normalized(row[key]) for key in ("subject", "chapter", "topic"))


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def quadrant_for(row):
    level, outcome = row.get("confidence"), row["outcome"]
    if level in LEVELS[:3] and outcome in {"correct", "wrong"}:
        return ("confident" if level == "sure" else "uncertain") + "_" + outcome
    return None


def topic_identity(row):
    """Keep missing metadata distinct from any real curriculum label."""
    return tuple(normalized(row.get(key) or "") for key in ("subject", "chapter", "topic"))


def unique_evidence(rows):
    seen = set()
    for row in sorted(rows, key=lambda row: (row["completed_at"], row["attempt_id"], row["question_id"]),
                      reverse=True):
        key = (row["attempt_id"], row["question_id"])
        if key not in seen:
            seen.add(key)
            yield row


def topic_breakdowns(rows, catalog=(), policy=DEFAULT_POLICY):
    """Aggregate the displayed attempt range, including known unassessed topics."""
    groups = {}
    for row in unique_evidence(rows):
        key = topic_identity(row)
        if key not in groups:
            groups[key] = (row, Breakdown(), set())
        _, counts, attempts = groups[key]
        counts.add(row)
        attempts.add(row["attempt_id"])
    for item in catalog:
        key = topic_identity(item)
        if key not in groups:
            groups[key] = (item, Breakdown(), set())
    return {
        key: {
            **{name: row.get(name) if part else None
               for name, part in zip(("subject", "chapter", "topic"), key, strict=True)},
            **counts.view(policy),
            "attempt_count": len(attempts),
            "last_practiced_at": row.get("completed_at"),
        }
        for key, (row, counts, attempts) in groups.items()
    }


@dataclass
class Breakdown:
    counts: Counter = field(default_factory=Counter)
    levels: dict = field(default_factory=lambda: {level: Counter() for level in LEVELS})
    wrong_attempts: set = field(default_factory=set)
    wrong_questions: set = field(default_factory=set)

    def add(self, row):
        outcome = row["outcome"]
        if outcome not in {"correct", "wrong"}:
            self.counts[outcome] += 1
            return
        level = row.get("confidence")
        if level not in LEVELS:
            level = "unrated"
        self.levels[level][outcome] += 1
        self.counts[outcome] += 1
        quadrant = quadrant_for(row)
        if quadrant:
            self.counts[quadrant] += 1
        if level == "sure" and outcome == "wrong":
            self.wrong_attempts.add(row["attempt_id"])
            self.wrong_questions.add((row["set_id"], row["question_id"]))

    def view(self, policy):
        quadrants = {key: self.counts[key] for key in QUADRANTS}
        rated = sum(quadrants.values())
        graded = self.counts["correct"] + self.counts["wrong"]
        sure = sum(self.levels["sure"].values())
        confident_wrong = quadrants["confident_wrong"]
        repeated = (graded >= policy.minimum_graded
                    and len(self.wrong_attempts) >= policy.repeated_attempts
                    and len(self.wrong_questions) >= policy.repeated_questions)
        return {
            "quadrants": quadrants,
            "percentages": {key: ratio(count, rated) for key, count in quadrants.items()},
            "rated": rated,
            "graded": graded,
            "unrated": graded - rated,
            "skipped": self.counts["skipped"],
            "ungraded": self.counts["ungraded"],
            "accuracy": ratio(self.counts["correct"], graded),
            "coverage": ratio(rated, graded),
            "high_confidence_error_rate": ratio(confident_wrong, sure),
            "confidence": {
                level: {"correct": counts["correct"], "wrong": counts["wrong"],
                        "accuracy": ratio(counts["correct"], sum(counts.values()))}
                for level, counts in self.levels.items()
            },
            "gap": ("repeated" if repeated else "possible") if confident_wrong else None,
            "confident_mistake_attempts": len(self.wrong_attempts),
        }


def summarize(rows, policy=DEFAULT_POLICY, *, include_topics=True):
    overall = Breakdown()
    topics = defaultdict(Breakdown)
    groups = defaultdict(dict)
    trend = defaultdict(Breakdown)
    attempts = {}
    labels = {}
    unique = list(unique_evidence(rows))
    for row in unique:
        overall.add(row)
        attempt = row["attempt_id"]
        trend[attempt].add(row)
        attempts[attempt] = row["completed_at"]
        if not include_topics or not all(row.get(field) for field in ("subject", "chapter", "topic")):
            continue
        key = group_key(row)
        labels.setdefault(key, {field: row[field] for field in ("subject", "chapter", "topic")})
        topics[key].add(row)
        groups[key].setdefault(attempt, Breakdown()).add(row)
    evidence = defaultdict(list)
    # Place confident mistakes first so a bounded list preserves actionable evidence.
    ordered = (sorted(unique, key=lambda row: quadrant_for(row) == "confident_wrong", reverse=True)
               if include_topics else ())
    for row in ordered:
        if not all(row.get(field) for field in ("subject", "chapter", "topic")):
            continue
        key = group_key(row)
        if len(evidence[key]) < policy.evidence_limit:
            evidence[key].append(row)
    topics = [
        {**labels[key], **value.view(policy), "evidence": evidence[key],
         "trend": [{"attempt_id": attempt, "completed_at": attempts[attempt], **item.view(policy)}
                   for attempt, item in reversed(list(groups[key].items()))][-3:]}
        for key, value in topics.items()
    ]
    topics.sort(key=lambda row: (row["gap"] != "repeated", row["gap"] is None, -row["graded"],
                                 row["subject"], row["chapter"], row["topic"]))
    return {
        "schema_version": 1,
        "overall": overall.view(policy),
        "topics": topics,
        "trend": [{"attempt_id": attempt, "completed_at": attempts[attempt], **value.view(policy)}
                  for attempt, value in reversed(list(trend.items()))],
    }
