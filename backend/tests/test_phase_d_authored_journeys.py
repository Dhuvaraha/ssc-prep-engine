"""Actual draft payloads through HTTP under synthetic authorization only.

This proves transport/state integration, not educational or publication acceptance.
Keys are read as test inputs; subject correctness is reviewed independently.
"""
import json
import pytest
from datetime import datetime

from sqlalchemy.orm import Session

import test_phase_d_objectives as fixtures
from app.content.syllogism import evaluate
from app.core.config import get_settings
from app.routers import pilot_objectives as api
from app.services.pilot_curriculum import DATA, load_unit

setup=fixtures.setup
client=fixtures.client
enabled=fixtures.enabled


@pytest.mark.parametrize('objective_id',sorted(p.stem for p in (DATA/'phase_d_units').glob('*.json')))
def test_authored_payloads_persist_repair_fresh_retry_and_delayed_retention(enabled,setup,monkeypatch,objective_id):
    client,units=enabled
    clock=datetime(2026,10,28)
    monkeypatch.setattr(api,'now',lambda:clock)
    manifest=json.loads(get_settings().phase_d_release_manifest)
    authored=[]
    for path in [DATA/'phase_d_units'/(objective_id+'.json')]:
        unit=load_unit(path.stem)
        assert not unit.reviewed(), 'Draft files must not acquire test approval stamps'
        unit.subject_review='Synthetic integration only, not subject approval'
        unit.teaching_review='Synthetic integration only, not teaching approval'
        unit.review_digest=unit.digest()
        units[path.stem]=unit
        manifest[path.stem]['digests']=[unit.digest()]
        authored.append(unit)
    monkeypatch.setattr(get_settings(),'phase_d_release_manifest',json.dumps(manifest))

    for unit in authored:
        oid=unit.objective_id
        path='/api/v1/learn/pilot/'+oid

        def action(name,**fields):
            before=client.get(path)
            assert before.status_code==200,(oid,before.text)
            response=client.post(path+'/actions',json=dict(
                expected_revision=before.json()['revision'],action=name,**fields))
            assert response.status_code==200,(oid,name,response.text)
            assert client.get(path).json()==response.json(),(oid,'resume')
            return response.json()

        def answer(correct=True):
            with Session(setup) as db:
                saved=json.loads(db.get(api.ObjectiveProgress,(1,1,oid)).state)
            question=unit.content().question(saved)
            pending=action('answer',selected=question['answer'] if correct else question['answer']%4+1)
            assert pending['phase']=='justify'
            fields=dict(reason_selected=question['reason_answer'])
            if question.get('construction'):
                task=question['construction']
                fields['model']=evaluate(task['premises'],task['conclusion'])['counterexample']
            feedback=action('justify',**fields)['feedback']
            assert feedback['correct'] is correct
            for key in ('passage','figure','diagram'):
                if key in question:
                    assert feedback[key]==question[key],(oid,key)
            return feedback

        action('start')
        for stage in ('entry','faded'):
            feedback=answer()
            assert not feedback['independent'],(oid,stage)
            action('continue')
        answer(False)
        assert action('continue')['phase']=='repair'
        action('retry')
        assert answer()['independent']
        action('continue')
        assert answer()['independent']
        waiting=action('continue')
        assert waiting['phase']=='waiting'
        early=client.post(path+'/actions',json=dict(expected_revision=waiting['revision'],action='revise'))
        assert early.status_code==409
        assert client.get(path).json()==waiting

        clock=datetime.fromisoformat(waiting['due_at'])
        action('revise');answer(False)
        assert action('continue')['phase']=='repair'
        action('retry');answer()
        waiting=action('continue')
        assert waiting['retention']==0,(oid,'repair is not delayed recall')
        for expected in (1,2):
            clock=datetime.fromisoformat(waiting['due_at'])
            action('revise');answer()
            waiting=action('continue')
            assert waiting['retention']==expected
        assert waiting['phase']=='complete' and waiting['due_at'] is None
        with Session(setup) as db:
            saved=json.loads(db.get(api.ObjectiveProgress,(1,1,oid)).state)
            identities=[event['question_id'] for event in saved['history']]
            assert len(identities)==len(set(identities)),oid
        assert not load_unit(oid).reviewed()
