"""Reviewed correction transaction. Caller commits publication and current projection together."""
import json
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import get_settings
from app.models import MockAttempt, MockAttemptQuestion, Topic
from app.access_models import PracticeDelivery
from app.revision_models import DeliveryRevision, EditorialCandidate, EditorialDecision, EditorialPublication, QuestionRevision
from app.services.revision_capture import lock_questions, snapshot, capture_state
from app.services.revision_ledger import digest


EDITABLE={'topic_id','correct_option','subtopic','pattern_type','review_notes',
          'verification_status','question_text','explanation','fast_method','difficulty'}


def publish_candidate(db, candidate_id, publisher_id):
    settings=get_settings()
    if not settings.phase_b_capture_enabled or not settings.phase_b_publication_enabled:
        raise HTTPException(409,'Revision publication is not enabled')
    candidate=db.get(EditorialCandidate,candidate_id)
    if candidate is None:
        raise HTTPException(404,'Candidate not found')
    questions=lock_questions(db,[candidate.question_id])
    if not questions:
        raise HTTPException(404,'Question not found')
    question=questions[0]
    if db.get(EditorialPublication,candidate.id):
        raise HTTPException(409,'Candidate already published')
    decision=db.get(EditorialDecision,candidate.id)
    if not decision or decision.reviewer_id==candidate.author_id:
        raise HTTPException(409,'Independent review required')
    if digest(capture_state(db,question,kind='editorial_base'))!=candidate.parent_revision_id:
        raise HTTPException(409,'STALE_REVISION')
    # A legacy in-flight assessment has no complete immutable view to preserve.
    active=db.execute(select(MockAttempt.id).join(MockAttemptQuestion).where(
        MockAttempt.status=='in_progress',MockAttemptQuestion.question_id==question.id)).scalars().all()
    if any(db.get(DeliveryRevision,('mock',str(aid),question.id)) is None for aid in active):
        raise HTTPException(409,'UNPINNED_ACTIVE_DELIVERY')
    practices=db.scalars(select(PracticeDelivery.id).where(
        PracticeDelivery.question_id==question.id,PracticeDelivery.result_json.is_(None),
        PracticeDelivery.created_at>=datetime.utcnow()-timedelta(hours=4))).all()
    if any(db.get(DeliveryRevision,('practice',token,question.id)) is None for token in practices):
        raise HTTPException(409,'UNPINNED_ACTIVE_DELIVERY')
    parent=json.loads(db.get(QuestionRevision,candidate.parent_revision_id).payload)
    proposed=json.loads(candidate.payload)
    before,after=parent['question'],proposed['question']
    if proposed['options']!=parent['options'] or proposed['asset_refs']!=parent['asset_refs']:
        raise HTTPException(409,'Unsupported option or asset correction')
    if set(before)!=set(after) or any(after[k]!=before[k] for k in before if k not in EDITABLE):
        raise HTTPException(409,'Unsupported question identity correction')
    if after['verification_status']!='verified' or after['correct_option'] not in {o.position for o in question.options}:
        raise HTTPException(409,'Verified candidate with valid key required')
    if after['topic_id'] is not None:
        topic=db.get(Topic,after['topic_id'])
        if not topic or topic.subject_id!=question.subject_id:
            raise HTTPException(409,'Candidate topic no longer valid')
    for key in EDITABLE:
        setattr(question,key,after[key])
    db.flush()
    revision_id=snapshot(db,question,kind='editorial_base')
    db.add(EditorialPublication(candidate_id=candidate.id,revision_id=revision_id,publisher_id=publisher_id))
    db.flush()
    return {'candidate_id':candidate.id,'revision_id':revision_id,'published':True}
