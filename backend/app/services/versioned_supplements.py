"""Explicitly reviewed, contributor-bound teaching payloads; no inferred approval."""
import json
from uuid import uuid4
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from app.access_models import ContentBinding, ContentSource, CourseGrant, SourceGrant
from app.models import Lesson, QuestionArchetype, Flashcard, Topic, Subject
from app.revision_models import TeachingSupplement, SupplementReview
from app.schemas import PracticeCoaching, OptionInsightOut
from app.services.revision_ledger import canonical, digest


class Contributor(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: str
    resource_id: int = Field(gt=0)


class SupplementDraft(BaseModel):
    model_config = ConfigDict(extra='forbid')
    coaching: PracticeCoaching | None = None
    option_insights: list[OptionInsightOut] = Field(default_factory=list)
    source_ids: list[str] = Field(min_length=1)
    contributors: list[Contributor] = Field(default_factory=list)


def fingerprint(data):
    return digest({k: data[k] for k in ('question', 'options', 'asset_refs')})


def sources_allowed(db, sources, exam_id, user_id=None):
    if not sources:
        return False
    if user_id is not None:
        course = db.get(CourseGrant, (user_id, exam_id))
        if not course or not course.active:
            return False
    for sid in sources:
        source = db.get(ContentSource, sid)
        if not source or source.exam_id != exam_id or not source.private_use_approved or not source.approval_reference.strip():
            return False
        if user_id is not None:
            grant = db.get(SourceGrant, (user_id, sid))
            if not grant or not grant.active:
                return False
    return True


def draft_supplement(db, question, author_id, draft):
    from app.services.revision_capture import capture_state
    data = capture_state(db, question, kind='editorial_base')
    positions = {o.position for o in question.options} - {question.correct_option}
    seen = set()
    for item in draft.option_insights:
        if (item.position not in positions or item.position in seen or
            item.insight_type not in {'fact','rule','misconception','comparison'} or
            not item.knowledge_text.strip() or not item.source_reference.strip() or
            bool(item.related_question) != bool(item.related_answer)):
            raise HTTPException(422, 'Invalid reviewed option context')
        seen.add(item.position)
    if draft.coaching is None and not draft.option_insights:
        raise HTTPException(422, 'Teaching payload required')
    sources = set(draft.source_ids)
    contributors = []
    # Declared first-party sources remain explicit; contributor mappings add ALL
    # dependencies and never establish rights by themselves.
    for ref in draft.contributors:
        model = {'lesson': Lesson, 'archetype': QuestionArchetype, 'flashcard': Flashcard}.get(ref.kind)
        resource = db.get(model, ref.resource_id) if model else None
        exam = db.scalar(select(Subject.exam_id).join(Topic, Topic.subject_id == Subject.id)
                         .where(Topic.id == resource.topic_id)) if resource else None
        ids = list(db.scalars(select(ContentBinding.source_id).where(
            ContentBinding.resource_kind == ref.kind, ContentBinding.resource_id == ref.resource_id)))
        if not resource or not resource.is_published or exam != question.exam_id or not ids:
            raise HTTPException(422, 'Complete published contributor bindings required')
        sources.update(ids)
        contributors.append({**ref.model_dump(), 'source_ids': sorted(ids)})
    if not sources_allowed(db, sources, question.exam_id):
        raise HTTPException(422, 'Explicit approved supplement sources required')
    payload = draft.model_dump(include={'coaching','option_insights'})
    row = TeachingSupplement(id=str(uuid4()), question_id=question.id,
        question_fingerprint=fingerprint(data), author_id=author_id,
        payload=canonical(payload), source_ids=canonical(sorted(sources)),
        contributors=canonical(contributors))
    db.add(row); db.flush()
    return row


def contributors_current(db, row, exam_id):
    for ref in json.loads(row.contributors):
        model = {'lesson': Lesson, 'archetype': QuestionArchetype, 'flashcard': Flashcard}.get(ref['kind'])
        resource = db.get(model, ref['resource_id']) if model else None
        course = db.scalar(select(Subject.exam_id).join(Topic, Topic.subject_id == Subject.id)
                           .where(Topic.id == resource.topic_id)) if resource else None
        ids = sorted(db.scalars(select(ContentBinding.source_id).where(
            ContentBinding.resource_kind == ref['kind'], ContentBinding.resource_id == ref['resource_id'])))
        if not resource or not resource.is_published or course != exam_id or not ids or ids != ref.get('source_ids'):
            return False
    return True


def choose_supplement(db, question, data, user_id):
    rows = db.scalars(select(TeachingSupplement).join(SupplementReview).where(
        TeachingSupplement.question_id == question.id,
        TeachingSupplement.question_fingerprint == fingerprint(data),
        SupplementReview.reviewer_id != TeachingSupplement.author_id,
    ).order_by(SupplementReview.created_at.desc(), TeachingSupplement.id.desc()))
    for row in rows:
        if contributors_current(db, row, question.exam_id) and sources_allowed(db, json.loads(row.source_ids), question.exam_id, user_id):
            return row.id
    return None


def delivered_supplements(db, question, user_id):
    empty = {'coaching': None, 'option_insights': []}
    sid = getattr(question, 'delivery_blueprint', {}).get('supplement_revision_id')
    if not sid:
        return empty
    row = db.get(TeachingSupplement, sid)
    review = db.get(SupplementReview, sid)
    if (not row or not review or review.reviewer_id == row.author_id or
        row.question_id != question.id or
        row.question_fingerprint != getattr(question, 'delivery_fingerprint', None) or
        not contributors_current(db, row, question.exam_id) or
        not sources_allowed(db, json.loads(row.source_ids), question.exam_id, user_id)):
        return empty
    # The immutable delivery pins the exact supplement; no current lookup fallback.
    return json.loads(row.payload)
