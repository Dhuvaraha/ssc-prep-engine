"""Shared transition contract and independently computed Time & Work keys."""
from datetime import datetime, timedelta
from fractions import Fraction
import copy
import pytest
from app.services import teaching_journey as engine
from app.services.percentage_journey import CONTENT as percentage
from app.services.time_work_journey import CONTENT as work


@pytest.mark.parametrize('content', [percentage, work])
def test_same_contract_preserves_independence_and_delayed_repair(content):
    clock = datetime(2026,10,23)
    state = engine.initial(content)
    def act(action, selected=None):
        nonlocal state
        before = copy.deepcopy(state)
        state = engine.advance(content, state, action, selected, clock)
        assert before is not state
        return state
    act('start')
    assert set(engine.view(content,state,1)['question']) == {'id','stem','options'}
    act('hint'); act('answer',content.question(state)['answer']); act('continue')
    assert state['phase'] == 'repair'
    old_question = content.question(state)
    act('retry')
    assert content.question(state)['stem'] != old_question['stem']
    for _ in range(3):
        act('answer',content.question(state)['answer']); act('continue')
    assert state['phase'] == 'waiting'
    with pytest.raises(engine.JourneyConflict,match='not due'):
        act('revise')
    clock += timedelta(days=1)
    act('revise'); act('hint'); act('answer',content.question(state)['answer'])
    act('continue'); act('retry'); act('answer',content.question(state)['answer']); act('continue')
    assert state['retention'] == 0
    clock += timedelta(days=1)
    act('revise'); act('answer',content.question(state)['answer']); act('continue')
    assert state['retention'] == 1


def test_work_answers_follow_conservation_and_schedule_not_labels():
    for n in range(16):
        k=n+2
        expected = {
            'diagnose': 1/(Fraction(1,6*k)+Fraction(1,3*k)),
            'retry': k + (1-Fraction(k,4*k))/(Fraction(1,4*k)+Fraction(1,6*k)),
            'transfer': (1-Fraction(3*k,4*k))/(Fraction(1,6*k)+Fraction(1,12*k)),
        }
        # Independently simulate alternate days including the last partial day.
        a,b=4*(5*n+2),6*(5*n+2)
        remaining=Fraction(1); elapsed=Fraction(0); day=0
        while remaining:
            rate=Fraction(1, a if day%2==0 else b)
            duration=min(Fraction(1),remaining/rate)
            remaining-=rate*duration;elapsed+=duration;day+=1
        expected['revision']=elapsed
        for stage,answer in expected.items():
            question=work.question(dict(stage=stage,variant=n))
            actual=Fraction(question['options'][question['answer']-1].removesuffix(' days'))
            assert actual == answer
            assert len(set(question['options']))==4


def test_cross_content_resume_and_bad_content_fail_without_mutation():
    state=engine.initial(percentage)
    before=copy.deepcopy(state)
    with pytest.raises(engine.JourneyConflict,match='version'):
        engine.advance(work,state,'start',None,datetime(2026,10,23))
    assert state==before
    malformed=engine.JourneyContent(percentage.version,{},lambda _:dict(
        id='bad',stem='bad',options=['1']*4,answer=1,explanations=['x']*4,repairs=['x']*4),'hint')
    with pytest.raises(engine.JourneyConflict,match='four-option'):
        engine.advance(malformed,state,'start',None,datetime(2026,10,23))
    assert state==before


def test_view_does_not_alias_persisted_feedback_or_authored_lesson():
    state=engine.initial(work)
    view=engine.view(work,state,0)
    view['lesson']['prerequisites'].clear()
    assert work.lesson['prerequisites']


@pytest.mark.parametrize('bad', [None, {}, {'stem': ''}, {'stem': None}, {'id': ''},
    {'options': None}, {'options': [[],[],[],[]]}, {'explanations': 'abcd'}, {'answer': True}])
def test_malformed_pack_cannot_advance_or_mutate_saved_state(bad):
    state=engine.initial(work)
    snapshot=copy.deepcopy(state)
    item=work.raw_item(state)
    malformed=None if bad is None else {**item, **bad}
    if bad == {}:
        del malformed['stem']
    content=engine.JourneyContent(work.version,work.lesson,lambda _:malformed,work.hint)
    with pytest.raises(engine.JourneyConflict,match='four-option'):
        engine.advance(content,state,'start',None,datetime(2026,10,23))
    assert state==snapshot


def test_percentage_content_matches_validated_bc15582_snapshot():
    import hashlib
    import json
    items=[percentage.question(dict(stage=stage,variant=n))
           for stage in ('diagnose','retry','transfer','revision') for n in range(24)]
    assert hashlib.sha256(json.dumps(items,sort_keys=True,ensure_ascii=True).encode()).hexdigest() == "e980e1350b0d1f15dec2201f32f031d369769c8e2e3c406c43292a4baa99893a"
