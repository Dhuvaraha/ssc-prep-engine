from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_current_user
from app.domain.mastery import clamp_mastery, mastery_delta
from app.domain.models import AttemptOutcome, MasterySignal
from app.domain.revision import next_revision_date
from app.models import Question, QuestionAttempt, RevisionItem, TopicMastery, User
from app.schemas import PracticeResult, PracticeSubmit, QuestionOut

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/questions", response_model=list[QuestionOut])
def get_practice_questions(
    topic_id: int | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
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
def submit_practice(
    payload: PracticeSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    question = db.get(Question, payload.question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct = payload.selected_option == question.correct_option
    db.add(
        QuestionAttempt(
            user_id=user.id,
            question_id=question.id,
            selected_option=payload.selected_option,
            is_correct=is_correct,
            time_seconds=payload.time_seconds,
            confidence=payload.confidence,
            used_hint=payload.used_hint,
            mistake_type=payload.mistake_type,
        )
    )

    mastery_score = None
    if question.topic_id is not None:
        mastery = db.scalar(
            select(TopicMastery).where(
                TopicMastery.user_id == user.id,
                TopicMastery.topic_id == question.topic_id,
            )
        )
        if not mastery:
            mastery = TopicMastery(user_id=user.id, topic_id=question.topic_id)
            db.add(mastery)

        outcome = AttemptOutcome.CORRECT if is_correct else AttemptOutcome.INCORRECT
        delta = mastery_delta(
            MasterySignal(
                topic_id=str(question.topic_id),
                outcome=outcome,
                time_seconds=payload.time_seconds,
                expected_time_seconds=float(question.expected_time_seconds or max(payload.time_seconds, 1)),
                confidence=payload.confidence,
                used_hint=payload.used_hint,
            )
        )
        mastery.attempts += 1
        mastery.correct += int(is_correct)
        mastery.mastery_score = clamp_mastery(mastery.mastery_score + delta)
        mastery.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        mastery_score = mastery.mastery_score

    revision_scheduled = False
    should_review = (not is_correct) or payload.used_hint or payload.confidence == 1
    if should_review:
        existing = db.scalar(
            select(RevisionItem).where(
                RevisionItem.user_id == user.id,
                RevisionItem.question_id == question.id,
                RevisionItem.is_active.is_(True),
            )
        )
        if not existing:
            due = next_revision_date(
                today=datetime.now(timezone.utc).date(),
                successful_reviews=0,
                days_until_exam=10,
            )
            db.add(
                RevisionItem(
                    user_id=user.id,
                    question_id=question.id,
                    reason=payload.mistake_type or ("wrong" if not is_correct else "low_confidence"),
                    next_review_at=datetime.combine(due, datetime.min.time()),
                )
            )
        revision_scheduled = True

    db.commit()

    return PracticeResult(
        correct=is_correct,
        correct_option=question.correct_option,
        explanation=question.explanation,
        fast_method=question.fast_method,
        mastery_score=mastery_score,
        revision_scheduled=revision_scheduled,
    )
