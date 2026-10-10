import hashlib
import json
import re
from datetime import datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.access_models import ContentExposure, PracticeDelivery
from app.models import MockAttempt, MockAttemptQuestion, QuestionAttempt


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def question_digest(question):
    return digest([question.question_text, question.question_image_url,
                   [(o.position, o.text, o.image_url) for o in question.options],
                   question.correct_option, question.explanation, question.fast_method])


def exposure_digest(question):
    def normalize(value):
        return re.sub(r"\s+", " ", value or "").strip().casefold()
    return digest([normalize(question.question_text), question.question_image_url,
                   sorted((normalize(o.text), o.image_url or "") for o in question.options)])


def expose(db, user_id, question, reason):
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    db.execute(insert(ContentExposure).values(
        user_id=user_id, content_digest=exposure_digest(question), reason=reason,
    ).on_conflict_do_nothing(index_elements=["user_id", "content_digest"]))


def issue_delivery(db, user_id, question):
    previously_seen = db.get(ContentExposure, (user_id, exposure_digest(question))) is not None
    # Compatibility: historical practice and mocks remain usable history, never
    # retroactively rewritten as fresh independent evidence.
    previously_seen |= db.scalar(select(QuestionAttempt.id).where(
        QuestionAttempt.user_id == user_id, QuestionAttempt.question_id == question.id).limit(1)) is not None
    previously_seen |= db.scalar(select(MockAttemptQuestion.id).join(MockAttempt).where(
        MockAttempt.user_id == user_id, MockAttemptQuestion.question_id == question.id).limit(1)) is not None
    delivery = PracticeDelivery(id=str(uuid4()), user_id=user_id, question_id=question.id,
                                content_digest=question_digest(question), assisted=previously_seen)
    db.add(delivery)
    db.flush()
    return delivery


def load_delivery(db, user_id, token, question):
    delivery = db.get(PracticeDelivery, token)
    if not delivery or delivery.user_id != user_id or delivery.question_id != question.id:
        raise HTTPException(404, "Delivery not available")
    if delivery.content_digest != question_digest(question):
        raise HTTPException(409, "CONTENT_CHANGED")
    if not delivery.result_json and delivery.created_at < datetime.utcnow() - timedelta(hours=4):
        raise HTTPException(409, "DELIVERY_EXPIRED")
    if db.get(ContentExposure, (user_id, exposure_digest(question))):
        delivery.assisted = True
    return delivery
