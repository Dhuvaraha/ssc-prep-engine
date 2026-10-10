"""SEC/INT fixtures are original synthetic content; no production records."""
from datetime import datetime
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.access_models import ContentBinding, ContentSource, CourseGrant, SourceGrant
from app.core.security import create_access_token
from app.db import Base, get_db
from app.main import app
from app.models import Exam, Lesson, MockAttempt, Question, QuestionAttempt, QuestionOption, Subject, Topic, User
from app.models import MockAttemptQuestion
from app.access_models import AssessmentAsset, AssessmentDelivery, ContentExposure
from app.services.practice_integrity import question_digest


@pytest.fixture
def secured():
    test_url = os.environ.get("PHASE_A_TEST_DATABASE_URL")
    admin_engine = None
    schema = None
    if test_url:
        parsed = make_url(test_url)
        if parsed.host not in {"127.0.0.1", "localhost"} or parsed.database != "ssc_phase_a_test":
            raise RuntimeError("Synthetic tests require loopback database ssc_phase_a_test")
        schema = "phase_a_" + uuid4().hex
        admin_engine = create_engine(test_url)
        with admin_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(test_url, connect_args={"options":f"-csearch_path={schema}"})
    else:
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory() as db:
        exam = Exam(slug="ssc-cgl-tier-1", name="Synthetic CGL", duration_minutes=60)
        db.add(exam); db.flush()
        subject = Subject(exam_id=exam.id, slug="quant", name="Synthetic Quant")
        user = User(email="synthetic@example.invalid", password_hash="unused")
        outsider = User(email="outsider@example.invalid", password_hash="unused")
        db.add_all([subject, user, outsider]); db.flush()
        topic = Topic(subject_id=subject.id, slug="synthetic", name="Synthetic")
        db.add(topic); db.flush()
        lesson = Lesson(topic_id=topic.id, title="Synthetic", intro="Original fixture", concept="SYNTHETIC_PRIVATE_LESSON")
        db.add(lesson)
        source = ContentSource(id="synthetic-original", exam_id=exam.id, private_use_approved=True, public_use_approved=False, approval_reference="synthetic-fixture-review")
        db.add(source); db.flush()
        db.add_all([CourseGrant(user_id=user.id, exam_id=exam.id, active=True), SourceGrant(user_id=user.id, source_id=source.id, active=True)])
        questions = []
        for i in range(3):
            q = Question(exam_id=exam.id, subject_id=subject.id, topic_id=topic.id, question_text=f"Synthetic {i}+1?", correct_option=1, explanation="SYNTHETIC_PRIVATE_ANSWER", difficulty=i+1, verification_status="verified", visibility="private")
            db.add(q); db.flush()
            db.add_all([QuestionOption(question_id=q.id, position=j, text=str(i+j)) for j in range(1,5)])
            if i < 2:
                db.add(ContentBinding(resource_kind="question", resource_id=q.id, source_id=source.id))
            questions.append(q.id)
        db.add(ContentBinding(resource_kind="lesson", resource_id=lesson.id, source_id=source.id))
        db.commit()
        ids = dict(user=user.id, outsider=outsider.id, exam=exam.id, topic=topic.id, lesson=lesson.id, questions=questions)
    def override():
        with factory() as session:
            yield session
    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    headers = {"Authorization": "Bearer " + create_access_token(str(ids["user"]))}
    yield client, factory, ids, headers
    app.dependency_overrides.clear()
    engine.dispose()
    if admin_engine:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin_engine.dispose()


def test_sec_01_02_anonymous_and_ungranted(secured):
    client, _, ids, _ = secured
    for path in [f'/learn/topics/{ids["topic"]}/package', f'/learn/topics/{ids["topic"]}/lessons', f'/learn/lessons/{ids["lesson"]}']:
        response = client.get('/api/v1'+path)
        assert response.status_code == 401
        assert 'SYNTHETIC_PRIVATE' not in response.text
        assert response.headers['cache-control'] == 'private, no-store'
        response = client.get('/api/v1'+path, headers={"Authorization": "Bearer " + create_access_token(str(ids['outsider']))})
        assert response.status_code == 404


def test_sec_03_04_filters_before_selection(secured):
    client, _, ids, headers = secured
    response = client.get(f'/api/v1/learn/topics/{ids["topic"]}/package', headers=headers)
    assert response.status_code == 200, response.text
    assert [q['id'] for q in response.json()['solved_examples']] == ids['questions'][:2]
    response = client.get('/api/v1/practice/questions?mode=mixed&limit=3', headers=headers)
    assert response.status_code == 200, response.text
    assert all(q['id'] in ids['questions'][:2] for q in response.json())
    assert 'correct_option' not in response.text


def test_int_01_02_03_broad_lock(secured):
    client, factory, ids, headers = secured
    with factory() as db:
        db.add(MockAttempt(user_id=ids['user'], exam_id=ids['exam'], mode='mini', status='in_progress', duration_minutes=4, started_at=datetime.utcnow()))
        db.commit()
    for path in [f'/learn/topics/{ids["topic"]}/package', '/revision/queue', '/practice/questions', '/diagnostics/baseline']:
        response = client.get('/api/v1'+path, headers=headers)
        assert response.status_code == 409, response.text
        assert response.json()['detail'] == 'ASSESSMENT_IN_PROGRESS'


def test_int_07_08_delivery_assistance_and_retry(secured):
    client, factory, ids, headers = secured
    questions = client.get('/api/v1/practice/questions?mode=mixed&limit=1', headers=headers).json()
    q = questions[0]
    token = q['delivery_token']
    assist = client.post(f'/api/v1/practice/deliveries/{token}/assist?action=compare', headers=headers)
    assert assist.status_code == 200, assist.text
    payload = dict(question_id=q['id'], delivery_token=token, selected_option=1, confidence=3, used_hint=False, time_seconds=10)
    first = client.post('/api/v1/practice/submit', headers=headers, json=payload)
    assert first.status_code == 200, first.text
    assert client.post('/api/v1/practice/submit', headers=headers, json=payload).json() == first.json()
    assert client.post('/api/v1/practice/submit', headers=headers, json={**payload, 'selected_option':2}).status_code == 409
    with factory() as db:
        attempts = list(db.scalars(select(QuestionAttempt)))
        assert len(attempts) == 1
        assert attempts[0].used_hint is True


@pytest.mark.parametrize("action", ["hint", "explain", "shortcut", "compare", "trap", "example"])
def test_int_07_all_assistance_actions_are_authoritative(secured, action):
    client, factory, _, headers = secured
    q = client.get('/api/v1/practice/questions?mode=mixed&limit=1', headers=headers).json()[0]
    assert client.post(f'/api/v1/practice/deliveries/{q["delivery_token"]}/assist?action={action}', headers=headers).status_code == 200
    assert client.post('/api/v1/practice/submit', headers=headers, json=dict(question_id=q['id'], delivery_token=q['delivery_token'], selected_option=1, used_hint=False, time_seconds=2)).status_code == 200
    with factory() as db:
        assert db.scalar(select(QuestionAttempt)).used_hint


def synthetic_mock(factory, ids, *, mode='full', status='in_progress', elapsed=0):
    from datetime import timedelta
    with factory() as db:
        attempt = MockAttempt(user_id=ids['user'], exam_id=ids['exam'], mode=mode, status=status, duration_minutes=60 if mode == 'full' else 4, started_at=datetime.utcnow()-timedelta(seconds=elapsed))
        db.add(attempt); db.flush()
        for index, qid in enumerate(ids['questions'][:2]):
            db.add(MockAttemptQuestion(attempt_id=attempt.id, question_id=qid, position=index+1, section_slug=['reasoning','general-awareness'][index]))
            q = db.get(Question, qid)
            db.add(AssessmentDelivery(attempt_id=attempt.id, question_id=qid, content_digest=question_digest(q), correct_option=q.correct_option))
        db.commit()
        return attempt.id


def test_int_01_02_03_every_answer_route_no_writes(secured):
    client, factory, ids, headers = secured
    q = client.get('/api/v1/practice/questions?mode=mixed&limit=1', headers=headers).json()[0]
    old = synthetic_mock(factory, ids, status='submitted')
    synthetic_mock(factory, ids)
    routes = [('/practice/submit', 'post', dict(question_id=q['id'], delivery_token=q['delivery_token'], selected_option=1, time_seconds=1)),
              (f'/practice/deliveries/{q["delivery_token"]}/assist?action=hint','post',None),
              ('/revision/bookmarks','get',None), ('/revision/flashcards/due','get',None),
              (f'/mocks/{old}/review','get',None), ('/backup/export','get',None),
              (f'/learn/lessons/{ids["lesson"]}','get',None),
              ('/exams/focus/current','put', {'exam_slug':'ssc-cgl-tier-1'})]
    for path, method, payload in routes:
        response = client.request(method, '/api/v1'+path, headers=headers, json=payload)
        assert response.status_code == 409, (path, response.text)
        assert 'SYNTHETIC_PRIVATE' not in response.text
    assert client.get('/api/v1/content/tree', headers=headers).status_code == 200
    with factory() as db:
        assert not list(db.scalars(select(QuestionAttempt)))


def test_int_04_server_section_and_stale_save(secured):
    client, factory, ids, headers = secured
    attempt = synthetic_mock(factory, ids)
    response = client.get(f'/api/v1/mocks/{attempt}', headers=headers)
    assert [q['question']['id'] for q in response.json()['questions']] == ids['questions'][:1]
    assert client.patch(f'/api/v1/mocks/{attempt}/response', headers=headers, json={'question_id':ids['questions'][1], 'selected_option':1}).status_code == 409
    from datetime import timedelta
    with factory() as db:
        db.get(MockAttempt, attempt).started_at = datetime.utcnow()-timedelta(seconds=901)
        db.commit()
    response = client.get(f'/api/v1/mocks/{attempt}', headers=headers)
    assert [q['question']['id'] for q in response.json()['questions']] == ids['questions'][1:2]
    assert client.patch(f'/api/v1/mocks/{attempt}/response', headers=headers, json={'question_id':ids['questions'][0], 'selected_option':1}).status_code == 409


def test_int_05_expired_still_locked_until_committed_and_retry(secured):
    client, factory, ids, headers = secured
    attempt = synthetic_mock(factory, ids, elapsed=3601)
    assert client.get(f'/api/v1/learn/topics/{ids["topic"]}/package', headers=headers).status_code == 409
    response = client.post(f'/api/v1/mocks/{attempt}/submit', headers=headers)
    assert response.status_code == 200, response.text
    assert client.post(f'/api/v1/mocks/{attempt}/submit', headers=headers).json() == response.json()
    assert client.get(f'/api/v1/learn/topics/{ids["topic"]}/package', headers=headers).status_code == 200


def test_int_06_abandon_is_terminal(secured):
    client, factory, ids, headers = secured
    attempt = synthetic_mock(factory, ids, mode='mini')
    assert client.delete(f'/api/v1/mocks/{attempt}', headers=headers).status_code == 200
    for suffix, method, body in [('', 'get', None), ('/submit', 'post', None), ('/response','patch',{'question_id':ids['questions'][0], 'selected_option':1})]:
        assert client.request(method, f'/api/v1/mocks/{attempt}'+suffix, headers=headers, json=body).status_code == 409


def test_int_08_unknown_foreign_changed_delivery_rejected(secured):
    client, factory, ids, headers = secured
    q = client.get('/api/v1/practice/questions?mode=mixed&limit=1', headers=headers).json()[0]
    payload = dict(question_id=q['id'], delivery_token='00000000-0000-0000-0000-000000000000', selected_option=1,time_seconds=2)
    assert client.post('/api/v1/practice/submit',headers=headers,json=payload).status_code == 404
    with factory() as db:
        db.get(Question, q['id']).explanation = 'Changed reviewed synthetic explanation'
        db.commit()
    payload['delivery_token'] = q['delivery_token']
    assert client.post('/api/v1/practice/submit',headers=headers,json=payload).status_code == 409
    with factory() as db:
        assert not list(db.scalars(select(QuestionAttempt)))


def test_sec_05_assets_are_referenced_scoped_and_reviewed(secured, tmp_path, monkeypatch):
    from app.routers.assets import settings
    import hashlib
    client, factory, ids, headers = secured
    monkeypatch.setattr(settings, 'private_asset_dir', str(tmp_path))
    data = b'synthetic-image-bytes'
    (tmp_path/'safe.png').write_bytes(data)
    (tmp_path/'unreferenced.png').write_bytes(data)
    with factory() as db:
        db.get(Question, ids['questions'][0]).question_image_url = 'private://safe.png'
        db.add(AssessmentAsset(asset_key='safe.png', content_sha256=hashlib.sha256(data).hexdigest(), review_reference='original fixture crop'))
        db.commit()
    assert client.get('/api/v1/assets/safe.png',headers=headers).content == data
    assert client.get('/api/v1/assets/unreferenced.png',headers=headers).status_code == 404
    assert client.get('/api/v1/assets/%2E%2E%2Foutside.png',headers=headers).status_code in {400,404}
    synthetic_mock(factory, ids)
    assert client.get('/api/v1/assets/safe.png',headers=headers).status_code == 200
    assert client.get('/api/v1/assets/unreferenced.png',headers=headers).status_code == 409
    (tmp_path/'safe.png').write_bytes(b'changed-file')
    assert client.get('/api/v1/assets/safe.png',headers=headers).status_code == 409


def test_sec_03_04_all_sources_required_and_revocation(secured):
    client, factory, ids, headers = secured
    with factory() as db:
        db.add(ContentSource(id='second-private',exam_id=ids['exam'],private_use_approved=True,approval_reference='fixture'))
        db.flush()
        db.add(ContentBinding(resource_kind='question',resource_id=ids['questions'][0],source_id='second-private'))
        db.commit()
    response = client.get(f'/api/v1/learn/topics/{ids["topic"]}/package',headers=headers)
    assert [q['id'] for q in response.json()['solved_examples']] == ids['questions'][1:2]
    with factory() as db:
        db.get(SourceGrant, (ids['user'],'synthetic-original')).active=False
        db.commit()
    assert client.get(f'/api/v1/learn/topics/{ids["topic"]}/package',headers=headers).status_code == 404


def test_sec_07_public_metadata_has_no_private_inventory(secured):
    client, _, _, _ = secured
    response = client.get('/api/v1/content/tree')
    assert response.json()['totals']['lessons'] == 0
    assert 'SYNTHETIC_PRIVATE' not in response.text
    assert 'source_notes' not in response.text


def test_int_07_solved_example_exposure_survives_later_delivery(secured):
    client, factory, ids, headers = secured
    assert client.get(f'/api/v1/learn/topics/{ids["topic"]}/package',headers=headers).status_code == 200
    q = client.get('/api/v1/practice/questions?mode=mixed&limit=1',headers=headers).json()[0]
    assert client.post('/api/v1/practice/submit',headers=headers,json=dict(question_id=q['id'],delivery_token=q['delivery_token'],selected_option=1,time_seconds=1,used_hint=False)).status_code == 200
    with factory() as db:
        assert db.scalar(select(QuestionAttempt)).used_hint
        assert db.scalar(select(ContentExposure)) is not None


def test_migration_manifest_dry_run_apply_and_history_preservation(secured):
    from app.services.entitlement_admin import apply_manifest
    from app.phase_a_migration import TABLES, migrate, verify_rollout
    from app.models import Bookmark, RevisionItem, TopicMastery
    client, factory, ids, headers = secured
    engine = factory.kw['bind']
    attempt = synthetic_mock(factory, ids, status='submitted')
    with factory() as db:
        old = db.get(MockAttempt, attempt)
        old.score = 3.5
        db.add(QuestionAttempt(user_id=ids['user'],question_id=ids['questions'][0],selected_option=1,is_correct=True,time_seconds=12,confidence=3,used_hint=False))
        db.add(TopicMastery(user_id=ids['user'],topic_id=ids['topic'],mastery_score=42,attempts=7,correct=5))
        db.add(Bookmark(user_id=ids['user'],question_id=ids['questions'][0]))
        db.add(RevisionItem(user_id=ids['user'],question_id=ids['questions'][0],reason='synthetic',next_review_at=datetime.utcnow()))
        saved = db.scalar(select(MockAttemptQuestion).where(MockAttemptQuestion.attempt_id == attempt).limit(1))
        saved.selected_option = 2
        saved.time_seconds = 17
        db.commit()
        before = (old.id, old.score, old.status, old.started_at)
        legacy_tables = [table for table in Base.metadata.sorted_tables if table not in TABLES]
        def snapshot():
            return {table.name:list(db.execute(select(table).order_by(*table.primary_key.columns))) for table in legacy_tables}
        legacy_before = snapshot()
        manifest = {'operator':'synthetic-reviewer','reason':'reviewed fixture only',
                    'courses':[{'user_id':ids['outsider'],'exam_id':ids['exam'],'active':True}],
                    'grants':[{'user_id':ids['outsider'],'source_id':'synthetic-original','active':True}]}
        report = apply_manifest(db, manifest)
        assert report['applied'] is False
        assert db.get(CourseGrant, (ids['outsider'], ids['exam'])) is None
        with pytest.raises(ValueError):
            apply_manifest(db, manifest, approved_digest='wrong')
        applied = apply_manifest(db, manifest, approved_digest=report['manifest_digest'])
        assert applied['applied'] is True
        db.commit()
        old = db.get(MockAttempt, attempt)
        assert (old.id, old.score, old.status, old.started_at) == before
        assert snapshot() == legacy_before
    migrate(engine)
    migrate(engine)  # Restart-safe additive DDL.
    verify_rollout(engine, report['manifest_digest'])
    with pytest.raises(RuntimeError):
        verify_rollout(engine, 'unreviewed')
    outsider = {'Authorization':'Bearer '+create_access_token(str(ids['outsider']))}
    assert client.get(f'/api/v1/learn/topics/{ids["topic"]}/package',headers=outsider).status_code == 200


def test_postgres_int_05_08_concurrent_identical_practice_submission(secured):
    from concurrent.futures import ThreadPoolExecutor
    client, factory, _, headers = secured
    if factory.kw['bind'].dialect.name != 'postgresql':
        pytest.skip('PostgreSQL row-lock integration test')
    q = client.get('/api/v1/practice/questions?mode=mixed&limit=1',headers=headers).json()[0]
    payload = dict(question_id=q['id'],delivery_token=q['delivery_token'],selected_option=1,time_seconds=1)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.post('/api/v1/practice/submit',headers=headers,json=payload), range(4)))
    assert all(r.status_code == 200 for r in responses)
    assert all(r.json() == responses[0].json() for r in responses)
    with factory() as db:
        assert len(list(db.scalars(select(QuestionAttempt)))) == 1


def test_postgres_int_05_concurrent_finalize_returns_one_result(secured):
    from concurrent.futures import ThreadPoolExecutor
    client, factory, ids, headers = secured
    if factory.kw['bind'].dialect.name != 'postgresql':
        pytest.skip('PostgreSQL row-lock integration test')
    attempt = synthetic_mock(factory, ids, elapsed=3601)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _: client.post(f'/api/v1/mocks/{attempt}/submit',headers=headers), range(4)))
    assert all(r.status_code == 200 for r in responses)
    assert all(r.json() == responses[0].json() for r in responses)
    with factory() as db:
        assert db.get(MockAttempt, attempt).status == 'submitted'


def test_postgres_int_05_locked_finalization_withholds_answers(secured):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    client, factory, ids, headers = secured
    if factory.kw['bind'].dialect.name != 'postgresql':
        pytest.skip('PostgreSQL row-lock integration test')
    attempt = synthetic_mock(factory, ids, elapsed=3601)
    entered = Event()
    with factory() as db:
        db.execute(select(User.id).where(User.id == ids['user']).with_for_update()).one()
        db.get(MockAttempt, attempt).status = 'submitted'
        db.flush()  # Not committed: the teaching request must wait.
        def request():
            entered.set()
            return client.get(f'/api/v1/learn/topics/{ids["topic"]}/package',headers=headers)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(request)
            assert entered.wait(2)
            from concurrent.futures import TimeoutError
            with pytest.raises(TimeoutError):
                pending.result(timeout=.2)
            db.rollback()  # Failed finalization must not unlock teaching.
            assert pending.result(timeout=5).status_code == 409


def test_postgres_db_01_backend_only_tables(secured):
    from app.phase_a_migration import TABLES, migrate
    _, factory, _, _ = secured
    engine = factory.kw['bind']
    if engine.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL privileges integration test')
    migrate(engine)
    with engine.connect() as connection:
        for table in TABLES:
            assert connection.scalar(text('SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:name)'), {'name':table.name})
            for role in ('anon','authenticated'):
                if connection.scalar(text('SELECT 1 FROM pg_roles WHERE rolname=:role'), {'role':role}):
                    for privilege in ('SELECT','INSERT','UPDATE','DELETE'):
                        assert not connection.scalar(text('SELECT has_table_privilege(:role,:name,:privilege)'), {'role':role,'name':table.name,'privilege':privilege})


def test_sec_03_04_publication_approval_is_distinct_from_authorization(secured):
    client, factory, ids, headers = secured
    with factory() as db:
        db.get(SourceGrant,(ids['user'],'synthetic-original')).active=False
        q = db.get(Question, ids['questions'][0])
        q.visibility='public'
        q.source_type='official'  # Neither flag is a publication approval.
        db.commit()
    assert client.get(f'/api/v1/learn/topics/{ids["topic"]}/package',headers=headers).status_code == 404
    with factory() as db:
        db.get(ContentSource,'synthetic-original').public_use_approved=True
        db.commit()
    response = client.get(f'/api/v1/learn/topics/{ids["topic"]}/package',headers=headers)
    assert response.status_code == 200
    assert [q['id'] for q in response.json()['solved_examples']] == ids['questions'][:1]
    assert response.json()['lessons'] == []  # A public question doesn't publish a private lesson.


def test_sec_02_05_cross_course_cannot_be_granted_through_wrong_binding(secured):
    client, factory, ids, headers = secured
    with factory() as db:
        exam = Exam(slug='synthetic-other', name='Other course',duration_minutes=60)
        db.add(exam); db.flush()
        db.add(ContentSource(id='other-course',exam_id=exam.id,private_use_approved=True,approval_reference='synthetic'))
        db.flush()
        db.add(SourceGrant(user_id=ids['user'],source_id='other-course',active=True))
        db.add(ContentBinding(resource_kind='question',resource_id=ids['questions'][0],source_id='other-course'))
        db.commit()
    response = client.get(f'/api/v1/learn/topics/{ids["topic"]}/package',headers=headers)
    assert [q['id'] for q in response.json()['solved_examples']] == ids['questions'][1:2]


def test_live_01_summary_never_exports_private_values():
    from app.phase_a_live_check import summarize
    result = summarize(200, {'cache-control':'private, no-store','x-ssc-release':'synthetic-sha'},
                       {'solved_examples':[{'id':42,'explanation':'PRIVATE_SENTINEL','source_reference':'private-path'}]}, {42}, 'synthetic-sha')
    import json
    serialized = json.dumps(result)
    assert result['private_id_match'] is True
    assert result['release_sha_matches'] is True
    assert 'PRIVATE_SENTINEL' not in serialized and 'private-path' not in serialized and '42' not in serialized


def test_sec_01_rejects_signed_token_without_expiry(secured):
    from jose import jwt
    from app.core.config import get_settings
    client, _, ids, _ = secured
    settings = get_settings()
    token = jwt.encode({'sub':str(ids['user']), 'role':'admin'},settings.jwt_secret,algorithm=settings.jwt_algorithm)
    assert client.get(f'/api/v1/learn/topics/{ids["topic"]}/package',headers={'Authorization':'Bearer '+token}).status_code == 401


def test_postgres_int_05_06_concurrent_starts_and_exposure_after_abandon(secured):
    from concurrent.futures import ThreadPoolExecutor
    client, factory, ids, headers = secured
    if factory.kw['bind'].dialect.name != 'postgresql':
        pytest.skip('PostgreSQL row-lock integration test')
    with factory() as db:
        subject_id = db.get(Topic, ids['topic']).subject_id
        for i in range(8):
            q = Question(exam_id=ids['exam'],subject_id=subject_id,topic_id=ids['topic'],question_text=f'Original race fixture {i}+10?',correct_option=1,explanation=f'{i}+10={i+10}',difficulty=1,verification_status='verified',visibility='private')
            db.add(q); db.flush()
            db.add_all([QuestionOption(question_id=q.id,position=j,text=str(i+9+j)) for j in range(1,5)])
            db.add(ContentBinding(resource_kind='question',resource_id=q.id,source_id='synthetic-original'))
        db.commit()
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: client.post('/api/v1/mocks/start',headers=headers,json={'mode':'topic','topic_id':ids['topic']}),range(2)))
    assert all(r.status_code == 200 for r in responses), [r.text for r in responses]
    attempt = responses[0].json()['attempt_id']
    assert responses[1].json()['attempt_id'] == attempt
    assert client.delete(f'/api/v1/mocks/{attempt}',headers=headers).status_code == 200
    with factory() as db:
        assert len(list(db.scalars(select(MockAttempt)))) == 1
        assert len(list(db.scalars(select(ContentExposure)))) == 10
    q = client.get('/api/v1/practice/questions?mode=mixed&limit=1',headers=headers).json()[0]
    response = client.post('/api/v1/practice/submit',headers=headers,json=dict(question_id=q['id'],delivery_token=q['delivery_token'],selected_option=1,time_seconds=1,used_hint=False))
    assert response.status_code == 200
    with factory() as db:
        assert db.scalar(select(QuestionAttempt)).used_hint
