from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Question
from app.schemas import PracticeResult, PracticeSubmit, QuestionOut

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/questions", response_model=list[QuestionOut])
def get_practice_questions(
    topic_id: int | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    stmt = (
        select(Question)
        .options(selectinload(Question.options))
        .where(Question.verification_status == "verified")
        .limit(limit)
    )
    if topic_id is not None:
        stmt = stmt.where(Question.topic_id == topic_id)
    return list(db.scalars(stmt).unique())


@router.post("/submit", response_model=PracticeResult)
def submit_practice(payload: PracticeSubmit, db: Session = Depends(get_db)):
    question = db.get(Question, payload.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = payload.selected_option == question.correct_option
    return PracticeResult(
        correct=is_correct,
        correct_option=question.correct_option,
        explanation=question.explanation,
        fast_method=question.fast_method,
    )
