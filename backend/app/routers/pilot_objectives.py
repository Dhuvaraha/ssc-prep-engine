"""Phase D objective delivery. Exact reviewed releases and scoped grants only."""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictBool, StrictInt
from sqlalchemy import ForeignKey, Integer, String, Text, update
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.exc import IntegrityError
from app.db import Base, get_db
from app.models import User
from app.core.config import get_settings
from app.services.content_access import teaching_user
from app.services.exam_scope import current_exam
from app.services.versioned_supplements import sources_allowed
from app.services.pilot_curriculum import OBJECTIVES, ObjectiveUnit, load_unit
from app.services import teaching_journey as journey

router = APIRouter(prefix='/learn/pilot', tags=['learn'])


class ObjectiveProgress(Base):
    __tablename__ = 'pilot_objective_progress'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey('exams.id'), primary_key=True)
    objective_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    revision: Mapped[int] = mapped_column(Integer)
    unit_payload: Mapped[str] = mapped_column(Text)
    source_ids: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text)


class Action(BaseModel):
    expected_revision: StrictInt = Field(ge=0)
    action: str
    selected: StrictInt | None = Field(default=None,ge=1,le=4)
    reason_selected: StrictInt | None = Field(default=None,ge=1,le=4)
    guessed: StrictBool = False
    model: list[list[str]] | None = Field(default=None,max_length=8)


def now():
    return datetime.utcnow()


def authorize(oid, db, user):
    settings=get_settings()
    exam=current_exam(db,user_id=user.id)
    if not settings.phase_d_pilot_enabled or oid not in OBJECTIVES or exam.slug!='ssc-cgl-tier-1':
        raise HTTPException(404,'Reviewed objective not available')
    try:
        release=json.loads(settings.phase_d_release_manifest).get(oid,{})
        source_ids=release['source_ids']
        digests=release['digests']
        valid=(isinstance(source_ids,list) and source_ids and all(isinstance(x,str) for x in source_ids)
               and isinstance(digests,list) and all(isinstance(x,str) for x in digests)
               and isinstance(release['access_reference'],str) and release['access_reference'].strip())
    except (ValueError,TypeError,KeyError,AttributeError):
        valid=False
    if not valid or not sources_allowed(db,source_ids,exam.id,user.id):
        raise HTTPException(404,'Reviewed objective not available')
    row=db.get(ObjectiveProgress,(user.id,exam.id,oid))
    if row:
        try:
            pinned_sources=json.loads(row.source_ids)
            pinned_valid=isinstance(pinned_sources,list) and pinned_sources and all(isinstance(x,str) for x in pinned_sources)
        except (ValueError,TypeError):
            pinned_valid=False
        if not pinned_valid or not sources_allowed(db,pinned_sources,exam.id,user.id):
            raise HTTPException(404,'Reviewed objective not available')
    try:
        unit=ObjectiveUnit.model_validate_json(row.unit_payload) if row else load_unit(oid)
    except ValueError:
        raise HTTPException(404,'Reviewed objective not available')
    if not unit or unit.objective_id!=oid or not unit.reviewed() or unit.digest() not in digests:
        raise HTTPException(404,'Reviewed objective not available')
    return exam.id,row,unit,source_ids


@router.get('')
def catalog(db: Session=Depends(get_db), user: User=Depends(teaching_user)):
    if not get_settings().phase_d_pilot_enabled:
        raise HTTPException(404,'Pilot not available')
    result=[]
    for oid, info in OBJECTIVES.items():
        try:
            authorize(oid,db,user)
            available=True
        except HTTPException as error:
            if error.status_code!=404:
                raise
            available=False
        result.append(dict(objective_id=oid,topic=info['topic'],title=info['description'],available=available))
    return result


@router.get('/{objective_id}')
def read(objective_id: str, db: Session=Depends(get_db), user: User=Depends(teaching_user)):
    _,row,unit,_=authorize(objective_id,db,user)
    content=unit.content()
    try:
        return journey.view(content,json.loads(row.state) if row else journey.initial(content),row.revision if row else 0)
    except journey.JourneyConflict as error:
        raise HTTPException(409,str(error)) from error


@router.post('/{objective_id}/actions')
def act(objective_id: str, payload: Action, db: Session=Depends(get_db), user: User=Depends(teaching_user)):
    exam_id,row,unit,source_ids=authorize(objective_id,db,user)
    content=unit.content()
    revision=row.revision if row else 0
    if payload.expected_revision!=revision:
        raise HTTPException(409,'Progress changed; reload the journey')
    try:
        state=journey.advance(content,json.loads(row.state) if row else journey.initial(content),
            payload.action,payload.selected,now(),reason_selected=payload.reason_selected,
            guessed=payload.guessed,model=payload.model)
        response=journey.view(content,state,revision+1)
    except journey.JourneyConflict as error:
        raise HTTPException(409,str(error)) from error
    encoded=json.dumps(state)
    if row:
        changed=db.execute(update(ObjectiveProgress).where(ObjectiveProgress.user_id==user.id,
            ObjectiveProgress.exam_id==exam_id,ObjectiveProgress.objective_id==objective_id,
            ObjectiveProgress.revision==revision).values(state=encoded,revision=revision+1))
        if changed.rowcount!=1:
            raise HTTPException(409,'Progress changed; reload the journey')
    else:
        db.add(ObjectiveProgress(user_id=user.id,exam_id=exam_id,objective_id=objective_id,
            revision=1,unit_payload=unit.model_dump_json(),source_ids=json.dumps(source_ids),state=encoded))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'Progress changed; reload the journey')
    return response
