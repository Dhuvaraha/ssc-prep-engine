"""Capture the exact loaded delivery; caller commits pins with the delivery."""
import json
from datetime import datetime
from sqlalchemy import exists, literal, select
from app.access_models import AssessmentAsset, ContentBinding
from app.core.config import get_settings
from app.models import QuestionOption
from app.revision_models import QuestionRevision, DeliveryRevision
from app.services.legacy_snapshot import capture_question
from app.services.revision_ledger import canonical, digest


def lock_questions(db, question_ids):
    """Serialize delivery/publication and refresh pre-lock ORM state."""
    from sqlalchemy import update
    from sqlalchemy.orm import selectinload
    from app.models import Question
    ids=sorted(set(question_ids))
    if db.bind.dialect.name=='sqlite':
        # SQLite has no row locks; acquire its writer lock before the read.
        db.execute(update(Question).where(Question.id.in_(ids)).values(id=Question.id))
    return list(db.scalars(select(Question).where(Question.id.in_(ids)).order_by(Question.id)
        .options(selectinload(Question.options)).with_for_update()
        .execution_options(populate_existing=True)).unique())


def capture_state(db, question, *, kind='delivery_capture'):
    expected=list(db.scalars(select(QuestionOption.id).where(QuestionOption.question_id==question.id)))
    data=capture_question(question,question.options,expected_option_ids=expected)
    for asset in data['asset_refs']:
        reference=asset['reference']
        if isinstance(reference,str) and reference.startswith('private://'):
            reviewed=db.get(AssessmentAsset,reference.removeprefix('private://'))
            if reviewed:
                asset.update(content_sha256=reviewed.content_sha256,bytes_verified=True,
                             hash_basis='reviewed_asset_manifest')
        if kind=='delivery_capture' and not asset['bytes_verified']:
            raise ValueError('Delivery revision requires versioned asset bytes')
    # This is present delivery evidence, not retroactive history reconstruction.
    data.update(capture_kind=kind, original_version_unknown=False)
    return data


def snapshot(db, question, *, kind='delivery_capture'):
    data=capture_state(db,question,kind=kind)
    rid=digest(data)
    key=digest({'answer':data['question']['correct_option'],'options':data['options'],'assets':data['asset_refs']})
    insert_module='postgresql' if db.bind.dialect.name=='postgresql' else 'sqlite'
    if insert_module=='postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    # Identical snapshots may be captured concurrently by separate learners.
    values=select(literal(rid),literal(question.id),literal(canonical(data)),literal(key),literal(datetime.utcnow())).where(
        ~exists(select(QuestionRevision.id).where(QuestionRevision.id==rid)))
    db.execute(insert(QuestionRevision).from_select(['id','question_id','payload','answer_version','captured_at'],values)
               .on_conflict_do_nothing(index_elements=['id']))
    return rid


def pin_delivery(db, *, kind, delivery_id, user_id, question, blueprint):
    if not get_settings().phase_b_capture_enabled:
        return
    rid=snapshot(db,question)
    source_ids=sorted(db.scalars(select(ContentBinding.source_id).where(
        ContentBinding.resource_kind=='question',ContentBinding.resource_id==question.id)))
    if not source_ids:
        raise ValueError('Cannot pin delivery without source bindings')
    db.add(DeliveryRevision(kind=kind,delivery_id=str(delivery_id),question_id=question.id,user_id=user_id,
        revision_id=rid,source_ids=canonical(source_ids),blueprint=canonical(blueprint)))
    db.flush()


def read_evidence(db, kind, delivery_id, question_id):
    """Internal only. Learner routes must separately authorize owner and sources."""
    pin=db.get(DeliveryRevision,(kind,str(delivery_id),question_id))
    if pin is None:
        return {'original_version_unknown':True,'revision':None}
    revision=db.get(QuestionRevision,pin.revision_id)
    return {'original_version_unknown':False,'revision':json.loads(revision.payload),
            'answer_version':revision.answer_version,'blueprint':json.loads(pin.blueprint)}


def delivered_question(db, *, kind, delivery_id, user_id, current):
    """Detached delivery view; authorize both current and historical dependencies.

    Never attach the snapshot to the ORM or reconstruct an absent historical pin.
    The caller still enforces assessment windows and answer visibility.
    """
    from types import SimpleNamespace
    from fastapi import HTTPException
    from app.access_models import ContentSource, CourseGrant, SourceGrant
    from app.models import Question
    from app.services.content_access import question_policy
    if not get_settings().phase_b_capture_enabled:
        return current
    pin=db.get(DeliveryRevision,(kind,str(delivery_id),current.id))
    if pin is None:
        return current
    course=db.get(CourseGrant,(user_id,current.exam_id))
    if pin.user_id!=user_id or not course or not course.active or not db.scalar(
        select(Question.id).where(Question.id==current.id,question_policy(user_id,current.exam_id))
    ):
        raise HTTPException(404,'Delivery not available')
    revision=db.get(QuestionRevision,pin.revision_id)
    data=json.loads(revision.payload)
    record=data['question']
    if record['id']!=current.id or record['exam_id']!=current.exam_id:
        raise HTTPException(409,'DELIVERY_REVISION_INVALID')
    sources=json.loads(pin.source_ids)
    if not sources:
        raise HTTPException(409,'DELIVERY_REVISION_INVALID')
    for source_id in sources:
        source=db.get(ContentSource,source_id)
        grant=db.get(SourceGrant,(user_id,source_id))
        allowed=source and source.exam_id==current.exam_id and (
            (record['visibility']=='public' and source.public_use_approved) or
            (source.private_use_approved and grant and grant.active))
        if not allowed:
            raise HTTPException(404,'Delivery not available')
    view=SimpleNamespace(**record,options=[SimpleNamespace(**o) for o in data['options']],
                         delivery_revision_id=pin.revision_id,
                         delivery_blueprint=json.loads(pin.blueprint))
    from app.services.practice_integrity import question_digest
    view.delivery_current_matches=question_digest(view)==question_digest(current)
    return view


def mock_marks(db, attempt, rows):
    """One coherent pinned marking scheme, with explicit legacy compatibility."""
    from fastapi import HTTPException
    from app.models import Exam
    blueprints=[getattr(q,'delivery_blueprint',None) for _,q in rows]
    pinned=[b for b in blueprints if b is not None]
    if pinned:
        schemes={(b['positive_marks'],b['negative_marks']) for b in pinned}
        if len(pinned)!=len(rows) or len(schemes)!=1:
            raise HTTPException(409,'INCONSISTENT_DELIVERY_BLUEPRINT')
        positive,negative=next(iter(schemes))
        return float(positive),float(negative)
    exam=db.get(Exam,attempt.exam_id)
    return float(exam.positive_marks if exam else 2),float(exam.negative_marks if exam else 0.5)


def bind_mock_timing(db, attempt):
    """Use a complete, consistent delivered blueprint; never backfill old attempts."""
    from fastapi import HTTPException
    from app.models import MockAttemptQuestion
    if not get_settings().phase_b_capture_enabled:
        return
    pins=db.scalars(select(DeliveryRevision).where(DeliveryRevision.kind=='mock',
        DeliveryRevision.delivery_id==str(attempt.id))).all()
    if not pins:
        return
    rows=db.scalars(select(MockAttemptQuestion).where(MockAttemptQuestion.attempt_id==attempt.id)).all()
    if len(pins)!=len(rows) or {p.question_id for p in pins}!={r.question_id for r in rows} or any(p.user_id!=attempt.user_id for p in pins):
        raise HTTPException(409,'INCOMPLETE_DELIVERY_BLUEPRINT')
    fields=('mode','duration_minutes','section_order','full_section_seconds')
    blueprints=[json.loads(p.blueprint) for p in pins]
    timing={key:blueprints[0].get(key) for key in fields}
    if any({key:b.get(key) for key in fields}!=timing for b in blueprints):
        raise HTTPException(409,'INCONSISTENT_DELIVERY_BLUEPRINT')
    duration,order,seconds=timing['duration_minutes'],timing['section_order'],timing['full_section_seconds']
    if (timing['mode']!=attempt.mode or duration!=attempt.duration_minutes or
        type(duration) is not int or duration<=0 or type(seconds) is not int or seconds<=0 or
        not isinstance(order,list) or not order or any(not isinstance(s,str) or not s for s in order) or
        len(set(order))!=len(order) or (attempt.mode=='full' and len(order)*seconds!=duration*60)):
        raise HTTPException(409,'INVALID_DELIVERY_BLUEPRINT')
    attempt.delivery_timing=timing
