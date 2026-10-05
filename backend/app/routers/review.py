from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.content.topic_tagger import suggest_topic
from app.db import get_db
from app.deps import get_current_user
from app.models import Question, Subject, Topic, User

router = APIRouter(prefix="/review", tags=["content-review"])


class ReviewUpdate(BaseModel):
    topic_id: int | None = None
    subtopic: str | None = Field(default=None, max_length=160)
    pattern_type: str | None = Field(default=None, max_length=160)
    review_notes: str | None = None
    verification_status: str


@router.get("/questions")
def list_review_questions(
    status: str = Query(default="review_required"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    stmt = (
        select(Question)
        .options(selectinload(Question.options))
        .where(Question.verification_status == status)
        .order_by(Question.id)
        .limit(limit)
    )
    questions = list(db.scalars(stmt).unique())
    return [
        {
            "id": q.id,
            "subject_id": q.subject_id,
            "topic_id": q.topic_id,
            "subtopic": q.subtopic,
            "pattern_type": q.pattern_type,
            "question_text": q.question_text,
            "question_image_url": q.question_image_url,
            "options": [
                {"position": o.position, "text": o.text, "image_url": o.image_url}
                for o in q.options
            ],
            "correct_option": q.correct_option,
            "explanation": q.explanation,
            "fast_method": q.fast_method,
            "year": q.year,
            "shift": q.shift,
            "source_type": q.source_type,
            "source_reference": q.source_reference,
            "verification_status": q.verification_status,
            "review_notes": q.review_notes,
        }
        for q in questions
    ]


@router.post("/questions/{question_id}/suggest-topic")
def auto_tag_question(
    question_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    subject = db.get(Subject, question.subject_id)
    if not subject:
        raise HTTPException(status_code=400, detail="Question subject not found")

    topic_slug, confidence = suggest_topic(subject.slug, question.question_text)
    topic_id = None
    topic_name = None
    if topic_slug:
        topic = db.scalar(
            select(Topic).where(Topic.subject_id == subject.id, Topic.slug == topic_slug)
        )
        if topic:
            topic_id = topic.id
            topic_name = topic.name

    return {
        "topic_id": topic_id,
        "topic_slug": topic_slug,
        "topic_name": topic_name,
        "confidence": confidence,
    }


@router.patch("/questions/{question_id}")
def update_review_question(
    question_id: int,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    allowed = {"raw", "parsed", "review_required", "verified", "rejected"}
    if payload.verification_status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid verification status")

    if payload.topic_id is not None:
        topic = db.get(Topic, payload.topic_id)
        if not topic or topic.subject_id != question.subject_id:
            raise HTTPException(status_code=400, detail="Topic does not match question subject")

    question.topic_id = payload.topic_id
    question.subtopic = payload.subtopic
    question.pattern_type = payload.pattern_type
    question.review_notes = payload.review_notes
    question.verification_status = payload.verification_status
    db.commit()

    return {"id": question.id, "verification_status": question.verification_status}
