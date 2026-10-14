from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, StrictBool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.content.topic_tagger import suggest_topic
from app.core.config import get_settings
from app.db import get_db
from app.deps import get_content_reviewer
from app.models import Question, Subject, Topic, User

router = APIRouter(prefix="/review", tags=["content-review"])


class ReviewUpdate(BaseModel):
    topic_id: int | None = None
    correct_option: int | None = Field(default=None, ge=1, le=10)
    subtopic: str | None = Field(default=None, max_length=160)
    pattern_type: str | None = Field(default=None, max_length=160)
    review_notes: str | None = None
    verification_status: str


@router.get("/questions")
def list_review_questions(
    status: str = Query(default="review_required"),
    limit: int = Query(default=50, ge=1, le=200),
    visual_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    _: User = Depends(get_content_reviewer),
):
    stmt = (
        select(Question)
        .options(selectinload(Question.options))
        .where(Question.verification_status == status)
        .order_by(Question.id)
        .limit(limit)
    )
    if visual_only:
        stmt = stmt.where(Question.requires_visual_review.is_(True))
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
            "source_page": q.source_page,
            "requires_visual_review": q.requires_visual_review,
            "source_chosen_option": q.source_chosen_option,
            "source_question_id": q.source_question_id,
            "source_status": q.source_status,
            "verification_status": q.verification_status,
            "review_notes": q.review_notes,
            "revision_digest": _revision_digest(db, q) if get_settings().phase_b_capture_enabled else None,
        }
        for q in questions
    ]


@router.post("/questions/{question_id}/suggest-topic")
def auto_tag_question(
    question_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_content_reviewer),
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
    _: User = Depends(get_content_reviewer),
):
    if get_settings().phase_b_capture_enabled:
        raise HTTPException(409, "Use immutable revision candidates; in-place review is disabled")
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    allowed = {"raw", "parsed", "review_required", "verified", "rejected"}
    if payload.verification_status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid verification status")

    changes = payload.model_dump(exclude_unset=True)
    if payload.verification_status == "verified" and changes.get('correct_option', question.correct_option) is None:
        raise HTTPException(status_code=400, detail="A verified question must have a correct answer")

    if payload.topic_id is not None:
        topic = db.get(Topic, payload.topic_id)
        if not topic or topic.subject_id != question.subject_id:
            raise HTTPException(status_code=400, detail="Topic does not match question subject")

    for key, value in changes.items():
        setattr(question, key, value)
    db.commit()

    return {"id": question.id, "verification_status": question.verification_status}


def _revision_digest(db, question):
    from app.services.revision_capture import capture_state
    from app.services.revision_ledger import digest
    return digest(capture_state(db, question, kind='editorial_base'))


class RevisionChanges(ReviewUpdate):
    question_text: str | None = Field(default=None, min_length=1)
    explanation: str | None = None
    fast_method: str | None = None
    difficulty: int | None = Field(default=None, ge=1, le=3)


class RevisionDraft(BaseModel):
    expected_digest: str = Field(min_length=64, max_length=64)
    reason: str = Field(min_length=1)
    changes: RevisionChanges


class RevisionReview(BaseModel):
    answer_verified: StrictBool
    all_options_checked: StrictBool
    instruction_reviewed: StrictBool
    visual_reviewed: StrictBool
    reference: str = Field(min_length=1)


@router.post('/questions/{question_id}/revisions')
def create_revision(question_id: int, payload: RevisionDraft, db: Session=Depends(get_db), reviewer: User=Depends(get_content_reviewer)):
    from uuid import uuid4
    from app.revision_models import EditorialCandidate, QuestionRevision
    from app.services.revision_capture import snapshot, lock_questions
    from app.services.revision_ledger import canonical
    import json
    if not get_settings().phase_b_capture_enabled:
        raise HTTPException(409, 'Phase B rollout is not enabled')
    locked=lock_questions(db,[question_id])
    question=locked[0] if locked else None
    if question is None:
        raise HTTPException(404, 'Question not found')
    if _revision_digest(db,question)!=payload.expected_digest:
        raise HTTPException(409, 'STALE_REVISION')
    if not payload.reason.strip():
        raise HTTPException(422, 'Revision reason required')
    changes=payload.changes.model_dump(exclude_unset=True)
    for field in ('question_text','difficulty'):
        if field in changes and changes[field] is None:
            raise HTTPException(422, f'{field} cannot be null')
    if 'question_text' in changes and not changes['question_text'].strip():
        raise HTTPException(422, 'Question text cannot be blank')
    if changes['verification_status'] not in {'raw','parsed','review_required','verified','rejected'}:
        raise HTTPException(422, 'Invalid verification status')
    if changes.get('topic_id') is not None:
        topic=db.get(Topic,changes['topic_id'])
        if topic is None or topic.subject_id!=question.subject_id:
            raise HTTPException(422, 'Topic does not match question subject')
    answer=changes.get('correct_option',question.correct_option)
    if changes['verification_status']=='verified' and answer not in {o.position for o in question.options}:
        raise HTTPException(422, 'Verified candidate requires an existing option key')
    parent=snapshot(db,question,kind='editorial_base')
    captured=json.loads(db.get(QuestionRevision,parent).payload)
    captured['question'].update(changes)
    captured.update(capture_kind='editorial_candidate',publication_eligible=False)
    candidate=EditorialCandidate(id=str(uuid4()),question_id=question.id,parent_revision_id=parent,
        author_id=reviewer.id,payload=canonical(captured),reason=payload.reason)
    db.add(candidate);db.commit()
    return {'candidate_id':candidate.id,'review_status':'pending_independent_review','published':False}


@router.get('/revisions/{candidate_id}')
def get_revision(candidate_id: str, db: Session=Depends(get_db), reviewer: User=Depends(get_content_reviewer)):
    import json
    from app.revision_models import EditorialCandidate, EditorialDecision, EditorialPublication, QuestionRevision
    if not get_settings().phase_b_capture_enabled:
        raise HTTPException(409, 'Phase B rollout is not enabled')
    candidate=db.get(EditorialCandidate,candidate_id)
    if candidate is None:
        raise HTTPException(404, 'Candidate not found')
    parent=db.get(QuestionRevision,candidate.parent_revision_id)
    return {'candidate_id':candidate.id,'author_id':candidate.author_id,'reason':candidate.reason,
            'before':json.loads(parent.payload),'after':json.loads(candidate.payload),
            'review_status':'reviewed' if db.get(EditorialDecision,candidate.id) else 'pending_independent_review',
            'published':bool(db.get(EditorialPublication,candidate.id))}


@router.post('/revisions/{candidate_id}/publish')
def publish_revision(candidate_id: str, db: Session=Depends(get_db), reviewer: User=Depends(get_content_reviewer)):
    from app.services.revision_publication import publish_candidate
    result=publish_candidate(db,candidate_id,reviewer.id)
    db.commit()
    return result


@router.post('/revisions/{candidate_id}/review')
def review_revision(candidate_id: str, payload: RevisionReview, db: Session=Depends(get_db), reviewer: User=Depends(get_content_reviewer)):
    from app.revision_models import EditorialCandidate, EditorialDecision
    from app.services.revision_ledger import canonical
    if not get_settings().phase_b_capture_enabled:
        raise HTTPException(409, 'Phase B rollout is not enabled')
    candidate=db.scalar(select(EditorialCandidate).where(EditorialCandidate.id==candidate_id).with_for_update())
    if candidate is None:
        raise HTTPException(404, 'Candidate not found')
    if candidate.author_id==reviewer.id:
        raise HTTPException(409, 'Independent reviewer required')
    if db.get(EditorialDecision,candidate_id):
        raise HTTPException(409, 'Decision already recorded')
    values=payload.model_dump()
    if not payload.reference.strip() or any(values[k] is not True for k in values if k!='reference'):
        raise HTTPException(422, 'Complete independent review evidence required')
    db.add(EditorialDecision(candidate_id=candidate_id,reviewer_id=reviewer.id,evidence=canonical(values)))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Decision already recorded')
    return {'candidate_id':candidate_id,'review_status':'reviewed','published':False}


@router.get("/stats")
def review_stats(
    db: Session = Depends(get_db),
    _: User = Depends(get_content_reviewer),
):
    statuses = ["raw", "parsed", "review_required", "verified", "rejected"]
    totals = {}
    for status in statuses:
        totals[status] = len(
            list(
                db.scalars(
                    select(Question.id).where(Question.verification_status == status)
                )
            )
        )
    visual_pending = len(
        list(
            db.scalars(
                select(Question.id).where(
                    Question.verification_status == "review_required",
                    Question.requires_visual_review.is_(True),
                )
            )
        )
    )
    return {"by_status": totals, "visual_pending": visual_pending}
