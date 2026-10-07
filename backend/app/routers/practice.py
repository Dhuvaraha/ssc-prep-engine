from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.domain.mastery import clamp_mastery, mastery_delta
from app.domain.models import AttemptOutcome, MasterySignal
from app.core.study_time import current_study_date
from app.domain.revision import next_revision_date
from app.models import Question, QuestionAttempt, RevisionItem, TopicMastery, User
from app.schemas import MistakeUpdate, PracticeResult, PracticeSubmit, QuestionOut
from app.services.planner import days_until_active_exam
from app.services.practice_selector import select_practice_questions

router = APIRouter(prefix="/practice", tags=["practice"])

PRACTICE_MODES = "^(guided|topic|timed|adaptive|pyq|mixed|weak|revision|speed|ladder)$"


@router.get("/questions", response_model=list[QuestionOut])
def get_practice_questions(
    topic_id: int | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
    mode: str = Query(default="adaptive", pattern=PRACTICE_MODES),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return select_practice_questions(
        db,
        user_id=user.id,
        topic_id=topic_id,
        limit=limit,
        mode=mode,
    )


@router.post("/submit", response_model=PracticeResult)
def submit_practice(
    payload: PracticeSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    question = db.get(Question, payload.question_id)
    if not question or question.verification_status != "verified":
        raise HTTPException(status_code=404, detail="Verified question not found")
    if question.correct_option is None:
        raise HTTPException(status_code=409, detail="Question answer key is not verified")

    is_correct = payload.selected_option == question.correct_option
    attempt = QuestionAttempt(
        user_id=user.id,
        question_id=question.id,
        selected_option=payload.selected_option,
        is_correct=is_correct,
        time_seconds=payload.time_seconds,
        confidence=payload.confidence,
        used_hint=payload.used_hint,
        mistake_type=payload.mistake_type,
    )
    db.add(attempt)
    db.flush()

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
    is_slow = bool(
        question.expected_time_seconds
        and payload.time_seconds > question.expected_time_seconds * 1.25
    )
    should_review = (
        (not is_correct)
        or payload.used_hint
        or payload.confidence == 1
        or is_slow
        or payload.mistake_type == "guess"
    )
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
                today=current_study_date(),
                successful_reviews=0,
                days_until_exam=days_until_active_exam(db, user_id=user.id),
            )
            db.add(
                RevisionItem(
                    user_id=user.id,
                    question_id=question.id,
                    reason=(
                        payload.mistake_type
                        or ("wrong" if not is_correct else "slow" if is_slow else "low_confidence")
                    ),
                    next_review_at=datetime.combine(due, datetime.min.time()),
                )
            )
        revision_scheduled = True

    db.commit()

    return PracticeResult(
        attempt_id=attempt.id,
        correct=is_correct,
        correct_option=question.correct_option,
        explanation=question.explanation,
        fast_method=question.fast_method,
        mastery_score=mastery_score,
        revision_scheduled=revision_scheduled,
    )


@router.patch("/attempts/{attempt_id}/mistake")
def classify_mistake(
    attempt_id: int,
    payload: MistakeUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed = {
        "concept",
        "formula",
        "calculation",
        "misread",
        "guess",
        "time_pressure",
        "unknown",
    }
    if payload.mistake_type not in allowed:
        raise HTTPException(status_code=400, detail="Invalid mistake type")

    attempt = db.get(QuestionAttempt, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=404, detail="Attempt not found")

    attempt.mistake_type = payload.mistake_type

    revision = db.scalar(
        select(RevisionItem).where(
            RevisionItem.user_id == user.id,
            RevisionItem.question_id == attempt.question_id,
            RevisionItem.is_active.is_(True),
        )
    )
    if revision:
        revision.reason = payload.mistake_type

    db.commit()
    return {"attempt_id": attempt.id, "mistake_type": attempt.mistake_type}
