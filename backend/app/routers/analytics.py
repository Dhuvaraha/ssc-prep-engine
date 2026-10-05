from collections import Counter, defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import MockAttempt, Question, QuestionAttempt, Topic, TopicMastery, User

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _pct(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100, 1)


@router.get("/summary")
def analytics_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempts = list(
        db.scalars(
            select(QuestionAttempt)
            .where(QuestionAttempt.user_id == user.id)
            .order_by(QuestionAttempt.attempted_at.desc())
        )
    )

    total_attempts = len(attempts)
    correct = sum(1 for item in attempts if item.is_correct is True)
    incorrect = sum(1 for item in attempts if item.is_correct is False)
    accuracy = _pct(correct, correct + incorrect)

    timed_count = 0
    within_target = 0
    topic_stats: dict[int, dict[str, float]] = defaultdict(
        lambda: {"attempts": 0, "correct": 0, "time": 0}
    )
    mistakes = Counter()

    for attempt in attempts:
        question = db.get(Question, attempt.question_id)
        if not question:
            continue

        if attempt.mistake_type:
            mistakes[attempt.mistake_type] += 1

        if question.expected_time_seconds:
            timed_count += 1
            if attempt.time_seconds <= question.expected_time_seconds:
                within_target += 1

        if question.topic_id:
            row = topic_stats[question.topic_id]
            row["attempts"] += 1
            row["correct"] += int(attempt.is_correct is True)
            row["time"] += attempt.time_seconds

    speed_score = _pct(within_target, timed_count)

    masteries = list(
        db.scalars(
            select(TopicMastery).where(TopicMastery.user_id == user.id)
        )
    )
    mastery_score = round(
        sum(item.mastery_score for item in masteries) / len(masteries),
        1,
    ) if masteries else 0.0

    topic_rows = []
    for topic_id, values in topic_stats.items():
        topic = db.get(Topic, topic_id)
        if not topic:
            continue
        topic_accuracy = _pct(values["correct"], values["attempts"])
        avg_time = round(values["time"] / values["attempts"], 1) if values["attempts"] else 0
        mastery = next((item.mastery_score for item in masteries if item.topic_id == topic_id), 0.0)
        topic_rows.append(
            {
                "topic_id": topic_id,
                "topic_name": topic.name,
                "attempts": int(values["attempts"]),
                "accuracy": topic_accuracy,
                "avg_time_seconds": avg_time,
                "mastery": round(float(mastery), 1),
            }
        )
    topic_rows.sort(key=lambda item: (item["mastery"], item["accuracy"], -item["attempts"]))

    mocks = list(
        db.scalars(
            select(MockAttempt)
            .where(
                MockAttempt.user_id == user.id,
                MockAttempt.status == "submitted",
            )
            .order_by(MockAttempt.submitted_at.desc())
            .limit(10)
        )
    )

    mock_attempted = sum(item.correct_count + item.incorrect_count for item in mocks)
    mock_correct = sum(item.correct_count for item in mocks)
    mock_total = sum(
        item.correct_count + item.incorrect_count + item.unattempted_count
        for item in mocks
    )
    mock_accuracy = _pct(mock_correct, mock_attempted)
    mock_attempt_rate = _pct(mock_attempted, mock_total)

    readiness = round(
        0.35 * accuracy
        + 0.25 * mastery_score
        + 0.20 * speed_score
        + 0.20 * mock_accuracy,
        1,
    )

    avoidable_types = {"calculation", "misread", "guess", "time_pressure"}
    avoidable_errors = sum(count for key, count in mistakes.items() if key in avoidable_types)
    potential_gain = round(avoidable_errors * 2.5, 1)

    recent_mocks = [
        {
            "attempt_id": item.id,
            "mode": item.mode,
            "score": float(item.score or 0),
            "correct": item.correct_count,
            "incorrect": item.incorrect_count,
            "unattempted": item.unattempted_count,
            "submitted_at": item.submitted_at.isoformat() if item.submitted_at else None,
        }
        for item in mocks[:5]
    ]

    return {
        "overview": {
            "practice_attempts": total_attempts,
            "accuracy": accuracy,
            "speed_score": speed_score,
            "mastery": mastery_score,
            "mock_accuracy": mock_accuracy,
            "mock_attempt_rate": mock_attempt_rate,
            "readiness": readiness,
        },
        "errors": {
            "breakdown": dict(mistakes),
            "avoidable_errors": avoidable_errors,
            "potential_score_gain": potential_gain,
        },
        "weak_topics": topic_rows[:8],
        "recent_mocks": recent_mocks,
    }
