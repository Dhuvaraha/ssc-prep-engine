"""Real HTTP, isolated data and clock: no production grants or time overrides."""
import json
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session
import test_phase_b_integration as fixtures
from app.main import app
from app.db import get_db
from app.core.config import get_settings
from app.core.security import create_access_token
from app.access_models import CourseGrant, SourceGrant
from app.models import User, Question, MockAttempt
from app.routers import percentage_pilot as pilot
from app.percentage_pilot_migration import migrate

setup = fixtures.setup


@pytest.fixture
def client(setup, monkeypatch):
    migrate(setup); migrate(setup)
    settings = get_settings()
    for name, value in [('percentage_pilot_enabled', True),
                        ('percentage_pilot_source_id', 'original-fixture'),
                        ('percentage_pilot_review_reference', 'Synthetic test only')]:
        monkeypatch.setattr(settings, name, value)
    with Session(setup) as db:
        db.add(User(id=2, email='other@example.invalid', password_hash='no-login'))
        db.flush()
        for uid in (1, 2):
            db.add(CourseGrant(user_id=uid, exam_id=1, active=True))
            db.add(SourceGrant(user_id=uid, source_id='original-fixture', active=True))
        db.commit()
    def database():
        with Session(setup) as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = database
    # No production lifespan is invoked.
    with_client = TestClient(app)
    with_client.headers['Authorization'] = 'Bearer ' + create_access_token('1')
    yield with_client
    with_client.close()
    app.dependency_overrides.clear(); app.dependency_overrides.update(previous)


URL = '/api/v1/learn/percentage-pilot'


def correct(client, engine):
    with Session(engine) as db:
        state = json.loads(db.get(pilot.PercentageProgress, (1, 1)).state)
    return action(client, 'answer', pilot.item(state)['answer'])


def action(client, name, selected=None):
    before = client.get(URL)
    assert before.status_code == 200, before.text
    response = client.post(URL+'/actions', json=dict(
        expected_revision=before.json()['revision'], action=name, selected=selected))
    assert response.status_code == 200, response.text
    return response.json()


def test_persistent_repair_independent_transfer_and_due_retention(client, setup, monkeypatch):
    clock = datetime(2026, 10, 23)
    monkeypatch.setattr(pilot, 'now', lambda: clock)
    first = action(client, 'start')
    assert set(first['question']) == {'id', 'stem', 'options'}
    wrong = action(client, 'answer', 1)
    assert not wrong['feedback']['independent']
    assert len(wrong['feedback']['explanations']) == 4
    assert action(client, 'continue')['phase'] == 'repair'
    fresh = action(client, 'retry')
    assert fresh['question']['stem'] != first['question']['stem']
    assert client.get(URL).json() == fresh
    action(client, 'hint')
    assert not correct(client, setup)['feedback']['independent']
    action(client, 'continue'); action(client, 'retry')
    assert correct(client, setup)['feedback']['independent']
    retry = action(client, 'continue')
    assert retry['stage'] == 'retry'
    correct(client, setup); action(client, 'continue')
    correct(client, setup)
    waiting = action(client, 'continue')
    assert waiting['phase'] == 'waiting'
    migrate(setup)
    assert client.get(URL).json() == waiting
    assert waiting['due_at'] == (clock+timedelta(days=1)).isoformat()
    denied = client.post(URL+'/actions', json=dict(expected_revision=waiting['revision'], action='revise'))
    assert denied.status_code == 409
    assert client.get(URL).json() == waiting
    for days, retention in [(1, 1), (3, 2)]:
        clock += timedelta(days=days)
        check = action(client, 'revise')
        assert check['question']['stem'] != retry['question']['stem']
        correct(client, setup)
        result = action(client, 'continue')
        assert result['retention'] == retention
    assert result['phase'] == 'complete'
    with Session(setup) as db:
        history = json.loads(db.get(pilot.PercentageProgress, (1, 1)).state)['history']
        assert len(history) == 7
        assert db.scalar(select(Question.question_text)) == 'Original fixture 2+2?'


def test_stale_actions_owner_isolation_and_revocation(client, setup):
    started = action(client, 'start')
    stale = client.post(URL+'/actions', json=dict(expected_revision=0, action='answer', selected=2))
    assert stale.status_code == 409
    assert client.get(URL).json() == started
    other = client.get(URL, headers={'Authorization': 'Bearer '+create_access_token('2')})
    assert other.json()['phase'] == 'teach'
    with Session(setup) as db:
        db.get(SourceGrant, (1, 'original-fixture')).active = False
        db.commit()
    assert client.get(URL).status_code == 404
    assert client.post(URL+'/actions', json=dict(expected_revision=1, action='hint')).status_code == 404


def test_feature_review_and_version_gates(client, setup, monkeypatch):
    monkeypatch.setattr(get_settings(), 'percentage_pilot_enabled', False)
    assert client.get(URL).status_code == 404
    monkeypatch.setattr(get_settings(), 'percentage_pilot_enabled', True)
    monkeypatch.setattr(get_settings(), 'percentage_pilot_review_reference', '')
    assert client.get(URL).status_code == 404
    monkeypatch.setattr(get_settings(), 'percentage_pilot_review_reference', 'Synthetic')
    action(client, 'start')
    with Session(setup) as db:
        row = db.get(pilot.PercentageProgress, (1, 1))
        state = json.loads(row.state); state['content_version'] = 'old'
        row.state = json.dumps(state); db.commit()
    assert client.post(URL+'/actions', json=dict(expected_revision=1, action='hint')).status_code == 409


def test_postgres_pilot_table_has_rls(setup):
    if setup.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL-only RLS assertion')
    migrate(setup)
    with setup.connect() as connection:
        assert connection.scalar(text("SELECT relrowsecurity FROM pg_class WHERE oid='percentage_pilot_progress'::regclass"))
        for role in connection.scalars(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")):
            assert not connection.scalar(text("SELECT has_table_privilege(:role, 'percentage_pilot_progress', 'SELECT,INSERT,UPDATE,DELETE')"), {'role': role})


def test_repaired_revision_requires_another_delayed_check(client, setup, monkeypatch):
    clock = datetime(2026, 10, 23)
    monkeypatch.setattr(pilot, 'now', lambda: clock)
    action(client, 'start')
    for _ in range(3):
        correct(client, setup); action(client, 'continue')
    clock += timedelta(days=1)
    action(client, 'revise'); action(client, 'hint')
    correct(client, setup); action(client, 'continue'); action(client, 'retry')
    correct(client, setup)
    repaired = action(client, 'continue')
    assert repaired['retention'] == 0
    assert repaired['due_at'] == (clock+timedelta(days=1)).isoformat()
    clock += timedelta(days=1)
    action(client, 'revise'); correct(client, setup)
    assert action(client, 'continue')['retention'] == 1


def test_assessment_blocks_teaching_without_changing_history(client, setup):
    with Session(setup) as db:
        db.add(MockAttempt(user_id=1, exam_id=1, mode='full', duration_minutes=60))
        db.commit()
    assert client.get(URL).status_code == 409
    assert client.post(URL+'/actions', json=dict(expected_revision=0, action='start')).status_code == 409
    with Session(setup) as db:
        assert db.get(pilot.PercentageProgress, (1, 1)) is None
        assert db.scalar(select(MockAttempt.status)) == 'in_progress'


def test_concurrent_first_actions_have_one_winner(client, setup):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    if setup.dialect.name != 'postgresql':
        pytest.skip('Production PostgreSQL row-lock concurrency')
    barrier = Barrier(2)
    def submit():
        barrier.wait(timeout=10)
        return client.post(URL+'/actions', json=dict(expected_revision=0, action='start')).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: submit(), range(2)))
    assert sorted(results) == [200, 409]
    assert client.get(URL).json()['revision'] == 1


def test_generated_checks_change_keys_and_never_repeat_original_transfer():
    original = pilot.item(dict(stage='transfer', variant=0))
    keys = set()
    for variant in range(1, 25):
        question = pilot.item(dict(stage='transfer', variant=variant))
        keys.add(question['answer'])
        assert len(set(question['options'])) == 4
        assert set(question['options']) != set(original['options'])
        assert 'compare receipt with cost' in question['explanations'][question['answer']-1]
    assert keys == {1, 2, 3, 4}
