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
    question_ids = {item.question_id for item in attempts}
    question_cache = {
        item.id: item
        for item in db.scalars(
            select(Question).where(Question.id.in_(question_ids))
        )
    } if question_ids else {}

    correct = sum(1 for item in attempts if item.is_correct is True)
    incorrect = sum(1 for item in attempts if item.is_correct is False)
    accuracy = _pct(correct, correct + incorrect)

    timed_count = 0
    within_target = 0
    time_over_target_seconds = 0.0
    slow_attempts = 0
    first_attempts = 0
    first_correct = 0
    repeat_attempts = 0
    repeat_correct = 0
    seen_question_ids: set[int] = set()
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

    for attempt in sorted(attempts, key=lambda item: (item.attempted_at, item.id)):
        question = question_cache.get(attempt.question_id)
        if not question:
            continue

        if attempt.question_id in seen_question_ids:
            repeat_attempts += 1
            repeat_correct += int(attempt.is_correct is True)
        else:
            seen_question_ids.add(attempt.question_id)
            first_attempts += 1
            first_correct += int(attempt.is_correct is True)

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
            else:
                slow_attempts += 1
                time_over_target_seconds += max(
                    0.0,
                    float(attempt.time_seconds) - float(question.expected_time_seconds),
                )

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
    first_attempt_accuracy = _pct(first_correct, first_attempts)
    repeat_attempt_accuracy = _pct(repeat_correct, repeat_attempts)
    repeat_gain = round(repeat_attempt_accuracy - first_attempt_accuracy, 1) if repeat_attempts else 0.0

    masteries = list(
        db.scalars(select(TopicMastery).where(TopicMastery.user_id == user.id))
    )
    mastery_score = round(
        sum(item.mastery_score for item in masteries) / len(masteries),
        1,
    ) if masteries else 0.0

    topic_rows = []
    mastery_lookup = {item.topic_id: item.mastery_score for item in masteries}
    topic_ids = set(topic_stats)
    topic_lookup = {
        item.id: item
        for item in db.scalars(select(Topic).where(Topic.id.in_(topic_ids)))
    } if topic_ids else {}
    for topic_id, values in topic_stats.items():
        topic = topic_lookup.get(topic_id)
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
    subject_ids = set(subject_stats)
    subject_lookup = {
        item.id: item
        for item in db.scalars(select(Subject).where(Subject.id.in_(subject_ids)))
    } if subject_ids else {}
    for subject_id, values in subject_stats.items():
        subject = subject_lookup.get(subject_id)
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

    # Practice signals describe sampled skills, not a whole-exam score.
    # A Quick Sprint or a sectional test must never unlock a numeric
    # 100-question SSC Tier-I readiness estimate.
    full_mocks = [
        item for item in mocks
        if item.mode == "full"
        and item.correct_count + item.incorrect_count + item.unattempted_count >= 100
        and item.correct_count + item.incorrect_count >= 50
    ]
    readiness_source = "full_mock" if full_mocks else "not_assessed"
    if full_mocks:
        full_attempted = sum(item.correct_count + item.incorrect_count for item in full_mocks)
        full_accuracy = _pct(sum(item.correct_count for item in full_mocks), full_attempted)
        # An actual full mock is a cross-section baseline. Practice/micro-drills
        # only influence the blended estimate when enough timed evidence exists.
        readiness = full_accuracy
        if total_attempts >= 40 and timed_count >= 20 and len(topic_stats) >= 4:
            readiness = round(
                0.45 * full_accuracy
                + 0.25 * accuracy
                + 0.15 * mastery_score
                + 0.15 * speed_score,
                1,
            )
    else:
        readiness = None

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

    if total_attempts == 0 and not mocks:
        evidence_level = "baseline"
        coach = {
            "evidence_level": evidence_level,
            "headline": "Build your exam baseline first.",
            "summary": "No performance history yet. Start with a Quick Sprint, then solve one guided topic set so the planner can learn from real evidence.",
            "primary_action": {
                "title": "Take a Quick Sprint",
                "reason": "Get one signal from every Tier-I section without pretending this is a full mock.",
                "path": "/mocks",
            },
            "secondary_action": {
                "title": "Start guided practice",
                "reason": "A short guided set begins topic-level accuracy, speed and confidence tracking.",
                "path": "/learn",
            },
        }
    elif total_attempts < 40 or not mocks:
        evidence_level = "developing"
        focus = topic_rows[0] if topic_rows else None
        coach = {
            "evidence_level": evidence_level,
            "headline": "Your baseline is forming — keep the signal clean.",
            "summary": (
                f"You have {total_attempts} practice attempts. "
                + ("Add a timed section or mock so readiness includes exam-pressure evidence." if not mocks else "Use another focused set before treating any one topic as a stable weakness.")
            ),
            "primary_action": {
                "title": f"Strengthen {focus['topic_name']}" if focus else "Build more topic evidence",
                "reason": (
                    f"{focus['attempts']} attempts • {focus['accuracy']}% accuracy. This is still an early signal."
                    if focus else
                    "Complete a guided topic set so the coach has enough evidence to rank weaknesses."
                ),
                "path": (
                    f"/practice?topic_id={focus['topic_id']}&mode=guided&limit=10"
                    if focus else
                    "/learn"
                ),
            },
            "secondary_action": {
                "title": "Add timed evidence",
                "reason": "Sectional or full-test results make readiness and pacing advice more reliable.",
                "path": "/mocks",
            },
        }
    else:
        evidence_level = "established"
        focus = topic_rows[0] if topic_rows else None
        top_error = mistakes.most_common(1)[0] if mistakes else None
        if focus:
            primary_title = f"Repair {focus['topic_name']}"
            primary_reason = (
                f"{focus['attempts']} attempts • {focus['accuracy']}% accuracy • "
                f"{focus['mastery']}% mastery."
            )
            primary_path = f"/practice?topic_id={focus['topic_id']}&mode=adaptive&limit=10"
        else:
            primary_title = "Protect your strongest sections"
            primary_reason = "Use mixed timed practice to keep accuracy and speed stable."
            primary_path = "/practice?mode=mixed&limit=10"

        coach = {
            "evidence_level": evidence_level,
            "headline": "Turn your data into the next marks gain.",
            "summary": (
                (
                    f"Provisional full-mock readiness is {readiness}%. "
                    if readiness is not None
                    else "Full-exam readiness has not been assessed. "
                )
                + f"Correcting classified avoidable errors could recover about {potential_gain} marks."
            ),
            "primary_action": {
                "title": primary_title,
                "reason": primary_reason,
                "path": primary_path,
            },
            "secondary_action": {
                "title": (
                    f"Reduce {top_error[0].replace('_', ' ')} errors"
                    if top_error else
                    "Take another timed test"
                ),
                "reason": (
                    f"{top_error[1]} classified miss{'es' if top_error[1] != 1 else ''} use this error pattern."
                    if top_error else
                    "Refresh exam-pressure evidence and compare section pacing."
                ),
                "path": "/revision" if top_error else "/mocks",
            },
        }

    return {
        "overview": {
            "practice_attempts": total_attempts,
            "accuracy": accuracy,
            "speed_score": speed_score,
            "mastery": mastery_score,
            "mock_accuracy": mock_accuracy,
            "mock_attempt_rate": mock_attempt_rate,
            "readiness": readiness,
            "readiness_source": readiness_source,
            "full_mock_count": len(full_mocks),
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
        "learning_curve": {
            "first_attempts": first_attempts,
            "first_attempt_accuracy": first_attempt_accuracy,
            "repeat_attempts": repeat_attempts,
            "repeat_attempt_accuracy": repeat_attempt_accuracy,
            "repeat_gain": repeat_gain,
            "slow_attempts": slow_attempts,
            "time_over_target_seconds": round(time_over_target_seconds, 1),
        },
        "subject_breakdown": subject_rows,
        "trend": trend,
        "weak_topics": topic_rows[:8],
        "next_actions": next_actions,
        "recent_mocks": recent_mocks,
        "coach": coach,
    }
