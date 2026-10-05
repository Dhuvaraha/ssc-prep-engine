from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Exam, MockAttempt, MockAttemptQuestion, Question, Subject


SECTION_ORDER = ["reasoning", "general-awareness", "quant", "english"]


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
        select(Question)
        .options(selectinload(Question.options))
        .where(
            Question.exam_id == exam_id,
            Question.subject_id == subject.id,
            Question.verification_status == "verified",
            Question.correct_option.is_not(None),
        )
        .order_by(
            Question.year.desc().nullslast(),
            Question.difficulty,
            Question.id,
        )
        .limit(count)
    )
    return list(db.scalars(stmt).unique())


def create_mock_attempt(
    db: Session,
    *,
    user_id: int,
    mode: str,
    subject_slug: str | None,
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
    else:
        plan = [(slug, 2) for slug in SECTION_ORDER]
        duration = 6

    selected: list[tuple[str, Question]] = []
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

    result: list[tuple[MockAttemptQuestion, Question]] = []
    for row in rows:
        question = db.scalar(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id == row.question_id)
        )
        if question:
            result.append((row, question))

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
