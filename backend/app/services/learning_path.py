"""Evidence-gated topic learning stages — not an exam readiness predictor.

Repeat attempts at the same question don't qualify as independent mastery.
Only verified, distinct practice responses without hints/guesses unlock the
next level. Timed speed and delayed recall remain separate readiness signals.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

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
        select(QuestionAttempt, Question.difficulty)
        .join(Question, Question.id == QuestionAttempt.question_id)
        .where(
            QuestionAttempt.user_id == user_id,
            Question.topic_id == topic_id,
            Question.exam_id == exam_id,
            Question.verification_status == "verified",
        )
        .order_by(QuestionAttempt.attempted_at.desc(), QuestionAttempt.id.desc())
        .limit(240)
    ).all()

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

    label, description = STAGES[level]
    return {
        "topic_id": topic_id,
        "exam_id": exam_id,
        "level": level,
        "stage": label,
        "description": description,
        "levels": details,
        "next_unlock": (
            "Complete 5 different questions at this level with at least 4 independently correct and 75% accuracy. "
            "Hints and guesses help you learn, but do not count as independent passes."
            if level < 3 else
            "Continue advanced work, spaced revision and timed tests. Reaching this level is not full exam mastery."
        ),
    }
