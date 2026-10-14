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
