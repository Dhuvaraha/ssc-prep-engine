"""Reusable teaching transitions; authorization and persistence remain in adapters."""
from copy import deepcopy
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable
from app.services.countermodel import check as check_countermodel


class JourneyConflict(ValueError):
    pass


@dataclass(frozen=True)
class JourneyContent:
    version: str
    lesson: dict
    raw_item: Callable[[dict], dict]
    hint: str
    learning_stages: tuple[str, ...] = ('diagnose', 'retry', 'transfer')
    guided_stages: tuple[str, ...] = ()
    track_exposure: bool = False
    repeat_revision: bool = True
    reason_after_answer: bool = False

    def question(self, state):
        result = deepcopy(self.raw_item(state))
        if (not isinstance(result, dict)
            or any(not isinstance(result.get(field), str) or not result[field].strip()
                   for field in ('id','stem'))
            or type(result.get('answer')) is not int or result['answer'] not in (1,2,3,4)
            or any(not isinstance(result.get(field), list) or len(result[field]) != 4
                   or any(not isinstance(value,str) or not value.strip() for value in result[field])
                   for field in ('options','explanations','repairs'))
            or len(set(result['options'])) != 4):
            raise JourneyConflict('Reviewed four-option content required')
        if 'reason_options' in result or 'reason_answer' in result:
            reasons=result.get('reason_options')
            if (not isinstance(reasons,list) or not 2 <= len(reasons) <= 4
                or any(not isinstance(x,str) or not x.strip() for x in reasons)
                or type(result.get('reason_answer')) is not int
                or result['reason_answer'] not in range(1,len(reasons)+1)
                or not isinstance(result.get('reason_prompt'),str) or not result['reason_prompt'].strip()
                or not isinstance(result.get('reason_explanation'),str) or not result['reason_explanation'].strip()):
                raise JourneyConflict('Reviewed reasoning rubric required')
        shift = state['variant'] % 4
        if self.track_exposure:
            shift = (shift + int(hashlib.sha256(result['id'].encode()).hexdigest()[:8],16)) % 4
            if 'reason_options' in result:
                reasons=result['reason_options']
                reason_shift=int(hashlib.sha256(('reason:'+result['id']).encode()).hexdigest()[:8],16)%len(reasons)
                result['reason_options']=reasons[reason_shift:]+reasons[:reason_shift]
                result['reason_answer']=(result['reason_answer']-1-reason_shift)%len(reasons)+1
        for field in ('options','explanations','repairs'):
            result[field] = result[field][shift:] + result[field][:shift]
        if result.get('figure'):
            scenes=result['figure']['options']
            result['figure']['options']=scenes[shift:]+scenes[:shift]
            if result.get('positional_figure_options'):
                result['options']=['Figure 1','Figure 2','Figure 3','Figure 4']
        result['answer'] = (result['answer'] - 1 - shift) % 4 + 1
        return result


def initial(content):
    return dict(content_version=content.version, phase='teach', stage=content.learning_stages[0], variant=0,
                assisted=False, feedback=None, due_at=None, retention=0, history=[])


def require_version(content, state):
    if state['content_version'] != content.version:
        raise JourneyConflict('Content version requires reviewed migration')


def view(content, state, revision):
    require_version(content, state)
    result = deepcopy({k:v for k,v in state.items() if k != 'history'})
    result.update(revision=revision, lesson=deepcopy(content.lesson),
        evidence_label='Pilot near-transfer and retention evidence only; not exam readiness.')
    if state['phase'] in ('check','justify'):
        q = content.question(state)
        result['question'] = {k:q[k] for k in ('id','stem','options')}
        if content.reason_after_answer:
            result['question']['requires_reason']=True
        if 'reason_options' in q and (not content.reason_after_answer or state['phase']=='justify'):
            result['question']['reason_prompt'] = q['reason_prompt']
            result['question']['reason_options'] = q['reason_options']
        for field in ('passage', 'figure', 'diagram'):
            if field in q:
                result['question'][field] = q[field]
        if q.get('construction') and state['phase']=='justify':
            result['question']['construction']=q['construction']
        result['hint'] = content.hint if state['assisted'] else None
    return result


def advance(content, saved_state, action, selected, clock, *, reason_selected=None, guessed=False, model=None):
    require_version(content, saved_state)
    state = deepcopy(saved_state)
    if selected is not None and (type(selected) is not int or selected not in (1,2,3,4)):
        raise JourneyConflict('Choose one of the four options')
    phase, action = state['phase'], action
    justified=False
    if phase=='justify' and action=='justify':
        pending=state.pop('pending_answer')
        if selected is not None and selected!=pending['selected']:
            raise JourneyConflict('The submitted answer is locked; justify that answer')
        if type(guessed) is not bool:
            raise JourneyConflict('Guess evidence must be a boolean')
        selected=pending['selected'];guessed=pending['guessed'] or guessed
        phase=state['phase']='check';action='answer';justified=True
    if phase=='check' and action=='answer' and content.reason_after_answer and not justified:
        if selected is None:
            raise JourneyConflict('Choose one of the four options')
        if type(guessed) is not bool:
            raise JourneyConflict('Guess evidence must be a boolean')
        state['pending_answer']=dict(selected=selected,guessed=guessed)
        state['phase']='justify'
        return state
    if phase == 'teach' and action == 'start':
        state['phase'] = 'check'
    elif phase == 'check' and action == 'hint':
        state['assisted'] = True
    elif phase == 'check' and action == 'answer' and selected is not None:
        q = content.question(state)
        reason_correct = True
        if 'reason_answer' in q:
            if type(reason_selected) is not int or reason_selected not in range(1, len(q['reason_options'])+1):
                raise JourneyConflict('Choose the supporting reason or evidence')
            reason_correct = reason_selected == q['reason_answer']
        if type(guessed) is not bool:
            raise JourneyConflict('Guess evidence must be a boolean')
        construction_correct=True
        construction_feedback=None
        if q.get('construction'):
            try:
                construction_correct,construction_feedback=check_countermodel(q['construction'],model)
            except ValueError as error:
                raise JourneyConflict(str(error)) from error
        correct = selected == q['answer'] and reason_correct and construction_correct
        guided = state['stage'] in content.guided_stages
        independent = correct and not state['assisted'] and not guessed and not guided
        state['feedback'] = dict(correct=correct, independent=independent,
            selected=selected,correct_option=q['answer'],options=q['options'],
            explanations=q['explanations'],repair=q['repairs'][selected-1],stem=q['stem'])
        state['history'].append(dict(stage=state['stage'],variant=state['variant'],selected=selected,
            independent=independent,assisted=state['assisted'],at=clock.isoformat()))
        if content.track_exposure:
            state['history'][-1].update(question_id=q['id'],reason_selected=reason_selected,
                reason_correct=reason_correct,guessed=guessed,guided=guided)
            state['feedback']['reason_explanation'] = q.get('reason_explanation', '')
            state['feedback']['candidate_misconception'] = not correct
            if q.get('construction'):
                state['history'][-1].update(model=deepcopy(model),construction_correct=construction_correct)
                state['feedback']['construction_feedback']=construction_feedback
            for field in ('passage','figure','diagram'):
                if field in q:
                    state['feedback'][field] = deepcopy(q[field])
        state['phase'] = 'feedback'
    elif phase == 'feedback' and action == 'continue':
        if not state['feedback']['independent'] and not (
            state['stage'] in content.guided_stages and state['feedback']['correct']):
            if state['stage'] == 'revision':
                state['revision_repaired'] = True
            state['phase'] = 'repair'
        elif state['stage'] in (content.learning_stages[-1],'revision'):
            repaired = state.get('revision_repaired', False)
            if state['stage']=='revision' and not repaired:
                state['retention'] += 1
            days = 1 if repaired else [1,3,7][min(state['retention'],2)]
            state['due_at'] = (clock+timedelta(days=days)).isoformat()
            state['phase'] = 'complete' if state['retention']>=2 else 'waiting'
            if state['phase']=='complete' and not content.repeat_revision:
                state['due_at']=None
        else:
            state['stage'] = content.learning_stages[content.learning_stages.index(state['stage'])+1]
            if state['variant']: state['variant'] += 1
            state['phase']='check';state['assisted']=False;state['feedback']=None
    elif phase == 'repair' and action == 'retry':
        state['variant'] += 1
        state['phase']='check';state['assisted']=False;state['feedback']=None
    elif phase in ('waiting','complete') and action == 'revise':
        if not state['due_at']:
            raise JourneyConflict('Reviewed delayed forms are complete')
        if clock < datetime.fromisoformat(state['due_at']):
            raise JourneyConflict('Revision is not due yet')
        state['stage']='revision';state['variant'] += 1
        state['revision_repaired'] = False
        state['phase']='check';state['assisted']=False;state['feedback']=None
    else:
        raise JourneyConflict('Action is not available at this stage')
    if state['phase'] == 'check':
        content.question(state)  # Reject unavailable/malformed content before persistence.
    return state
