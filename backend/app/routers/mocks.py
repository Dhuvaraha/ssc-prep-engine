from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Exam, MockAttempt, User
from app.schemas import (
    MockQuestionOut,
    MockResponseUpdate,
    MockStartRequest,
    MockStartResponse,
    MockSubmitResponse,
)
from app.services.mock_engine import create_mock_attempt, load_mock_attempt, mock_timing, submit_mock_attempt

router = APIRouter(prefix="/mocks", tags=["mocks"])


def _serialize_attempt(attempt, rows):
    return MockStartResponse(
        attempt_id=attempt.id,
        mode=attempt.mode,
        duration_minutes=attempt.duration_minutes,
        questions=[
            MockQuestionOut(
                position=row.position,
                section_slug=row.section_slug,
                question=question,
            )
            for row, question in rows
        ],
    )


@router.post("/start", response_model=MockStartResponse)
def start_mock(
    payload: MockStartRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    active = db.scalar(
        select(MockAttempt)
        .where(MockAttempt.user_id == user.id, MockAttempt.status == "in_progress")
        .order_by(MockAttempt.started_at.desc())
    )
    if active:
        try:
            active_attempt, rows = load_mock_attempt(db, attempt_id=active.id, user_id=user.id)
            return _serialize_attempt(active_attempt, rows)
        except LookupError:
            pass

    try:
        attempt, rows = create_mock_attempt(
            db,
            user_id=user.id,
            mode=payload.mode,
            subject_slug=payload.subject_slug,
            topic_id=payload.topic_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize_attempt(attempt, rows)


@router.get("/active/current")
def active_mock(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = db.scalar(
        select(MockAttempt)
        .where(MockAttempt.user_id == user.id, MockAttempt.status == "in_progress")
        .order_by(MockAttempt.started_at.desc())
    )
    if not attempt:
        return {"attempt_id": None}
    timing = mock_timing(attempt)
    return {
        "attempt_id": attempt.id,
        "mode": attempt.mode,
        "subject_slug": attempt.subject_slug,
        **timing,
    }


@router.get("/{attempt_id}", response_model=MockStartResponse)
def get_mock(
    attempt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        attempt, rows = load_mock_attempt(db, attempt_id=attempt_id, user_id=user.id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Mock attempt not found")
    return _serialize_attempt(attempt, rows)


@router.patch("/{attempt_id}/response")
def save_mock_response(
    attempt_id: int,
    payload: MockResponseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        attempt, rows = load_mock_attempt(db, attempt_id=attempt_id, user_id=user.id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Mock attempt not found")

    if attempt.status == "submitted":
        raise HTTPException(status_code=409, detail="Mock already submitted")

    target = next((row for row, _ in rows if row.question_id == payload.question_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Question not part of this mock")

    timing = mock_timing(attempt)
    if timing["seconds_left"] <= 0:
        raise HTTPException(status_code=409, detail="Test time is over. Submit the test.")
    if attempt.mode == "full" and target.section_slug != timing["active_section_slug"]:
        active = timing["active_section_slug"] or "next section"
        raise HTTPException(
            status_code=409,
            detail=f"This section is locked. Continue with {active}.",
        )

    target.selected_option = payload.selected_option
    target.marked_for_review = payload.marked_for_review
    target.time_seconds = payload.time_seconds
    db.commit()

    return {
        "question_id": target.question_id,
        "selected_option": target.selected_option,
        "marked_for_review": target.marked_for_review,
        "time_seconds": target.time_seconds,
    }


@router.get("/{attempt_id}/state")
def get_mock_state(
    attempt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        attempt, rows = load_mock_attempt(db, attempt_id=attempt_id, user_id=user.id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Mock attempt not found")

    timing = mock_timing(attempt)
    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "started_at": attempt.started_at.isoformat(),
        "duration_minutes": attempt.duration_minutes,
        **timing,
        "responses": [
            {
                "question_id": row.question_id,
                "selected_option": row.selected_option,
                "marked_for_review": row.marked_for_review,
                "time_seconds": row.time_seconds,
            }
            for row, _ in rows
        ],
    }


@router.get("/{attempt_id}/review")
def review_mock(
    attempt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        attempt, rows = load_mock_attempt(db, attempt_id=attempt_id, user_id=user.id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Mock attempt not found")
    if attempt.status != "submitted":
        raise HTTPException(status_code=409, detail="Submit the mock before reviewing it")

    sections: dict[str, dict[str, float | int]] = {}
    questions = []
    easy_missed = 0
    slow_questions = 0
    missed_patterns = Counter()

    for row, question in rows:
        correct = row.selected_option == question.correct_option if row.selected_option is not None else False
        attempted = row.selected_option is not None
        section = sections.setdefault(
            row.section_slug,
            {"correct": 0, "incorrect": 0, "unattempted": 0, "time_seconds": 0.0},
        )
        if not attempted:
            section["unattempted"] += 1
        elif correct:
            section["correct"] += 1
        else:
            section["incorrect"] += 1
        section["time_seconds"] += float(row.time_seconds or 0)

        if question.difficulty == 1 and not correct:
            easy_missed += 1
        if attempted and not correct and question.pattern_type:
            missed_patterns[question.pattern_type] += 1
        if question.expected_time_seconds and row.time_seconds > question.expected_time_seconds * 1.25:
            slow_questions += 1

        questions.append(
            {
                "position": row.position,
                "section_slug": row.section_slug,
                "question_id": question.id,
                "question_text": question.question_text,
                "selected_option": row.selected_option,
                "correct_option": question.correct_option,
                "correct": correct,
                "marked_for_review": row.marked_for_review,
                "time_seconds": round(float(row.time_seconds or 0), 1),
                "expected_time_seconds": question.expected_time_seconds,
                "difficulty": question.difficulty,
                "pattern_type": question.pattern_type,
                "explanation": question.explanation,
                "fast_method": question.fast_method,
            }
        )

    exam = db.get(Exam, attempt.exam_id)
    positive = float(exam.positive_marks if exam else 2.0)
    negative = float(exam.negative_marks if exam else 0.5)
    for section in sections.values():
        section["score"] = round(
            float(section["correct"]) * positive - float(section["incorrect"]) * negative,
            2,
        )
        attempted_count = int(section["correct"]) + int(section["incorrect"])
        section["accuracy"] = round(
            float(section["correct"]) * 100 / attempted_count,
            1,
        ) if attempted_count else 0.0

    return {
        "attempt_id": attempt.id,
        "sections": sections,
        "easy_missed": easy_missed,
        "slow_questions": slow_questions,
        "weak_patterns": [
            {"pattern": pattern, "missed": count}
            for pattern, count in missed_patterns.most_common(5)
        ],
        "questions": questions,
    }


@router.delete("/{attempt_id}")
def abandon_mock(
    attempt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = db.get(MockAttempt, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Mock attempt not found")
    if attempt.status == "submitted":
        raise HTTPException(status_code=409, detail="Submitted mock cannot be abandoned")
    attempt.status = "abandoned"
    db.commit()
    return {"attempt_id": attempt.id, "status": attempt.status}


@router.post("/{attempt_id}/submit", response_model=MockSubmitResponse)
def submit_mock(
    attempt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        attempt, rows = load_mock_attempt(db, attempt_id=attempt_id, user_id=user.id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Mock attempt not found")

    timing = mock_timing(attempt)
    if (
        attempt.mode == "full"
        and timing["seconds_left"] > 0
        and timing["section_index"] is not None
        and timing["section_index"] < len(("reasoning", "general-awareness", "quant", "english")) - 1
    ):
        raise HTTPException(
            status_code=409,
            detail="Full Tier-I simulation can be submitted only in the final section or after time expires.",
        )
    return submit_mock_attempt(db, attempt=attempt, rows=rows)
