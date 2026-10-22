"""Read saved practice evidence without reconstructing missing historical content."""
import json
from sqlalchemy import select
from app.access_models import PracticeDelivery
from app.core.config import get_settings
from app.revision_models import DeliveryRevision
from app.services.revision_capture import delivered_question


def attempt_views(db, attempts, questions):
    views = {a.id: questions.get(a.question_id) for a in attempts}
    if not attempts or not get_settings().phase_b_capture_enabled:
        return views
    by_id = {a.id: a for a in attempts}
    users = {a.user_id for a in attempts}
    direct = list(db.scalars(select(DeliveryRevision).where(
        DeliveryRevision.kind == 'practice_attempt', DeliveryRevision.delivery_id.in_([str(a.id) for a in attempts]),
        DeliveryRevision.user_id.in_(users))))
    direct_ids = set()
    for pin in direct:
        aid = int(pin.delivery_id)
        attempt = by_id[aid]
        if pin.user_id != attempt.user_id or pin.question_id != attempt.question_id:
            from fastapi import HTTPException
            raise HTTPException(409, 'INVALID_ATTEMPT_REVISION')
        direct_ids.add(aid)
        current = questions.get(attempt.question_id)
        if current is not None:
            views[aid] = delivered_question(db, kind='practice_attempt', delivery_id=aid,
                                            user_id=attempt.user_id, current=current)
    # Previously committed Phase B results already contain the exact attempt ID.
    # Join only actual delivery evidence; never infer a pin from timestamps.
    rows = db.execute(select(PracticeDelivery, DeliveryRevision).join(
        DeliveryRevision,
        (DeliveryRevision.kind == 'practice') &
        (DeliveryRevision.delivery_id == PracticeDelivery.id) &
        (DeliveryRevision.question_id == PracticeDelivery.question_id) &
        (DeliveryRevision.user_id == PracticeDelivery.user_id),
    ).where(PracticeDelivery.user_id.in_(users), PracticeDelivery.result_json.is_not(None)))
    seen = set()
    for delivery, pin in rows:
        aid = json.loads(delivery.result_json).get('attempt_id')
        attempt = by_id.get(aid)
        if not attempt or aid in direct_ids:
            continue
        if aid in seen or attempt.user_id != pin.user_id or attempt.question_id != pin.question_id:
            from fastapi import HTTPException
            raise HTTPException(409, 'AMBIGUOUS_ATTEMPT_REVISION')
        seen.add(aid)
        current = questions.get(attempt.question_id)
        if current is not None:
            views[aid] = delivered_question(db, kind='practice', delivery_id=delivery.id,
                                            user_id=attempt.user_id, current=current)
    return views


def record_attempt_receipt(db, attempt, delivery):
    if not get_settings().phase_b_capture_enabled:
        return
    pin = db.get(DeliveryRevision, ('practice', delivery.id, attempt.question_id))
    if pin is None:
        return  # An authentic legacy delivery stays explicitly unpinned.
    from app.services.revision_ledger import canonical
    db.add(DeliveryRevision(kind='practice_attempt', delivery_id=str(attempt.id),
        question_id=attempt.question_id, user_id=attempt.user_id, revision_id=pin.revision_id,
        source_ids=pin.source_ids, blueprint=canonical({**json.loads(pin.blueprint),
                                                     'practice_delivery_id': delivery.id})))
