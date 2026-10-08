from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import Question, QuestionAttempt, RevisionItem, TopicMastery
from app.services.question_quality import unique_questions
from app.services.learning_path import get_topic_learning_path


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


def _question_order():
    source_rank = case(
        (Question.source_type == "official", 0),
        (Question.source_type == "licensed", 1),
        (Question.source_type == "user_private", 1),
        (Question.source_type == "original", 2),
        else_=3,
    )
    missing_year = case((Question.year.is_(None), 1), else_=0)
    return (missing_year, Question.year.desc(), source_rank, Question.difficulty, Question.id)


def _hydrate_questions(db: Session, ids: list[int], *, exam_id: int | None = None) -> list[Question]:
    if not ids:
        return []
    stmt = select(Question).options(selectinload(Question.options)).where(Question.id.in_(ids))
    if exam_id is not None:
        stmt = stmt.where(Question.exam_id == exam_id)
    rows = list(db.scalars(stmt).unique())
    by_id = {question.id: question for question in rows}
    return [by_id[qid] for qid in ids if qid in by_id]


def _balanced_candidate_ids(db: Session, *, topic_id: int | None, limit: int, exam_id: int | None = None) -> list[int]:
    base = [
        Question.verification_status == "verified",
        Question.correct_option.is_not(None),
    ]
    if exam_id is not None:
        base.append(Question.exam_id == exam_id)

    if topic_id is not None:
        # Do not let a large first-easy block hide the medium/hard bank.
        # Preserve topic-specific pattern variety while sampling each level.
        ranked = (
            select(
                Question.id.label("qid"),
                func.row_number().over(
                    partition_by=Question.difficulty,
                    order_by=_question_order(),
                ).label("difficulty_rank"),
                Question.difficulty.label("difficulty"),
            )
            .where(*base, Question.topic_id == topic_id)
            .subquery()
        )
        per_level = max(40, limit * 4)
        return list(db.scalars(
            select(ranked.c.qid)
            .where(ranked.c.difficulty_rank <= per_level)
            .order_by(ranked.c.difficulty_rank, ranked.c.difficulty, ranked.c.qid)
            .limit(max(120, limit * 12))
        ))

    # Keep candidate hydration bounded, but include every difficulty even
    # when a large topic has hundreds of easy questions. Across many topics,
    # first sample one per topic+difficulty before taking second variants.
    ranked = (
        select(
            Question.id.label("question_id"),
            Question.topic_id.label("topic_id"),
            Question.difficulty.label("difficulty"),
            func.row_number().over(
                partition_by=(Question.topic_id, Question.difficulty),
                order_by=_question_order(),
            ).label("topic_rank"),
        )
        .where(*base)
        .subquery()
    )
    return list(db.scalars(
        select(ranked.c.question_id)
        .where(ranked.c.topic_rank <= max(4, min(limit, 10)))
        .order_by(ranked.c.topic_rank, ranked.c.topic_id, ranked.c.difficulty, ranked.c.question_id)
        .limit(max(320, limit * 24))
    ))


def _recent_attempt_ids(db: Session, *, user_id: int, limit: int, exam_id: int | None = None) -> list[int]:
    stmt = select(QuestionAttempt.question_id).where(QuestionAttempt.user_id == user_id)
    if exam_id is not None:
        stmt = stmt.join(Question, Question.id == QuestionAttempt.question_id).where(Question.exam_id == exam_id)
    raw = list(db.scalars(
        stmt.order_by(QuestionAttempt.attempted_at.desc(), QuestionAttempt.id.desc())
        .limit(max(100, limit * 12))
    ))
    # Preserve recency while removing repeated attempts of the same question.
    return list(dict.fromkeys(raw))


def _merge_ids(*groups: list[int]) -> list[int]:
    merged: list[int] = []
    seen: set[int] = set()
    for group in groups:
        for value in group:
            if value in seen:
                continue
            seen.add(value)
            merged.append(value)
    return merged


def select_practice_questions(
    db: Session,
    *,
    user_id: int,
    topic_id: int | None,
    limit: int,
    mode: str,
    similar_to_question_id: int | None = None,
    exam_id: int | None = None,
) -> list[Question]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    def hydrate(ids: list[int]) -> list[Question]:
        # Preserve the existing selector API and bounded-query test hooks.
        # Exam-bound requests still enforce the restriction at SQL level.
        if exam_id is None:
            return _hydrate_questions(db, ids)
        return _hydrate_questions(db, ids, exam_id=exam_id)

    if similar_to_question_id is not None:
        anchor = db.get(Question, similar_to_question_id)
        if anchor and anchor.verification_status == "verified" and anchor.topic_id is not None and (exam_id is None or anchor.exam_id == exam_id):
            similar_stmt = select(Question.id).where(
                Question.verification_status == "verified",
                Question.correct_option.is_not(None),
                Question.topic_id == anchor.topic_id,
                Question.id != anchor.id,
            )
            if anchor.pattern_type:
                similar_stmt = similar_stmt.where(Question.pattern_type == anchor.pattern_type)
            ids = list(
                db.scalars(
                    similar_stmt
                    .order_by(*_question_order())
                    .limit(max(40, limit * 8))
                )
            )
            similar = unique_questions(hydrate(ids))
            if similar:
                return similar[:limit]

            fallback_ids = list(
                db.scalars(
                    select(Question.id)
                    .where(
                        Question.verification_status == "verified",
                        Question.correct_option.is_not(None),
                        Question.topic_id == anchor.topic_id,
                        Question.id != anchor.id,
                    )
                    .order_by(*_question_order())
                    .limit(max(40, limit * 8))
                )
            )
            fallback = unique_questions(hydrate(fallback_ids))
            if fallback:
                return fallback[:limit]

    if mode == "revision":
        due_ids = list(
            db.scalars(
                select(RevisionItem.question_id)
                .join(Question, Question.id == RevisionItem.question_id)
                .where(
                    RevisionItem.user_id == user_id,
                    RevisionItem.is_active.is_(True),
                    RevisionItem.next_review_at <= now,
                    *([Question.exam_id == exam_id] if exam_id is not None else []),
                )
                .order_by(RevisionItem.next_review_at, RevisionItem.id)
                .limit(max(limit * 3, 30))
            )
        )
        due_questions = unique_questions(hydrate(due_ids))
        if topic_id is not None:
            due_questions = [question for question in due_questions if question.topic_id == topic_id]
        if due_questions:
            return due_questions[:limit]

    candidate_ids = _balanced_candidate_ids(db, topic_id=topic_id, limit=limit, exam_id=exam_id)
    if topic_id is None:
        candidate_ids = _merge_ids(
            _recent_attempt_ids(db, user_id=user_id, limit=limit, exam_id=exam_id),
            candidate_ids,
        )

    questions = unique_questions(hydrate(candidate_ids))
    if not questions:
        return []

    if mode == "path":
        if topic_id is None or exam_id is None:
            return []
        progress = get_topic_learning_path(
            db, user_id=user_id, topic_id=topic_id, exam_id=exam_id,
        )
        difficulty = progress["level"]
        at_level = [q for q in questions if q.difficulty == difficulty]
        recent = set(_recent_attempt_ids(db, user_id=user_id, limit=limit, exam_id=exam_id))
        # Novel questions first, with diverse pattern families inside a level.
        groups: dict[str, list[Question]] = defaultdict(list)
        for question in at_level:
            groups[question.pattern_type or question.subtopic or "other"].append(question)
        for group in groups.values():
            group.sort(key=lambda q: (q.id in recent, -(q.year or 0), q.id))
        ordered = _round_robin(groups, len(at_level))
        ordered.sort(key=lambda q: q.id in recent)
        return ordered[:limit]

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
        depth = 0
        while len(selected) < limit:
            added = False
            for difficulty in (1, 2, 3):
                items = grouped_by_difficulty.get(difficulty, [])
                if depth < len(items):
                    selected.append(items[depth])
                    added = True
                    if len(selected) >= limit:
                        break
            if not added:
                break
            depth += 1
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
            .order_by(QuestionAttempt.attempted_at.desc(), QuestionAttempt.id.desc())
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
