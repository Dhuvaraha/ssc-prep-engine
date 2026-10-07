from datetime import datetime, timezone

from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from app.models import Exam, MockAttempt, MockAttemptQuestion, Question, Subject, Topic
from app.services.question_quality import unique_questions


SECTION_ORDER = ["reasoning", "general-awareness", "quant", "english"]
FULL_SECTION_SECONDS = 15 * 60
FULL_TOTAL_SECONDS = len(SECTION_ORDER) * FULL_SECTION_SECONDS


def mock_timing(attempt: MockAttempt, *, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    elapsed = max(0, int((now - attempt.started_at).total_seconds()))
    total_seconds = attempt.duration_minutes * 60
    seconds_left = max(0, total_seconds - elapsed)

    if attempt.mode != "full":
        return {
            "seconds_left": seconds_left,
            "active_section_slug": None,
            "section_index": None,
            "section_seconds_left": None,
            "section_duration_seconds": None,
        }

    if elapsed >= FULL_TOTAL_SECONDS:
        return {
            "seconds_left": 0,
            "active_section_slug": None,
            "section_index": None,
            "section_seconds_left": 0,
            "section_duration_seconds": FULL_SECTION_SECONDS,
        }

    section_index = min(elapsed // FULL_SECTION_SECONDS, len(SECTION_ORDER) - 1)
    section_elapsed = elapsed - section_index * FULL_SECTION_SECONDS
    return {
        "seconds_left": max(0, FULL_TOTAL_SECONDS - elapsed),
        "active_section_slug": SECTION_ORDER[section_index],
        "section_index": section_index,
        "section_seconds_left": max(0, FULL_SECTION_SECONDS - section_elapsed),
        "section_duration_seconds": FULL_SECTION_SECONDS,
    }


def _question_order():
    source_rank = case(
        (Question.source_type == "official", 0),
        (Question.source_type == "licensed", 1),
        (Question.source_type == "user_private", 1),
        (Question.source_type == "original", 2),
        else_=3,
    )
    missing_year = case((Question.year.is_(None), 1), else_=0)
    return (source_rank, missing_year, Question.year.desc(), Question.difficulty, Question.id)


def _hydrate_questions(db: Session, ids: list[int]) -> list[Question]:
    if not ids:
        return []
    questions = list(
        db.scalars(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id.in_(ids))
        ).unique()
    )
    by_id = {question.id: question for question in questions}
    return [by_id[qid] for qid in ids if qid in by_id]


def _bounded_unique_questions(db: Session, stmt, *, count: int) -> list[Question]:
    """
    Fetch a bounded candidate window first, then hydrate only those option rows.

    Full/section mocks used to hydrate an entire subject bank to choose 25
    questions. Production subjects can contain thousands of rows, so this keeps
    mock startup proportional to the requested test size while preserving the
    exact duplicate-content guard.
    """
    for candidate_limit in (max(80, count * 6), max(200, count * 20)):
        ids = list(db.scalars(stmt.limit(candidate_limit)))
        selected = unique_questions(_hydrate_questions(db, ids))
        if len(selected) >= count:
            return selected[:count]

    # Safety fallback for an unusually duplicate-heavy subject/topic.
    ids = list(db.scalars(stmt))
    return unique_questions(_hydrate_questions(db, ids))[:count]


def _difficulty_targets(count: int) -> dict[int, int]:
    if count <= 1:
        return {2: count}
    easy = max(1, round(count * 0.28))
    medium = max(1, round(count * 0.48))
    hard = max(1, count - easy - medium)
    while easy + medium + hard > count:
        if medium > 1:
            medium -= 1
        elif easy > 1:
            easy -= 1
        else:
            hard -= 1
    while easy + medium + hard < count:
        medium += 1
    return {1: easy, 2: medium, 3: hard}


def _balanced_difficulty_questions(db: Session, stmt, *, count: int) -> list[Question]:
    targets = _difficulty_targets(count)
    selected: list[Question] = []
    selected_ids: set[int] = set()

    for difficulty in (1, 2, 3):
        target = targets.get(difficulty, 0)
        if target <= 0:
            continue
        rows = _bounded_unique_questions(
            db,
            stmt.where(Question.difficulty == difficulty),
            count=target,
        )
        for question in rows:
            if question.id not in selected_ids:
                selected.append(question)
                selected_ids.add(question.id)

    selected = unique_questions(selected)
    if len(selected) < count:
        fallback_stmt = stmt
        if selected_ids:
            fallback_stmt = fallback_stmt.where(Question.id.not_in(selected_ids))
        fallback = _bounded_unique_questions(
            db,
            fallback_stmt,
            count=count - len(selected),
        )
        selected = unique_questions(selected + fallback)

    groups = {
        difficulty: [q for q in selected if max(1, min(3, q.difficulty)) == difficulty]
        for difficulty in (1, 2, 3)
    }
    mixed: list[Question] = []
    depth = 0
    while len(mixed) < min(count, len(selected)):
        added = False
        for difficulty in (2, 1, 2, 3):
            items = groups.get(difficulty, [])
            index = depth if difficulty != 2 else sum(
                1 for q in mixed if max(1, min(3, q.difficulty)) == 2
            )
            if index < len(items) and items[index] not in mixed:
                mixed.append(items[index])
                added = True
                if len(mixed) >= count:
                    break
        if not added:
            for question in selected:
                if question not in mixed:
                    mixed.append(question)
                    added = True
                    if len(mixed) >= count:
                        break
        if not added:
            break
        depth += 1
    return mixed[:count]


def _questions_for_subject(
    db: Session,
    *,
    exam_id: int,
    subject_slug: str,
    count: int,
) -> list[Question]:
    subject = db.scalar(
        select(Subject).where(
            Subject.exam_id == exam_id,
            Subject.slug == subject_slug,
        )
    )
    if not subject:
        return []

    stmt = (
        select(Question.id)
        .where(
            Question.exam_id == exam_id,
            Question.subject_id == subject.id,
            Question.verification_status == "verified",
            Question.correct_option.is_not(None),
        )
        .order_by(*_question_order())
    )
    return _balanced_difficulty_questions(db, stmt, count=count)


def _questions_for_topic(
    db: Session,
    *,
    exam_id: int,
    topic_id: int,
    count: int,
) -> tuple[str, list[Question]]:
    topic = db.get(Topic, topic_id)
    if not topic:
        return "", []
    subject = db.get(Subject, topic.subject_id)
    if not subject or subject.exam_id != exam_id:
        return "", []

    stmt = (
        select(Question.id)
        .where(
            Question.exam_id == exam_id,
            Question.topic_id == topic_id,
            Question.verification_status == "verified",
            Question.correct_option.is_not(None),
        )
        .order_by(*_question_order())
    )
    return subject.slug, _bounded_unique_questions(db, stmt, count=count)


def create_mock_attempt(
    db: Session,
    *,
    user_id: int,
    mode: str,
    subject_slug: str | None,
    topic_id: int | None = None,
) -> tuple[MockAttempt, list[tuple[MockAttemptQuestion, Question]]]:
    exam = db.scalar(select(Exam).where(Exam.slug == "ssc-cgl-tier-1"))
    if not exam:
        raise ValueError("SSC CGL exam is not seeded")

    if mode == "full":
        plan = [(slug, 25) for slug in SECTION_ORDER]
        duration = 60
    elif mode == "sectional":
        if subject_slug not in SECTION_ORDER:
            raise ValueError("A valid subject is required for sectional mode")
        plan = [(subject_slug, 25)]
        duration = 15
    elif mode == "topic":
        if not topic_id:
            raise ValueError("A topic is required for topic-test mode")
        plan = []
        duration = 20
    else:
        plan = [(slug, 1) for slug in SECTION_ORDER]
        duration = 4

    selected: list[tuple[str, Question]] = []
    if mode == "topic":
        slug, questions = _questions_for_topic(
            db,
            exam_id=exam.id,
            topic_id=topic_id,
            count=20,
        )
        if len(questions) < 10:
            raise ValueError(f"Not enough verified questions for topic {topic_id}: need at least 10")
        selected.extend((slug, question) for question in questions)
    else:
        for slug, count in plan:
            questions = _questions_for_subject(
                db,
                exam_id=exam.id,
                subject_slug=slug,
                count=count,
            )
            if len(questions) < count:
                raise ValueError(
                    f"Not enough verified questions for {slug}: need {count}, found {len(questions)}"
                )
            selected.extend((slug, question) for question in questions)

    attempt = MockAttempt(
        user_id=user_id,
        exam_id=exam.id,
        mode=mode,
        subject_slug=subject_slug,
        duration_minutes=duration,
    )
    db.add(attempt)
    db.flush()

    rows: list[tuple[MockAttemptQuestion, Question]] = []
    for position, (slug, question) in enumerate(selected, start=1):
        row = MockAttemptQuestion(
            attempt_id=attempt.id,
            question_id=question.id,
            section_slug=slug,
            position=position,
        )
        db.add(row)
        rows.append((row, question))

    db.commit()
    return attempt, rows


def load_mock_attempt(
    db: Session,
    *,
    attempt_id: int,
    user_id: int,
) -> tuple[MockAttempt, list[tuple[MockAttemptQuestion, Question]]]:
    attempt = db.get(MockAttempt, attempt_id)
    if not attempt or attempt.user_id != user_id:
        raise LookupError("Mock attempt not found")

    rows = list(
        db.scalars(
            select(MockAttemptQuestion)
            .where(MockAttemptQuestion.attempt_id == attempt.id)
            .order_by(MockAttemptQuestion.position)
        )
    )
    question_ids = [row.question_id for row in rows]
    questions = _hydrate_questions(db, question_ids)
    by_id = {question.id: question for question in questions}

    result = [
        (row, by_id[row.question_id])
        for row in rows
        if row.question_id in by_id
    ]
    return attempt, result


def submit_mock_attempt(
    db: Session,
    *,
    attempt: MockAttempt,
    rows: list[tuple[MockAttemptQuestion, Question]],
) -> dict:
    if attempt.status == "submitted":
        return {
            "attempt_id": attempt.id,
            "score": float(attempt.score or 0),
            "correct": attempt.correct_count,
            "incorrect": attempt.incorrect_count,
            "unattempted": attempt.unattempted_count,
            "total_questions": len(rows),
        }

    correct = 0
    incorrect = 0
    unattempted = 0

    for row, question in rows:
        if row.selected_option is None:
            unattempted += 1
        elif row.selected_option == question.correct_option:
            correct += 1
        else:
            incorrect += 1

    exam = db.get(Exam, attempt.exam_id)
    positive = float(exam.positive_marks if exam else 2.0)
    negative = float(exam.negative_marks if exam else 0.5)
    score = round(correct * positive - incorrect * negative, 2)

    attempt.status = "submitted"
    attempt.submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    attempt.score = score
    attempt.correct_count = correct
    attempt.incorrect_count = incorrect
    attempt.unattempted_count = unattempted
    db.commit()

    return {
        "attempt_id": attempt.id,
        "score": score,
        "correct": correct,
        "incorrect": incorrect,
        "unattempted": unattempted,
        "total_questions": len(rows),
    }
