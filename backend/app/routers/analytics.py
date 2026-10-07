from collections import Counter, defaultdict
from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.study_time import current_study_date, utc_naive_to_study_date
from app.db import get_db
from app.deps import get_current_user
from app.models import MockAttempt, Question, QuestionAttempt, Subject, Topic, TopicMastery, User

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
    subject_stats: dict[int, dict[str, float]] = defaultdict(
        lambda: {"attempts": 0, "correct": 0, "time": 0}
    )
    daily_stats: dict[str, dict[str, float]] = defaultdict(
        lambda: {"attempts": 0, "correct": 0, "time": 0}
    )
    mistakes = Counter()
    confidence_counts = Counter()
    active_dates = set()

    question_cache: dict[int, Question | None] = {}
    for attempt in attempts:
        question = question_cache.get(attempt.question_id)
        if attempt.question_id not in question_cache:
            question = db.get(Question, attempt.question_id)
            question_cache[attempt.question_id] = question
        if not question:
            continue

        attempt_day = utc_naive_to_study_date(attempt.attempted_at)
        day_key = attempt_day.isoformat()
        active_dates.add(attempt_day)
        daily_stats[day_key]["attempts"] += 1
        daily_stats[day_key]["correct"] += int(attempt.is_correct is True)
        daily_stats[day_key]["time"] += attempt.time_seconds

        if attempt.mistake_type:
            mistakes[attempt.mistake_type] += 1

        if attempt.confidence == 3:
            confidence_counts["sure"] += 1
            confidence_counts["sure_correct"] += int(attempt.is_correct is True)
            confidence_counts["overconfident_errors"] += int(attempt.is_correct is False)
        elif attempt.confidence == 2:
            confidence_counts["unsure"] += 1
            confidence_counts["unsure_correct"] += int(attempt.is_correct is True)
        elif attempt.confidence == 1:
            confidence_counts["guess"] += 1
            confidence_counts["guess_correct"] += int(attempt.is_correct is True)

        if question.expected_time_seconds:
            timed_count += 1
            if attempt.time_seconds <= question.expected_time_seconds:
                within_target += 1

        if question.topic_id:
            row = topic_stats[question.topic_id]
            row["attempts"] += 1
            row["correct"] += int(attempt.is_correct is True)
            row["time"] += attempt.time_seconds

        row = subject_stats[question.subject_id]
        row["attempts"] += 1
        row["correct"] += int(attempt.is_correct is True)
        row["time"] += attempt.time_seconds

    speed_score = _pct(within_target, timed_count)

    masteries = list(
        db.scalars(select(TopicMastery).where(TopicMastery.user_id == user.id))
    )
    mastery_score = round(
        sum(item.mastery_score for item in masteries) / len(masteries),
        1,
    ) if masteries else 0.0

    topic_rows = []
    mastery_lookup = {item.topic_id: item.mastery_score for item in masteries}
    for topic_id, values in topic_stats.items():
        topic = db.get(Topic, topic_id)
        if not topic:
            continue
        topic_accuracy = _pct(values["correct"], values["attempts"])
        avg_time = round(values["time"] / values["attempts"], 1) if values["attempts"] else 0
        topic_rows.append(
            {
                "topic_id": topic_id,
                "topic_name": topic.name,
                "attempts": int(values["attempts"]),
                "accuracy": topic_accuracy,
                "avg_time_seconds": avg_time,
                "mastery": round(float(mastery_lookup.get(topic_id, 0.0)), 1),
            }
        )
    topic_rows.sort(key=lambda item: (item["mastery"], item["accuracy"], -item["attempts"]))

    subject_rows = []
    for subject_id, values in subject_stats.items():
        subject = db.get(Subject, subject_id)
        if not subject:
            continue
        subject_rows.append(
            {
                "subject_slug": subject.slug,
                "subject_name": subject.name,
                "attempts": int(values["attempts"]),
                "accuracy": _pct(values["correct"], values["attempts"]),
                "avg_time_seconds": round(values["time"] / values["attempts"], 1) if values["attempts"] else 0,
            }
        )
    subject_rows.sort(key=lambda item: item["subject_name"])

    now = current_study_date()
    trend = []
    for offset in range(13, -1, -1):
        day = now - timedelta(days=offset)
        values = daily_stats.get(day.isoformat(), {"attempts": 0, "correct": 0, "time": 0})
        trend.append(
            {
                "date": day.isoformat(),
                "attempts": int(values["attempts"]),
                "accuracy": _pct(values["correct"], values["attempts"]),
                "avg_time_seconds": round(values["time"] / values["attempts"], 1) if values["attempts"] else 0,
            }
        )

    streak = 0
    cursor = now
    while cursor in active_dates:
        streak += 1
        cursor -= timedelta(days=1)
    if streak == 0 and (now - timedelta(days=1)) in active_dates:
        cursor = now - timedelta(days=1)
        while cursor in active_dates:
            streak += 1
            cursor -= timedelta(days=1)

    mocks = list(
        db.scalars(
            select(MockAttempt)
            .where(
                MockAttempt.user_id == user.id,
                MockAttempt.status == "submitted",
            )
            .order_by(MockAttempt.submitted_at.desc())
            .limit(20)
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
        for item in mocks[:10]
    ]

    next_actions = []
    for topic in topic_rows[:3]:
        next_actions.append(
            {
                "type": "weak_topic",
                "title": f"Repair {topic['topic_name']}",
                "reason": f"Mastery {topic['mastery']}% • accuracy {topic['accuracy']}%",
                "topic_id": topic["topic_id"],
            }
        )
    if mistakes:
        top_error, count = mistakes.most_common(1)[0]
        next_actions.append(
            {
                "type": "error_pattern",
                "title": f"Reduce {top_error.replace('_', ' ')} errors",
                "reason": f"{count} classified attempt{'s' if count != 1 else ''}",
                "topic_id": None,
            }
        )

    return {
        "overview": {
            "practice_attempts": total_attempts,
            "accuracy": accuracy,
            "speed_score": speed_score,
            "mastery": mastery_score,
            "mock_accuracy": mock_accuracy,
            "mock_attempt_rate": mock_attempt_rate,
            "readiness": readiness,
            "streak": streak,
        },
        "errors": {
            "breakdown": dict(mistakes),
            "avoidable_errors": avoidable_errors,
            "potential_score_gain": potential_gain,
        },
        "confidence": {
            "sure_accuracy": _pct(confidence_counts["sure_correct"], confidence_counts["sure"]),
            "unsure_accuracy": _pct(confidence_counts["unsure_correct"], confidence_counts["unsure"]),
            "guess_accuracy": _pct(confidence_counts["guess_correct"], confidence_counts["guess"]),
            "guess_rate": _pct(confidence_counts["guess"], total_attempts),
            "overconfident_errors": confidence_counts["overconfident_errors"],
        },
        "subject_breakdown": subject_rows,
        "trend": trend,
        "weak_topics": topic_rows[:8],
        "next_actions": next_actions,
        "recent_mocks": recent_mocks,
    }
