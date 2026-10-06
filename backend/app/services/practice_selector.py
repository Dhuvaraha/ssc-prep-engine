from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Question, QuestionAttempt


def select_practice_questions(
    db: Session,
    *,
    user_id: int,
    topic_id: int | None,
    limit: int,
    mode: str,
) -> list[Question]:
    stmt = (
        select(Question)
        .options(selectinload(Question.options))
        .where(
            Question.verification_status == "verified",
            Question.correct_option.is_not(None),
        )
    )
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)

    questions = list(db.scalars(stmt).unique())
    if not questions:
        return []

    if mode == "guided":
        grouped: dict[str, list[Question]] = defaultdict(list)
        for question in questions:
            key = question.pattern_type or question.subtopic or f"question-{question.id}"
            grouped[key].append(question)

        for items in grouped.values():
            items.sort(
                key=lambda q: (
                    q.difficulty,
                    -(q.year or 0),
                    q.id,
                )
            )

        ordered_groups = sorted(
            grouped.values(),
            key=lambda items: (
                items[0].difficulty,
                items[0].pattern_type or "",
                items[0].id,
            ),
        )

        selected: list[Question] = []
        depth = 0
        while len(selected) < limit:
            added = False
            for items in ordered_groups:
                if depth < len(items):
                    selected.append(items[depth])
                    added = True
                    if len(selected) == limit:
                        break
            if not added:
                break
            depth += 1
        return selected

    if mode == "timed":
        return sorted(
            questions,
            key=lambda q: (
                q.difficulty,
                -(q.year or 0),
                q.id,
            ),
        )[:limit]

    ids = [question.id for question in questions]
    attempts = list(
        db.scalars(
            select(QuestionAttempt)
            .where(
                QuestionAttempt.user_id == user_id,
                QuestionAttempt.question_id.in_(ids),
            )
            .order_by(QuestionAttempt.attempted_at.desc())
        )
    )

    by_question: dict[int, list[QuestionAttempt]] = defaultdict(list)
    for attempt in attempts:
        by_question[attempt.question_id].append(attempt)

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def priority(question: Question) -> tuple[float, int]:
        history = by_question.get(question.id, [])
        score = 0.0

        if not history:
            score += 100.0
        else:
            latest = history[0]
            if latest.is_correct is False:
                score += 55.0
            if latest.confidence == 1:
                score += 24.0
            elif latest.confidence == 2:
                score += 10.0

            expected = float(question.expected_time_seconds or 45)
            if latest.time_seconds > expected * 1.35:
                score += 18.0

            days_since = max(0.0, (now - latest.attempted_at).total_seconds() / 86400)
            score += min(days_since, 14.0)

            recent_correct = sum(1 for item in history[:3] if item.is_correct)
            score -= recent_correct * 8.0

        if question.year:
            score += max(0, question.year - 2020) * 1.5

        score -= max(0, question.difficulty - 3) * 2.0
        return (-score, question.id)

    return sorted(questions, key=priority)[:limit]
