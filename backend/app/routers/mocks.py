from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import MockAttemptQuestion, User
from app.schemas import (
    MockQuestionOut,
    MockResponseUpdate,
    MockStartRequest,
    MockStartResponse,
    MockSubmitResponse,
)
from app.services.mock_engine import create_mock_attempt, load_mock_attempt, submit_mock_attempt

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
    try:
        attempt, rows = create_mock_attempt(
            db,
            user_id=user.id,
            mode=payload.mode,
            subject_slug=payload.subject_slug,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize_attempt(attempt, rows)


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

    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "started_at": attempt.started_at.isoformat(),
        "duration_minutes": attempt.duration_minutes,
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
    return submit_mock_attempt(db, attempt=attempt, rows=rows)
