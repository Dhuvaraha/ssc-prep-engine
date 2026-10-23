"""Gated original teaching pilot. No legacy attempts or mastery rows are changed."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictInt
from sqlalchemy import ForeignKey, Integer, Text, update
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.exc import IntegrityError
from app.db import Base, get_db
from app.models import User
from app.core.config import get_settings
from app.services.content_access import teaching_user
from app.services.exam_scope import current_exam
from app.services.versioned_supplements import sources_allowed
from app.services.percentage_journey import CONTENT
from app.services import teaching_journey as journey

router = APIRouter(prefix='/learn/percentage-pilot', tags=['learn'])


class PercentageProgress(Base):
    __tablename__ = 'percentage_pilot_progress'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey('exams.id'), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(Text)


class Action(BaseModel):
    expected_revision: StrictInt = Field(ge=0)
    action: str
    selected: StrictInt | None = Field(default=None, ge=1, le=4)


def now():
    return datetime.utcnow()


def authorize(db, user):
    settings = get_settings()
    exam = current_exam(db, user_id=user.id)
    if (not settings.percentage_pilot_enabled or not settings.percentage_pilot_review_reference.strip()
        or exam.slug != 'ssc-cgl-tier-1' or not sources_allowed(db,
        [settings.percentage_pilot_source_id], exam.id, user.id)):
        raise HTTPException(404, 'Pilot not available')
    return exam.id


def initial():
    return journey.initial(CONTENT)


def item(state):
    return CONTENT.question(state)


def view(state, revision):
    try:
        return journey.view(CONTENT, state, revision)
    except journey.JourneyConflict as error:
        raise HTTPException(409, str(error)) from error


@router.get('')
def get_pilot(db: Session=Depends(get_db), user: User=Depends(teaching_user)):
    exam_id = authorize(db,user)
    row = db.get(PercentageProgress,(user.id,exam_id))
    return view(json.loads(row.state) if row else initial(),row.revision if row else 0)


@router.post('/actions')
def act(payload: Action, db: Session=Depends(get_db), user: User=Depends(teaching_user)):
    exam_id = authorize(db,user)
    row = db.get(PercentageProgress,(user.id,exam_id))
    revision = row.revision if row else 0
    if payload.expected_revision != revision:
        raise HTTPException(409,'Progress changed; reload the journey')
    state = json.loads(row.state) if row else initial()
    try:
        state = journey.advance(CONTENT, state, payload.action, payload.selected, now())
    except journey.JourneyConflict as error:
        raise HTTPException(409, str(error)) from error
    encoded = json.dumps(state)
    if row:
        changed = db.execute(update(PercentageProgress).where(PercentageProgress.user_id==user.id,
            PercentageProgress.exam_id==exam_id,PercentageProgress.revision==revision)
            .values(state=encoded,revision=revision+1))
        if changed.rowcount != 1: raise HTTPException(409,'Progress changed; reload the journey')
    else:
        db.add(PercentageProgress(user_id=user.id,exam_id=exam_id,revision=1,state=encoded))
    try: db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Progress changed; reload the journey')
    return view(state,revision+1)
