"""Load the analytics screen from a bounded, read-only SQLite snapshot."""

import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from datetime import UTC, datetime

from app.core.exam_strategy import simulate
from app.core.reliability import LEVELS, summarize
from app.data.db import datetime_from_text


def timestamp(value):
    return datetime_from_text(value).astimezone(UTC).isoformat()


def history_metrics(items):
    correct = sum(item["correct"] for item in items)
    wrong = sum(item["wrong"] for item in items)
    graded = correct + wrong
    answered = sum(item["answered"] for item in items if item["responseTimeMs"] is not None)
    response_time = sum(item["responseTimeMs"] or 0 for item in items)
    confidence = {level: {"correct": 0, "wrong": 0} for level in LEVELS}
    for item in items:
        for level in LEVELS:
            counts = item["confidence"].get(level, {})
            for result in ("correct", "wrong"):
                confidence[level][result] += int(counts.get(result, 0))
    trends = []
    for index, item in enumerate(reversed(items)):
        count = item["correct"] + item["wrong"]
        trends.append({
            "index": index, "label": item["completedAt"],
            "accuracyPercent": round(item["correct"] * 100 / count) if count else -1,
            "correct": item["correct"], "wrong": item["wrong"],
        })
    return {
        "attempts": len(items), "correct": correct, "wrong": wrong,
        "skipped": sum(item["skipped"] for item in items),
        "accuracyPercent": round(correct * 100 / graded) if graded else -1,
        "practiceTimeMs": sum(item["durationMs"] for item in items),
        "averageResponseTimeMs": round(response_time / answered) if answered else -1,
        "webAttempts": sum(item["source"] == "web" for item in items),
        "deviceAttempts": sum(item["source"] == "device" for item in items),
        "confidence": confidence, "trends": trends,
    }


def evidence(identity, answer):
    selected, correct = answer.get("selected_key"), answer.get("is_correct")
    outcome = "skipped" if selected is None else (
        "ungraded" if correct is None else "correct" if correct else "wrong"
    )
    return {
        **identity, "topic": answer.get("topic"), "difficulty": answer.get("difficulty"),
        "question_type": answer.get("question_type"), "question_id": answer["question_id"],
        "response_id": answer.get("response_id"), "outcome": outcome,
        "confidence": answer.get("confidence"), "response_time_ms": answer.get("response_time_ms") or None,
        "marked_review": bool(answer.get("marked_review")),
    }


def local_history(connection, profile_id, window):
    attempts = connection.execute(
        """
        SELECT a.id AS attempt_id, a.set_id, a.set_version AS version, a.completed_at,
               a.duration_ms, a.sync_status, s.title, s.subject, s.chapter, s.marking_json,
               (SELECT count(*) FROM attempt_questions WHERE attempt_id = a.id) AS question_count
        FROM attempts a JOIN question_sets s ON s.id = a.set_id AND s.version = a.set_version
        WHERE a.profile_id = ? AND a.status = 'completed'
        ORDER BY a.completed_at DESC, a.id DESC LIMIT ?
        """, (profile_id, window),
    ).fetchall()
    if not attempts:
        return []
    placeholders = ",".join("?" for _ in attempts)
    responses = defaultdict(list)
    for row in connection.execute(
        f"""
        SELECT r.*, r.id AS response_id, q.topic, q.difficulty, q.options_json
        FROM responses r JOIN attempts a ON a.id = r.attempt_id
        LEFT JOIN questions q ON q.set_id = a.set_id AND q.set_version = a.set_version
                             AND q.id = r.question_id
        WHERE r.attempt_id IN ({placeholders})
        """, [attempt["attempt_id"] for attempt in attempts],
    ):
        answer = dict(row)
        options = answer.pop("options_json")
        answer["question_type"] = (None if options is None else
                                   "multiple_choice" if json.loads(options) else "numerical")
        responses[row["attempt_id"]].append(answer)
    return [(dict(attempt), responses[attempt["attempt_id"]]) for attempt in attempts]


def identity_for(attempt, source):
    return {
        "attempt_id": attempt["attempt_id"], "source": source,
        "completed_at": timestamp(attempt["completed_at"]), "set_id": attempt.get("set_id"),
        "version": attempt.get("version"), "subject": attempt.get("subject"),
        "chapter": attempt.get("chapter"),
    }


def history_entry(identity, title, marking, result, *, rows, missing):
    return {
        **identity,
        "title": title, "marking": marking,
        "metrics": {
            "completedAt": datetime.fromisoformat(identity["completed_at"]).astimezone().strftime("%d %b %Y"),
            "source": identity["source"],
            "correct": result.get("correct", 0), "wrong": result.get("wrong", 0),
            "skipped": result.get("skipped", 0), "durationMs": result.get("duration_ms", 0),
            "responseTimeMs": result.get("response_time_ms"),
            "answered": result.get("answered", result.get("correct", 0) + result.get("wrong", 0)),
            "confidence": result.get("confidence") or {},
        },
        "rows": rows, "limited": missing,
    }


def local_entry(attempt, responses):
    identity = identity_for(attempt, "device")
    rows = [evidence(identity, answer) for answer in responses]
    confidence = {level: {"correct": 0, "wrong": 0} for level in LEVELS}
    result = {
        "correct": 0, "wrong": 0, "answered": 0, "response_time_ms": 0,
        "duration_ms": attempt["duration_ms"], "confidence": confidence,
    }
    for row in rows:
        if row["outcome"] == "skipped":
            continue
        result["answered"] += 1
        result["response_time_ms"] += row["response_time_ms"] or 0
        if row["outcome"] in {"correct", "wrong"}:
            result[row["outcome"]] += 1
            confidence[row["confidence"] or "unrated"][row["outcome"]] += 1
    result["skipped"] = max(0, attempt["question_count"] - result["answered"])
    return history_entry(identity, attempt["title"], json.loads(attempt["marking_json"]), result,
                         rows=rows, missing=len(responses) < attempt["question_count"])


def remote_entry(attempt):
    identity = identity_for(attempt, attempt["source"])
    versioned = attempt.get("review_evidence_version") == 1
    # Older detail could include unreported questions from a full pack. Only
    # include rows that can establish a response from a legacy detail snapshot.
    rows = [evidence(identity, row) for row in attempt.get("review", [])
            if row.get("response_id") or (not versioned and row.get("selected_key") is not None)]
    return history_entry(identity, attempt["title"], attempt.get("marking"), attempt["result"],
                         rows=rows, missing=not versioned or not attempt.get("review_available"))


def read_cache(connection, name, profile_id):
    row = connection.execute("SELECT value FROM settings WHERE key=?", (name + ":" + profile_id,)).fetchone()
    return json.loads(row["value"]) if row else {}


def check_status(connection, profile_id, checks, profile, now):
    pack_ids = {item["pi_pack_id"] for item in checks if item.get("pi_pack_id")}
    completed, installed = set(), set()
    if pack_ids:
        placeholders = ",".join("?" for _ in pack_ids)
        completed = {row[0] for row in connection.execute(
            f"SELECT DISTINCT set_id FROM attempts WHERE profile_id = ? AND status = 'completed' "
            f"AND set_id IN ({placeholders})", [profile_id, *pack_ids],
        )}
        installed = {row[0] for row in connection.execute(
            f"""
            SELECT l.set_id FROM profile_library l
            JOIN question_sets q ON q.id = l.set_id AND q.version = l.version
            WHERE l.local_profile_id = ? AND l.eligible = 1 AND l.link_id = ?
            AND l.set_id IN ({placeholders})
            """, [profile_id, profile["link_id"], *pack_ids],
        )}
    for item in checks:
        pack = item.get("pi_pack_id")
        if pack:
            item["pending_completion"] = pack in completed
            item["can_open_pack"] = pack in installed and pack not in completed
        if item.get("due_at"):
            due = datetime_from_text(item["due_at"]).astimezone(now.tzinfo)
            item["local_due"] = due.strftime("%d %b")
            if item["status"] in {"due", "upcoming"}:
                item["local_status"] = ("Overdue" if due.date() < now.date() else
                                        "Due today" if due.date() == now.date() else "Upcoming")
    return checks


def load_intelligence(database, profile_id, window, marking=None, budget_ms=None):
    uri = database.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=3)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("BEGIN")
        profile = connection.execute(
            """
            SELECT p.cloud_profile_id, p.link_state, l.link_id
            FROM profiles p LEFT JOIN profile_link_context l ON l.local_profile_id = p.id
            WHERE p.id = ? AND p.deleted_at IS NULL
            """, (profile_id,),
        ).fetchone()
        if not profile:
            return {}
        local = local_history(connection, profile_id, window)
        items = {attempt["attempt_id"]: local_entry(attempt, responses) for attempt, responses in local}
        linked = profile["link_state"] == "linked" and bool(profile["link_id"])
        history = read_cache(connection, "completed_results", profile_id) if linked else {}
        if linked and history.get("study_profile_id") == profile["cloud_profile_id"]:
            # Local native evidence wins for matching UUIDs. Older cached
            # attempts cannot displace a native item that fell beyond the window.
            candidates = sorted(history.get("items", []),
                                key=lambda row: (timestamp(row["completed_at"]), row["attempt_id"]),
                                reverse=True)[:window]
            for attempt in candidates:
                if attempt["attempt_id"] not in items:
                    items[attempt["attempt_id"]] = remote_entry(attempt)
        items = sorted(items.values(), key=lambda row: (row["completed_at"], row["attempt_id"]),
                       reverse=True)[:window]
        rows = [row for item in items for row in item["rows"]]
        checks = read_cache(connection, "analytics_checks", profile_id) if linked else {}
        if checks.get("study_profile_id") != profile["cloud_profile_id"] or checks.get("link_id") != profile["link_id"]:
            checks = {}
        now = datetime.now().astimezone()
        targets = {kind: check_status(connection, profile_id, checks.get(kind, []), profile, now)
                   for kind in ("recovery", "retention")}
        ids = {item["attempt_id"] for item in items}
        for topic in targets["retention"]:
            topic["history"] = [event for event in topic["history"] if event["attempt_id"] in ids]
        pending = linked and any(attempt["sync_status"] != "synced" for attempt, _ in local)
    strategy = None
    newest = items[0] if items else None
    if newest and (marking or newest["marking"]):
        projection = [{key: item[key] for key in ("attempt_id", "completed_at", "title", "marking")}
                      for item in items]
        strategy = simulate(rows, projection[0], projection, marking=marking, budget_ms=budget_ms)
    return {
        "metrics": history_metrics([item["metrics"] for item in items]),
        "knowledge": summarize(rows), "strategy": strategy, **targets,
        "pending": pending, "limited": any(item["limited"] for item in items),
        "checks_cached": bool(checks), "checks_limited": bool(checks.get("limited")),
        "linked": linked,
    }
