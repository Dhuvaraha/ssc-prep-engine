"""Reusable teaching transitions; authorization and persistence remain in adapters."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable


class JourneyConflict(ValueError):
    pass


@dataclass(frozen=True)
class JourneyContent:
    version: str
    lesson: dict
    raw_item: Callable[[dict], dict]
    hint: str

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
        shift = state['variant'] % 4
        for field in ('options','explanations','repairs'):
            result[field] = result[field][shift:] + result[field][:shift]
        result['answer'] = (result['answer'] - 1 - shift) % 4 + 1
        return result


def initial(content):
    return dict(content_version=content.version, phase='teach', stage='diagnose', variant=0,
                assisted=False, feedback=None, due_at=None, retention=0, history=[])


def require_version(content, state):
    if state['content_version'] != content.version:
        raise JourneyConflict('Content version requires reviewed migration')


def view(content, state, revision):
    require_version(content, state)
    result = deepcopy({k:v for k,v in state.items() if k != 'history'})
    result.update(revision=revision, lesson=deepcopy(content.lesson),
        evidence_label='Pilot near-transfer and retention evidence only; not exam readiness.')
    if state['phase'] == 'check':
        q = content.question(state)
        result['question'] = {k:q[k] for k in ('id','stem','options')}
        result['hint'] = content.hint if state['assisted'] else None
    return result


def advance(content, saved_state, action, selected, clock):
    require_version(content, saved_state)
    state = deepcopy(saved_state)
    if selected is not None and (type(selected) is not int or selected not in (1,2,3,4)):
        raise JourneyConflict('Choose one of the four options')
    phase, action = state['phase'], action
    if phase == 'teach' and action == 'start':
        state['phase'] = 'check'
    elif phase == 'check' and action == 'hint':
        state['assisted'] = True
    elif phase == 'check' and action == 'answer' and selected is not None:
        q = content.question(state)
        independent = selected == q['answer'] and not state['assisted']
        state['feedback'] = dict(correct=selected==q['answer'], independent=independent,
            selected=selected,correct_option=q['answer'],options=q['options'],
            explanations=q['explanations'],repair=q['repairs'][selected-1],stem=q['stem'])
        state['history'].append(dict(stage=state['stage'],variant=state['variant'],selected=selected,
            independent=independent,assisted=state['assisted'],at=clock.isoformat()))
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
            state['due_at'] = (clock+timedelta(days=days)).isoformat()
            state['phase'] = 'complete' if state['retention']>=2 else 'waiting'
        else:
            state['stage'] = 'retry' if state['stage']=='diagnose' else 'transfer'
            if state['variant']: state['variant'] += 1
            state['phase']='check';state['assisted']=False;state['feedback']=None
    elif phase == 'repair' and action == 'retry':
        state['variant'] += 1
        state['phase']='check';state['assisted']=False;state['feedback']=None
    elif phase in ('waiting','complete') and action == 'revise':
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
