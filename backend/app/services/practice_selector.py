from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Question, QuestionAttempt, RevisionItem, TopicMastery


def _round_robin(groups: dict[object, list[Question]], limit: int) -> list[Question]:
    ordered = [items for _, items in sorted(groups.items(), key=lambda pair: str(pair[0])) if items]
    selected: list[Question] = []
    depth = 0
    while len(selected) < limit:
        added = False
        for items in ordered:
            if depth < len(items):
                selected.append(items[depth])
                added = True
                if len(selected) >= limit:
                    break
        if not added:
            break
        depth += 1
    return selected


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

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if mode == "revision":
        due_ids = list(
            db.scalars(
                select(RevisionItem.question_id)
                .where(
                    RevisionItem.user_id == user_id,
                    RevisionItem.is_active.is_(True),
                    RevisionItem.next_review_at <= now,
                )
                .order_by(RevisionItem.next_review_at, RevisionItem.id)
            )
        )
        if due_ids:
            by_id = {question.id: question for question in questions}
            due_questions = [by_id[qid] for qid in due_ids if qid in by_id]
            if due_questions:
                return due_questions[:limit]

    if mode == "guided":
        grouped: dict[str, list[Question]] = defaultdict(list)
        for question in questions:
            key = question.pattern_type or question.subtopic or f"question-{question.id}"
            grouped[key].append(question)
        for items in grouped.values():
            items.sort(key=lambda q: (q.difficulty, -(q.year or 0), q.id))
        return _round_robin(grouped, limit)

    if mode == "pyq":
        pyqs = [
            question for question in questions
            if question.year is not None or question.source_type in {"official", "licensed", "user_private"}
        ]
        if not pyqs:
            pyqs = questions
        pyqs.sort(key=lambda q: (-(q.year or 0), q.difficulty, q.id))
        return pyqs[:limit]

    if mode == "speed":
        return sorted(
            questions,
            key=lambda q: (
                q.expected_time_seconds or 999,
                q.difficulty,
                -(q.year or 0),
                q.id,
            ),
        )[:limit]

    if mode == "ladder":
        grouped_by_difficulty: dict[int, list[Question]] = defaultdict(list)
        for question in questions:
            grouped_by_difficulty[max(1, min(3, question.difficulty))].append(question)
        for items in grouped_by_difficulty.values():
            items.sort(key=lambda q: (-(q.year or 0), q.id))
        selected: list[Question] = []
        while len(selected) < limit:
            added = False
            for difficulty in (1, 2, 3):
                items = grouped_by_difficulty.get(difficulty, [])
                if items:
                    selected.append(items.pop(0))
                    added = True
                    if len(selected) >= limit:
                        break
            if not added:
                break
        return selected

    if mode in {"mixed", "topic"}:
        grouped_by_topic: dict[int, list[Question]] = defaultdict(list)
        for question in questions:
            grouped_by_topic[question.topic_id or -question.id].append(question)
        for items in grouped_by_topic.values():
            items.sort(key=lambda q: (q.difficulty, -(q.year or 0), q.id))
        return _round_robin(grouped_by_topic, limit)

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

    weak_topics: dict[int, float] = {}
    if mode == "weak" and topic_id is None:
        for mastery in db.scalars(
            select(TopicMastery).where(TopicMastery.user_id == user_id)
        ):
            weak_topics[mastery.topic_id] = float(mastery.mastery_score)

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

        if mode == "weak" and topic_id is None and question.topic_id is not None:
            mastery = weak_topics.get(question.topic_id)
            if mastery is None:
                score += 35.0
            else:
                score += max(0.0, 100.0 - mastery) * 0.8

        if question.year:
            score += max(0, question.year - 2020) * 1.5

        score -= max(0, question.difficulty - 3) * 2.0
        return (-score, question.id)

    return sorted(questions, key=priority)[:limit]
