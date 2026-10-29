"""Constructed models are graded evidence, not a selected prepared diagram."""
import json
from datetime import datetime
import pytest
from sqlalchemy.orm import Session
from app.services.countermodel import check,CountermodelTask
from app.services import teaching_journey as journey
from app.services.pilot_curriculum import load_unit
from app.routers import pilot_objectives as api
from app.core.config import get_settings
import test_phase_d_objectives as fixtures

setup=fixtures.setup
client=fixtures.client
enabled=fixtures.enabled
synthetic_unit=fixtures.synthetic_unit

TASK=dict(terms=['A','B'],premises=[['all','A','B']],conclusion=['all','B','A'])


@pytest.mark.parametrize('objects,valid',[([],False),([['B']],True),([['A']],False),([['A','B'],['B']],True),([['A','B']],False)])
def test_countermodel_requires_true_premises_and_false_conclusion(objects,valid):
    assert check(TASK,objects)[0] is valid


@pytest.mark.parametrize('objects',[None,'B',[['C']],[['A','A']],[[False]],[[]]*9])
def test_malformed_constructions_are_rejected(objects):
    with pytest.raises(ValueError):check(TASK,objects)


def test_constructed_response_cannot_be_replaced_by_correct_mcq():
    unit=synthetic_unit('SYL-4')
    unit.checks['independent_a'][0].construction=CountermodelTask(**TASK)
    content=unit.content();clock=datetime(2026,10,28)
    state=journey.initial(content);state.update(phase='check',stage='independent_a')
    question=content.question(state)
    pending=journey.advance(content,state,'answer',question['answer'],clock)
    assert 'construction' not in journey.view(content,state,0)['question']
    assert journey.view(content,pending,1)['question']['construction']==TASK
    with pytest.raises(journey.JourneyConflict):
        journey.advance(content,pending,'justify',None,clock,reason_selected=question['reason_answer'])
    incorrect=journey.advance(content,pending,'justify',None,clock,reason_selected=question['reason_answer'],model=[['A']])
    assert not incorrect['feedback']['independent']
    assert 'premise' in incorrect['feedback']['construction_feedback']
    correct=journey.advance(content,pending,'justify',None,clock,reason_selected=question['reason_answer'],model=[['B']])
    assert correct['feedback']['independent']
    assert correct['history'][-1]['model']==[['B']]
    assert not pending['history']


def test_optional_construction_preserves_preexisting_unit_digest():
    import hashlib
    unit=load_unit('PCT-1')
    old=unit.model_dump(exclude={'subject_review','teaching_review','review_digest'})
    for checks in old['checks'].values():
        for q in checks:
            q.pop('construction');q.pop('positional_figure_options')
    expected=hashlib.sha256(json.dumps(old,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    assert unit.digest()==expected


def test_authored_construction_tasks_have_small_countermodels():
    from app.content.syllogism import evaluate
    for checks in load_unit('SYL-4').checks.values():
        for q in checks:
            task=q.construction
            assert task is not None
            result=evaluate(task.premises,task.conclusion)
            assert result['consistent'] and not result['must_follow']
            assert check(task,result['counterexample'])[0]


def test_api_constructed_evidence_is_persisted_and_stale_submission_denied(enabled,setup,monkeypatch):
    client,units=enabled
    unit=units['SYL-4']
    unit.checks['entry'][0].construction=CountermodelTask(**TASK)
    unit.review_digest=unit.digest()
    release=json.loads(get_settings().phase_d_release_manifest)
    release['SYL-4']['digests']=[unit.digest()]
    monkeypatch.setattr(get_settings(),'phase_d_release_manifest',json.dumps(release))
    path='/api/v1/learn/pilot/SYL-4'
    client.post(path+'/actions',json=dict(expected_revision=0,action='start'))
    state=journey.initial(unit.content());question=unit.content().question(state)
    pending=client.post(path+'/actions',json=dict(expected_revision=1,action='answer',selected=question['answer']))
    assert pending.status_code==200
    assert client.get(path).json()==pending.json()
    bad=client.post(path+'/actions',json=dict(expected_revision=2,action='justify',reason_selected=question['reason_answer'],model=[['UNKNOWN']]))
    assert bad.status_code==409
    assert client.get(path).json()['revision']==2
    payload=dict(expected_revision=2,action='justify',reason_selected=question['reason_answer'],model=[['B']])
    assert client.post(path+'/actions',json=payload).status_code==200
    assert client.post(path+'/actions',json=payload).status_code==409
    with Session(setup) as db:
        saved=json.loads(db.get(api.ObjectiveProgress,(1,1,'SYL-4')).state)
        assert saved['history'][-1]['construction_correct']
        assert saved['history'][-1]['model']==[['B']]
