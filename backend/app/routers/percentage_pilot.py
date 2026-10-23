"""Gated original teaching pilot. No legacy attempts or mastery rows are changed."""
import json
from datetime import datetime, timedelta
from decimal import Decimal
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
from app.services.percentage_journey import LESSON, ITEMS, VERSION

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
    return dict(content_version=VERSION, phase='teach', stage='diagnose', variant=0,
                assisted=False, feedback=None, due_at=None, retention=0, history=[])


def item(state):
    result = dict(raw_item(state))
    shift = state['variant'] % 4
    for field in ('options', 'explanations', 'repairs'):
        result[field] = result[field][shift:] + result[field][:shift]
    result['answer'] = (result['answer'] - 1 - shift) % 4 + 1
    return result


def raw_item(state):
    base = next(i for i in ITEMS if i['id'] == state['stage'])
    n = state['variant']
    if not n:
        return base
    # Fresh quantities, same explicit objective. These are near-transfer checks,
    # not independent evidence of whole-topic or examination readiness.
    amount = Decimal(400 + n * 100)
    a, b = Decimal(20), Decimal(15)
    correct = amount * (1-a/100) * (1-b/100)
    values = [amount*(1-(a+b)/100), correct, amount*(1-a/100), amount*(1-b/100)]
    if state['stage'] == 'transfer':
        markup = Decimal(40+n)
        payment = (100+markup)*Decimal('.9')*Decimal('.8')
        receipt = payment*Decimal('.95')
        values = [receipt-100,payment-100,(100+markup)*Decimal('.7')*Decimal('.95')-100,payment-105]
        labels = [f'{abs(v).normalize():f}% '+('profit' if v>=0 else 'loss') for v in values]
        return dict(id='transfer', stem=f'A seller lists an item {markup}% above cost, discounts it by 10% then 20%, and pays 5% of the customer payment as a fee. What is the result relative to cost?',
            options=labels,answer=1,explanations=[f'Use cost 100: payment {payment}, receipt {receipt}; compare receipt with cost.',
            'This omits the fee from customer payment.','This adds the discount rates instead of changing the base.',
            'This incorrectly subtracts a fee of 5 from a cost base of 100.'],repairs=base['repairs'])
    return dict(id=state['stage'],stem=f'A price of {amount} receives successive discounts of 20% and 15%. What is paid?',
        options=[f'{v.normalize():f}' for v in values],answer=2,
        explanations=[f'{values[0]} adds the rates, using the wrong second base.',
        f'{correct} = {amount} × 0.80 × 0.85. The second base is {values[2]}.',
        f'{values[2]} stops after the first discount.',f'{values[3]} omits the first discount.'],
        repairs=['Name the new base before applying the second reduction.',
                 'Explain both bases without looking at the worked example.',
                 'Complete the second reduction after the first.',
                 'Apply both reductions in their stated order.'])


def view(state, revision):
    if state['content_version'] != VERSION:
        raise HTTPException(409, 'Content version requires reviewed migration')
    result = {k:v for k,v in state.items() if k != 'history'}
    result.update(revision=revision, lesson=LESSON,
        evidence_label='Pilot near-transfer and retention evidence only; not exam readiness.')
    if state['phase'] == 'check':
        q = item(state)
        result['question'] = {k:q[k] for k in ('id','stem','options')}
        result['hint'] = 'Name the amount each percentage applies to, then multiply the fractions remaining.' if state['assisted'] else None
    return result


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
    if state['content_version'] != VERSION:
        raise HTTPException(409,'Content version requires reviewed migration')
    phase, action = state['phase'], payload.action
    if phase == 'teach' and action == 'start':
        state['phase'] = 'check'
    elif phase == 'check' and action == 'hint':
        state['assisted'] = True
    elif phase == 'check' and action == 'answer' and payload.selected is not None:
        q = item(state)
        independent = payload.selected == q['answer'] and not state['assisted']
        state['feedback'] = dict(correct=payload.selected==q['answer'], independent=independent,
            selected=payload.selected,correct_option=q['answer'],options=q['options'],
            explanations=q['explanations'],repair=q['repairs'][payload.selected-1],stem=q['stem'])
        state['history'].append(dict(stage=state['stage'],variant=state['variant'],selected=payload.selected,
            independent=independent,assisted=state['assisted'],at=now().isoformat()))
        state['phase'] = 'feedback'
    elif phase == 'feedback' and action == 'continue':
        if not state['feedback']['independent']:
            if state['stage'] == 'revision':
                state['revision_repaired'] = True
            state['phase'] = 'repair'
        elif state['stage'] in ('transfer','revision'):
            repaired = state.get('revision_repaired', False)
            if state['stage']=='revision' and not repaired:
                state['retention'] += 1
            days = 1 if repaired else [1,3,7][min(state['retention'],2)]
            state['due_at'] = (now()+timedelta(days=days)).isoformat()
            state['phase'] = 'complete' if state['retention']>=2 else 'waiting'
        else:
            state['stage'] = 'retry' if state['stage']=='diagnose' else 'transfer'
            if state['variant']: state['variant'] += 1
            state['phase']='check';state['assisted']=False;state['feedback']=None
    elif phase == 'repair' and action == 'retry':
        state['variant'] += 1
        state['phase']='check';state['assisted']=False;state['feedback']=None
    elif phase in ('waiting','complete') and action == 'revise':
        if now() < datetime.fromisoformat(state['due_at']):
            raise HTTPException(409,'Revision is not due yet')
        state['stage']='revision';state['variant'] += 1
        state['revision_repaired'] = False
        state['phase']='check';state['assisted']=False;state['feedback']=None
    else:
        raise HTTPException(409,'Action is not available at this stage')
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
