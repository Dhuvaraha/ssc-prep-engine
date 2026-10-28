"""Synthetic reviewed objective fixtures, never production release evidence."""
import json
from datetime import datetime
import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text
import test_percentage_pilot_api as fixtures
from app.core.config import get_settings
from app.routers import pilot_objectives as api
from app.services.pilot_curriculum import ObjectiveUnit, OBJECTIVES, STAGES
from app.services import teaching_journey as journey
from app.phase_d_migration import migrate
from app.access_models import ContentSource, SourceGrant
from app.core.security import create_access_token
from app.models import MockAttempt

def advance(content,state,action,selected,clock,**kwargs):
    # Exercise both persisted protocol transitions in pure engine assertions.
    if action=='answer' and content.reason_after_answer and state['phase']=='check':
        pending=journey.advance(content,state,action,selected,clock,**kwargs)
        return journey.advance(content,pending,'justify',None,clock,**kwargs)
    return journey.advance(content,state,action,selected,clock,**kwargs)


setup=fixtures.setup
client=fixtures.client


def synthetic_unit(oid='PCT-1'):
    checks={}
    for stage in STAGES:
        checks[stage]=[dict(id=f'{oid}-{stage}-{n}',family='synthetic',context=f'{stage}-{n}',
            stem=f'Synthetic {stage} form {n}: what is 1+1?',options=['1','2','3','4'],answer=2,
            explanations=['Too small','1+1=2','Too large','Counts twice'],
            repairs=['Add both units','Check the units','Count each once','Do not double count'],
            reason_prompt='Which calculation supports your answer?',reason_options=['1+1=2','1+1=4'],
            reason_answer=1,reason_explanation='Adding two single units makes two.') for n in range(4 if stage=='revision' else 2)]
    unit=ObjectiveUnit(objective_id=oid,prerequisites=['Synthetic counting'],explanation='Test-only fixture',
        worked=[dict(action='Count one',justification='One unit'),dict(action='Add one',justification='Two units')],
        hint='Count once',shortcut='Add',limitation='Synthetic only',checks=checks,sources=['synthetic-only'])
    unit.subject_review='Synthetic test, not educational approval'
    unit.teaching_review='Synthetic test, not educational approval'
    unit.review_digest=unit.digest()
    return unit


@pytest.fixture
def enabled(client,setup,monkeypatch):
    units={oid:synthetic_unit(oid) for oid in OBJECTIVES}
    migrate(setup);migrate(setup)
    monkeypatch.setattr(api,'load_unit',units.get)
    monkeypatch.setattr(get_settings(),'phase_d_pilot_enabled',True)
    manifest={oid:dict(source_ids=['original-fixture'],digests=[unit.digest()],access_reference='synthetic only') for oid,unit in units.items()}
    monkeypatch.setattr(get_settings(),'phase_d_release_manifest',json.dumps(manifest))
    return client,units


def test_fixed_scope_and_real_content_not_inferred_from_counts():
    assert len(OBJECTIVES)==45
    assert {oid.split('-')[0] for oid in OBJECTIVES}=={'PCT','TW','SYL','MIR','ENG','RC','POL','PHY'}
    unit=synthetic_unit()
    assert unit.reviewed()
    unit.checks['independent_a'][0].stem+=' changed'
    assert not unit.reviewed()


def test_guided_and_guess_and_reason_evidence_are_not_independent():
    content=synthetic_unit().content()
    state=journey.initial(content)
    clock=datetime(2026,10,27)
    state=advance(content,state,'start',None,clock)
    for stage in ('entry','faded'):
        assert state['stage']==stage
        state=advance(content,state,'answer',content.question(state)['answer'],clock,reason_selected=content.question(state)['reason_answer'])
        assert not state['feedback']['independent']
        state=advance(content,state,'continue',None,clock)
    assert state['stage']=='independent_a'
    first=content.question(state)
    wrong_reason=advance(content,state,'answer',first['answer'],clock,reason_selected=(content.question(state)['reason_answer']%2)+1)
    assert not wrong_reason['feedback']['correct']
    guess=advance(content,state,'answer',first['answer'],clock,reason_selected=first['reason_answer'],guessed=True)
    assert not guess['feedback']['independent']
    independent=advance(content,state,'answer',first['answer'],clock,reason_selected=content.question(state)['reason_answer'])
    assert independent['feedback']['independent']
    assert independent['history'][-1]['question_id']==first['id']


def test_objectives_are_isolated_and_snapshot_resume_is_pinned(enabled,setup):
    client,units=enabled
    base='/api/v1/learn/pilot/'
    response=client.post(base+'PCT-1/actions',json=dict(expected_revision=0,action='start'))
    assert response.status_code==200,response.text
    assert client.get(base+'TW-1').json()['phase']=='teach'
    assert client.get(base+'PCT-1').json()==response.json()
    units['PCT-1'].checks['entry'][0].stem='Edited candidate must not replace saved session'
    assert client.get(base+'PCT-1').json()==response.json()
    migrate(setup)
    assert client.get(base+'PCT-1').json()==response.json()
    stale=client.post(base+'PCT-1/actions',json=dict(expected_revision=0,action='hint'))
    assert stale.status_code==409
    with Session(setup) as db:
        assert db.get(api.ObjectiveProgress,(1,1,'TW-1')) is None


def test_unreviewed_unreleased_and_invalid_manifest_fail_closed(enabled,monkeypatch):
    client,units=enabled
    base='/api/v1/learn/pilot/'
    units['TW-1'].teaching_review=''
    assert client.get(base+'TW-1').status_code==404
    units['POL-1'].subject_review=''
    assert client.get(base+'POL-1').status_code==404
    assert client.get(base+'../../secrets').status_code==404
    monkeypatch.setattr(get_settings(),'phase_d_release_manifest','[]')
    assert client.get(base+'PCT-1').status_code==404


def test_no_keys_or_unseen_delayed_forms_in_response(enabled):
    client,_=enabled
    response=client.post('/api/v1/learn/pilot/PCT-1/actions',json=dict(expected_revision=0,action='start'))
    question=response.json()['question']
    assert set(question)=={'id','stem','options','requires_reason'}
    assert 'revision' not in question['stem']


def test_exhausted_fresh_pool_cannot_reaward_or_mutate_progress():
    content=synthetic_unit().content()
    state=journey.initial(content)
    state['stage']='independent_a';state['phase']='check'
    clock=datetime(2026,10,27)
    for _ in range(2):
        q=content.question(state)
        state=advance(content,state,'answer',q['answer'],clock,reason_selected=(content.question(state)['reason_answer']%2)+1)
        state=advance(content,state,'continue',None,clock)
        if len(state['history'])==1:
            state=advance(content,state,'retry',None,clock)
    before=json.dumps(state,sort_keys=True)
    with pytest.raises(journey.JourneyConflict,match='No fresh'):
        advance(content,state,'retry',None,clock)
    assert json.dumps(state,sort_keys=True)==before


def test_objective_postgres_rls_and_direct_client_denial(enabled,setup):
    if setup.dialect.name!='postgresql':
        pytest.skip('PostgreSQL role check')
    with setup.connect() as connection:
        assert connection.scalar(text("SELECT relrowsecurity FROM pg_class WHERE oid='pilot_objective_progress'::regclass"))
        for role in connection.scalars(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")):
            assert not connection.scalar(text("SELECT has_table_privilege(:role,'pilot_objective_progress','SELECT,INSERT,UPDATE,DELETE')"),{'role':role})


def test_rebinding_release_cannot_bypass_pinned_source_revocation(enabled,setup,monkeypatch):
    client,units=enabled
    path='/api/v1/learn/pilot/PCT-1'
    assert client.post(path+'/actions',json=dict(expected_revision=0,action='start')).status_code==200
    with Session(setup) as db:
        db.add(ContentSource(id='replacement',exam_id=1,private_use_approved=True,approval_reference='synthetic'))
        db.flush()
        db.add(SourceGrant(user_id=1,source_id='replacement',active=True))
        db.get(SourceGrant,(1,'original-fixture')).active=False
        db.commit()
    manifest={'PCT-1':dict(source_ids=['replacement'],digests=[units['PCT-1'].digest()],access_reference='synthetic')}
    monkeypatch.setattr(get_settings(),'phase_d_release_manifest',json.dumps(manifest))
    assert client.get(path).status_code==404
    assert client.post(path+'/actions',json=dict(expected_revision=1,action='hint')).status_code==404


def test_finite_revision_completion_does_not_promise_unavailable_forms():
    from datetime import timedelta
    unit=synthetic_unit();content=unit.content();clock=datetime(2026,10,27)
    state=journey.initial(content)
    state=advance(content,state,'start',None,clock)
    for _ in range(4):
        state=advance(content,state,'answer',content.question(state)['answer'],clock,reason_selected=content.question(state)['reason_answer'])
        state=advance(content,state,'continue',None,clock)
    for days in (1,3):
        clock+=timedelta(days=days)
        state=advance(content,state,'revise',None,clock)
        state=advance(content,state,'answer',content.question(state)['answer'],clock,reason_selected=content.question(state)['reason_answer'])
        state=advance(content,state,'continue',None,clock)
    assert state['phase']=='complete' and state['due_at'] is None
    with pytest.raises(journey.JourneyConflict,match='complete'):
        advance(content,state,'revise',None,clock)


def test_one_delayed_form_cannot_pass_structural_gate():
    data=synthetic_unit().model_dump()
    data['checks']['revision']=data['checks']['revision'][:1]
    with pytest.raises(ValueError,match='Two held-out'):
        ObjectiveUnit.model_validate(data)


def test_rotated_figure_and_full_passage_survive_feedback():
    unit=synthetic_unit()
    scene=dict(description='A triangle at the listed coordinates',polygons=[[dict(x=1,y=1),dict(x=3,y=1),dict(x=1,y=2)]],dots=[],lines=[])
    data=unit.model_dump()
    check=data['checks']['independent_a'][0]
    check['passage']='An original complete passage for synthetic feedback verification.'
    check['figure']=dict(stem=scene,options=[{**scene,'description':f'Figure {i}'} for i in range(4)])
    content=ObjectiveUnit.model_validate(data).content()
    state=journey.initial(content);state.update(phase='check',stage='independent_a',variant=1)
    question=content.question(state)
    assert question['figure']['options'][0]['description']==f"Figure {int(question['options'][0])-1}"
    after=advance(content,state,'answer',question['answer'],datetime(2026,10,27),reason_selected=content.question(state)['reason_answer'])
    assert after['feedback']['figure']==question['figure']
    assert after['feedback']['passage']==question['passage']


def test_account_and_active_assessment_boundaries_preserve_saved_progress(enabled,setup):
    client,_=enabled
    path='/api/v1/learn/pilot/PCT-1'
    saved=client.post(path+'/actions',json=dict(expected_revision=0,action='start')).json()
    client.headers['Authorization']='Bearer '+create_access_token('2')
    assert client.get(path).json()['phase']=='teach'
    assert client.post(path+'/actions',json=dict(expected_revision=1,action='hint')).status_code==409
    client.headers['Authorization']='Bearer '+create_access_token('1')
    with Session(setup) as db:
        db.add(MockAttempt(user_id=1,exam_id=1,mode='full',duration_minutes=60))
        db.commit()
    assert client.get(path).status_code==409
    assert client.post(path+'/actions',json=dict(expected_revision=1,action='hint')).status_code==409
    with Session(setup) as db:
        row=db.get(api.ObjectiveProgress,(1,1,'PCT-1'))
        assert row.revision==saved['revision']
        assert not json.loads(row.state)['assisted']
        assert db.get(api.ObjectiveProgress,(2,1,'PCT-1')) is None


@pytest.mark.parametrize('existing',[False,True])
def test_postgres_concurrent_objective_actions_have_one_winner(enabled,setup,existing):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    if setup.dialect.name!='postgresql':
        pytest.skip('Production PostgreSQL row-lock concurrency')
    client,_=enabled
    path='/api/v1/learn/pilot/PCT-1'
    if existing:
        assert client.post(path+'/actions',json=dict(expected_revision=0,action='start')).status_code==200
    barrier=Barrier(2)
    def submit(_):
        barrier.wait(timeout=10)
        return client.post(path+'/actions',json=dict(expected_revision=int(existing),action='hint' if existing else 'start')).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(submit,range(2)))
    assert sorted(results)==[200,409]
    assert client.get(path).json()['revision']==int(existing)+1


def test_answer_is_persistently_locked_before_reason_choices_are_revealed(enabled,setup):
    client,_=enabled
    path='/api/v1/learn/pilot/PCT-1'
    start=client.post(path+'/actions',json=dict(expected_revision=0,action='start')).json()
    assert 'reason_options' not in start['question']
    pending=client.post(path+'/actions',json=dict(expected_revision=1,action='answer',selected=1,reason_selected=1)).json()
    assert pending['phase']=='justify' and pending['feedback'] is None
    assert client.get(path).json()==pending
    assert pending['question']['reason_options']
    assert client.post(path+'/actions',json=dict(expected_revision=2,action='justify',selected=2,reason_selected=1)).status_code==409
    assert client.post(path+'/actions',json=dict(expected_revision=2,action='answer',selected=2)).status_code==409
    finished=client.post(path+'/actions',json=dict(expected_revision=2,action='justify',reason_selected=1,guessed=True)).json()
    assert finished['phase']=='feedback' and finished['feedback']['selected']==1
    with Session(setup) as db:
        state=json.loads(db.get(api.ObjectiveProgress,(1,1,'PCT-1')).state)
        assert len(state['history'])==1 and state['history'][0]['guessed']
