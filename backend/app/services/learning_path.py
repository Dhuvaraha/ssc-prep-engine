"""Evidence-gated topic learning stages — not an exam readiness predictor.

Repeat attempts at the same question don't qualify as independent mastery.
Only verified, distinct practice responses without hints/guesses unlock the
next level. Timed speed and delayed recall remain separate readiness signals.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Question, QuestionAttempt


STAGES = {
    1: ("Foundation", "Understand the rule and recognise the question pattern."),
    2: ("Application", "Apply the method to unfamiliar, medium-level questions."),
    3: ("Challenge", "Solve advanced variations and explain traps."),
}


def get_topic_learning_path(
    db: Session, *, user_id: int, topic_id: int, exam_id: int,
) -> dict:
    # Most recent independent question attempts only, bounded per learner/topic.
    rows = db.execute(
        select(QuestionAttempt, Question).options(selectinload(Question.options))
        .join(Question, Question.id == QuestionAttempt.question_id)
        .where(
            QuestionAttempt.user_id == user_id,
            Question.exam_id == exam_id,
        )
        .order_by(QuestionAttempt.attempted_at.desc(), QuestionAttempt.id.desc())
    ).all()
    from app.services.revision_history import attempt_views
    views = attempt_views(db, [a for a,q in rows], {q.id:q for a,q in rows})
    rows = [(a, views[a.id].difficulty) for a,q in rows if views.get(a.id) and
            views[a.id].topic_id == topic_id and views[a.id].verification_status == 'verified'][:240]

    per_level: dict[int, list[QuestionAttempt]] = {1: [], 2: [], 3: []}
    seen: set[int] = set()
    for attempt, raw_difficulty in rows:
        difficulty = int(raw_difficulty or 2)
        if difficulty not in per_level or attempt.question_id in seen:
            continue
        seen.add(attempt.question_id)
        if len(per_level[difficulty]) < 8:
            per_level[difficulty].append(attempt)

    details = {}
    for difficulty in (1, 2, 3):
        attempts = per_level[difficulty]
        independent_correct = sum(
            attempt.is_correct is True
            and not attempt.used_hint
            and (attempt.confidence or 1) >= 2
            for attempt in attempts
        )
        passed = (
            len(attempts) >= 5
            and independent_correct >= 4
            and independent_correct / len(attempts) >= .75
        )
        details[difficulty] = {
            "distinct_attempts": len(attempts),
            "independent_correct": independent_correct,
            "passed": passed,
        }

    level = 1
    if details[1]["passed"]:
        level = 2
    if level == 2 and details[2]["passed"]:
        level = 3

    availability = {
        int(difficulty): int(count)
        for difficulty, count in db.execute(
            select(Question.difficulty, func.count(Question.id))
            .where(
                Question.topic_id == topic_id,
                Question.exam_id == exam_id,
                Question.verification_status == "verified",
                Question.correct_option.is_not(None),
            )
            .group_by(Question.difficulty)
        )
    }
    content_blocked = False
    blocked_level = None
    if availability.get(level, 0) < 5:
        # Do not advertise a level that cannot even provide five distinct
        # qualifying questions. The bank needs editorial expansion first.
        content_blocked = True
        blocked_level = level
        level = max(1, level - 1)

    label, description = STAGES[level]
    return {
        "topic_id": topic_id,
        "exam_id": exam_id,
        "level": level,
        "stage": label,
        "description": description,
        "levels": details,
        "available_questions": availability,
        "content_blocked": content_blocked,
        "blocked_level": blocked_level,
        "next_unlock": (
            "The next difficulty needs at least five distinct verified questions. "
            "Continue related topics or revision while this level is expanded."
            if content_blocked else
            "Complete 5 different questions at this level with at least 4 independently correct and 75% accuracy. "
            "Hints and guesses help you learn, but do not count as independent passes."
            if level < 3 else
            "Continue advanced work, spaced revision and timed tests. Reaching this level is not full exam mastery."
        ),
    }
