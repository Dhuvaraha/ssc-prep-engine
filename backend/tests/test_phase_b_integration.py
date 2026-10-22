"""Synthetic application capture + additive database immutability checks."""
import os
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db import Base
from app.models import Exam, Question, QuestionOption, Subject, Topic, User
from app.access_models import ContentBinding, ContentSource, PracticeDelivery
from app.revision_models import QuestionRevision, DeliveryRevision
from app.phase_b_migration import migrate, verify, TABLES
from app.services.practice_integrity import issue_delivery
from app.services.revision_capture import read_evidence


@pytest.fixture
def setup(tmp_path,monkeypatch):
    url=os.environ.get('PHASE_A_TEST_DATABASE_URL')
    admin=None; schema=None
    if url:
        parsed=make_url(url)
        if parsed.host not in {'localhost','127.0.0.1'} or parsed.database!='ssc_phase_a_test' or parsed.query or parsed.drivername!='postgresql+psycopg':
            raise RuntimeError('Only isolated loopback PostgreSQL permitted')
        args={'hostaddr':'127.0.0.1','dbname':'ssc_phase_a_test'}
        admin=create_engine(url,connect_args=args)
        schema='phase_b_'+uuid4().hex
        with admin.begin() as c:c.execute(text(f'CREATE SCHEMA {schema}'))
        engine=create_engine(url,connect_args={**args,'options':f'-csearch_path={schema}'})
    else:
        engine=create_engine('sqlite:///'+str(tmp_path/'phase_b.sqlite'))
    Base.metadata.create_all(engine)
    migrate(engine);migrate(engine);verify(engine)
    monkeypatch.setattr(get_settings(),'phase_b_capture_enabled',True)
    with Session(engine) as db:
        db.add(Exam(id=1,slug='ssc-cgl-tier-1',name='Fixture',duration_minutes=60))
        db.flush()
        db.add_all([User(id=1,email='synthetic@example.invalid',password_hash='no-login'),Subject(id=1,exam_id=1,slug='quant',name='Quant')]);db.flush()
        db.add(Topic(id=1,subject_id=1,slug='fixture',name='Fixture'));db.flush()
        db.add(Question(id=1,exam_id=1,subject_id=1,topic_id=1,question_text='Original fixture 2+2?',correct_option=2,explanation='Four',verification_status='verified'));db.flush()
        db.add_all([QuestionOption(id=i,question_id=1,position=i,text=str(i+2)) for i in range(1,5)])
        db.add(ContentSource(id='original-fixture',exam_id=1,approval_reference='synthetic-only',private_use_approved=True));db.flush()
        db.add(ContentBinding(resource_kind='question',resource_id=1,source_id='original-fixture'));db.commit()
    yield engine
    engine.dispose()
    if admin:
        with admin.begin() as c:c.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()


def question(db):
    return db.scalar(select(Question).options(selectinload(Question.options)).where(Question.id==1))


def test_practice_delivery_captures_and_preserves_version(setup):
    with Session(setup) as db:
        q=question(db)
        delivery=issue_delivery(db,1,q);token=delivery.id;db.commit()
        before=read_evidence(db,'practice',token,1)
        assert before['revision']['question']['correct_option']==2
        assert before['blueprint']['expiry_seconds']==14400
        q.explanation='Later edit';q.correct_option=3;db.commit()
        assert read_evidence(db,'practice',token,1)==before
        other=issue_delivery(db,1,q);db.commit()
        assert read_evidence(db,'practice',other.id,1)['answer_version']!=before['answer_version']


def test_capture_rollback_refuses_existing_history_without_mutation(setup):
    from app.phase_b_migration import verify_capture_rollback
    verify_capture_rollback(setup, capture_enabled=False)
    with Session(setup) as db:
        delivery=issue_delivery(db,1,question(db));db.commit()
        token=delivery.id
        before=read_evidence(db,'practice',token,1)
    with pytest.raises(RuntimeError,match='revision-compatible release'):
        verify_capture_rollback(setup, capture_enabled=False)
    verify_capture_rollback(setup, capture_enabled=True)
    with Session(setup) as db:
        assert read_evidence(db,'practice',token,1)==before


def test_capture_disabled_supports_database_without_phase_b_tables(tmp_path):
    from app.phase_b_migration import verify_capture_rollback
    engine=create_engine('sqlite:///'+str(tmp_path/'legacy.sqlite'))
    try:
        verify_capture_rollback(engine, capture_enabled=False)
    finally:
        engine.dispose()


def test_capture_rollback_rejects_rls_hidden_history(setup):
    from sqlalchemy import event
    from app.phase_b_migration import verify_capture_rollback
    if setup.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL RLS role regression')
    with Session(setup) as db:
        issue_delivery(db,1,question(db));db.commit()
    with setup.begin() as connection:
        if not connection.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='anon')")):
            pytest.skip('Requires isolated CI anon role')
        schema=connection.scalar(text('SELECT current_schema()'))
        quoted=setup.dialect.identifier_preparer.quote(schema)
        connection.execute(text(f'GRANT USAGE ON SCHEMA {quoted} TO anon'))
        connection.execute(text(f'GRANT SELECT ON {DeliveryRevision.__tablename__} TO anon'))
    def restricted(connection):
        connection.execute(text('SET LOCAL ROLE anon'))
    event.listen(setup,'begin',restricted)
    try:
        with setup.connect() as connection:
            assert not connection.execute(select(DeliveryRevision.__table__)).first()
        with pytest.raises(RuntimeError,match='proven history visibility'):
            verify_capture_rollback(setup,capture_enabled=False)
    finally:
        event.remove(setup,'begin',restricted)


def test_capture_deduplicates_without_mutation(setup):
    with Session(setup) as db:
        q=question(db)
        issue_delivery(db,1,q);issue_delivery(db,1,q);db.commit()
        assert len(db.scalars(select(QuestionRevision)).all())==1
        assert len(db.scalars(select(DeliveryRevision)).all())==2


def test_delivery_and_revision_rollback_together(setup):
    with Session(setup) as db:
        issue_delivery(db,1,question(db));db.rollback()
        assert not db.scalars(select(QuestionRevision)).all()
        assert not db.scalars(select(PracticeDelivery)).all()
        assert read_evidence(db,'mock',999,1)['original_version_unknown']


@pytest.mark.parametrize('operation',['UPDATE','DELETE','UPSERT'])
def test_database_rejects_history_mutations(setup,operation):
    with Session(setup) as db:
        issue_delivery(db,1,question(db));db.commit()
        rid=db.scalar(select(QuestionRevision.id))
    sql={'UPDATE':"UPDATE question_revisions SET payload='changed'",'DELETE':'DELETE FROM question_revisions',
         'UPSERT':"INSERT INTO question_revisions SELECT * FROM question_revisions WHERE id=:rid ON CONFLICT(id) DO UPDATE SET payload='changed'"}[operation]
    with pytest.raises(DBAPIError):
        with setup.begin() as c:c.execute(text(sql),{'rid':rid})


def test_unknown_external_image_blocks_new_pin(setup):
    with Session(setup) as db:
        q=question(db);q.question_image_url='https://example.invalid/unversioned.svg'
        with pytest.raises(ValueError,match='versioned asset'):issue_delivery(db,1,q)
        db.rollback()
        assert not db.scalars(select(PracticeDelivery)).all()


def test_postgres_truncate_and_client_grants(setup):
    if setup.dialect.name!='postgresql':pytest.skip('PostgreSQL-specific')
    with pytest.raises(DBAPIError):
        with setup.begin() as c:c.execute(text('TRUNCATE question_revisions CASCADE'))
    with setup.connect() as c:
        for table in TABLES:
            assert c.scalar(text('SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(:name)'),{'name':table.name})
            for role in c.scalars(text("SELECT rolname FROM pg_roles WHERE rolname IN ('anon','authenticated')")).all():
                assert not c.scalar(text("SELECT has_table_privilege(:role,:name,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE')"),{'role':role,'name':table.name})


def test_authenticated_editorial_flow_preserves_live_question(setup,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_db
    from app.core.security import create_access_token
    from app.revision_models import EditorialDecision
    with Session(setup) as db:
        db.add_all([User(id=2,email='reviewer@example.invalid',password_hash='no-login'),User(id=3,email='outsider@example.invalid',password_hash='no-login')]);db.commit()
    monkeypatch.setattr(get_settings(),'reviewer_emails','synthetic@example.invalid,reviewer@example.invalid')
    def scoped_db():
        with Session(setup) as db:yield db
    app.dependency_overrides[get_db]=scoped_db
    headers=lambda uid:{'Authorization':'Bearer '+create_access_token(str(uid))}
    try:
        client=TestClient(app)
        assert client.get('/api/v1/review/questions').status_code==401
        assert client.get('/api/v1/review/questions',headers=headers(3)).status_code==403
        listed=client.get('/api/v1/review/questions?status=verified',headers=headers(1)).json()
        payload={'expected_digest':listed[0]['revision_digest'],'reason':'Review explanation context',
                 'changes':{'verification_status':'review_required','review_notes':'Needs deeper explanation','explanation':'Combine two pairs to obtain four.'}}
        stale={**payload,'expected_digest':'0'*64}
        assert client.post('/api/v1/review/questions/1/revisions',json=stale,headers=headers(1)).status_code==409
        response=client.post('/api/v1/review/questions/1/revisions',json=payload,headers=headers(1))
        assert response.status_code==200,response.text
        cid=response.json()['candidate_id']
        path='/api/v1/review/revisions/'+cid
        assert client.get(path,headers=headers(3)).status_code==403
        view=client.get(path,headers=headers(2)).json()
        assert view['after']['question']['correct_option']==2
        assert view['after']['question']['topic_id']==1
        assert view['after']['question']['explanation']=='Combine two pairs to obtain four.'
        assert not view['published']
        evidence=dict(answer_verified=True,all_options_checked=True,instruction_reviewed=True,visual_reviewed=True,reference='Independent synthetic review')
        assert client.post(path+'/review',json=evidence,headers=headers(1)).status_code==409
        assert client.post(path+'/review',json={**evidence,'answer_verified':'true'},headers=headers(2)).status_code==422
        assert client.post(path+'/review',json=evidence,headers=headers(2)).status_code==200
        assert client.post(path+'/review',json=evidence,headers=headers(2)).status_code==409
        assert client.patch('/api/v1/review/questions/1',json={'verification_status':'rejected'},headers=headers(1)).status_code==409
        with Session(setup) as db:
            q=question(db)
            assert q.verification_status=='verified' and q.correct_option==2 and q.review_notes is None
            assert q.explanation=='Four'
            assert db.get(EditorialDecision,cid).reviewer_id==2
    finally:
        app.dependency_overrides.pop(get_db,None)


def test_mock_creation_pins_blueprint_in_actual_service(setup):
    from app.services.mock_engine import create_mock_attempt
    with Session(setup) as db:
        # Add enough distinct original questions for the real topic selector.
        for qid in range(2,13):
            db.add(Question(id=qid,exam_id=1,subject_id=1,topic_id=1,question_text=f'Original fixture {qid}+1?',correct_option=1,explanation='Synthetic',verification_status='verified'))
            db.flush()
            db.add_all([QuestionOption(id=(qid-1)*4+i,question_id=qid,position=i,text=str(qid+i)) for i in range(1,5)])
            db.add(ContentBinding(resource_kind='question',resource_id=qid,source_id='original-fixture'))
        db.commit()
        exam=db.get(Exam,1)
        attempt,rows=create_mock_attempt(db,user_id=1,mode='topic',subject_slug=None,topic_id=1)
        saved=read_evidence(db,'mock',attempt.id,rows[0][1].id)
        assert saved['blueprint']['duration_minutes']==20
        assert saved['blueprint']['positive_marks']==exam.positive_marks
        assert len(db.scalars(select(DeliveryRevision).where(DeliveryRevision.kind=='mock')).all())==len(rows)


def test_phase_b_disables_in_place_repair(setup):
    from app.services.content_repair import repair_content_integrity
    with Session(setup) as db:
        with pytest.raises(ValueError,match='revision candidates'):repair_content_integrity(db,apply=True)


def test_asset_manifest_cannot_change_bytes_under_existing_locator(setup):
    from app.access_models import AssessmentAsset
    with Session(setup) as db:
        db.add(AssessmentAsset(asset_key='figure-v1.svg',content_sha256='a'*64,review_reference='synthetic-review'));db.commit()
    for sql in ["UPDATE assessment_assets SET content_sha256='changed' WHERE asset_key='figure-v1.svg'",
                "DELETE FROM assessment_assets WHERE asset_key='figure-v1.svg'",
                "INSERT INTO assessment_assets SELECT * FROM assessment_assets WHERE asset_key='figure-v1.svg' ON CONFLICT(asset_key) DO UPDATE SET content_sha256='changed'"]:
        with pytest.raises(DBAPIError):
            with setup.begin() as c:c.execute(text(sql))
    with Session(setup) as db:
        db.add(AssessmentAsset(asset_key='figure-v2.svg',content_sha256='b'*64,review_reference='new-review'));db.commit()
        assert db.get(AssessmentAsset,'figure-v1.svg').content_sha256=='a'*64


def test_startup_verifier_rejects_missing_guard(setup):
    with setup.begin() as c:
        if setup.dialect.name=='postgresql':
            c.execute(text('DROP TRIGGER phase_b_immutable ON question_revisions'))
        else:
            c.execute(text('DROP TRIGGER question_revisions_UPDATE'))
    with pytest.raises(RuntimeError,match='trigger'):verify(setup)


def test_legacy_review_patch_preserves_omitted_fields(setup,monkeypatch):
    from app.routers.review import ReviewUpdate,update_review_question
    monkeypatch.setattr(get_settings(),'phase_b_capture_enabled',False)
    with Session(setup) as db:
        update_review_question(1,ReviewUpdate(verification_status='verified',review_notes='Synthetic note'),db,db.get(User,1))
        q=question(db)
        assert q.topic_id==1 and q.correct_option==2
        assert q.review_notes=='Synthetic note'


def seeded_pinned_mock(db, *, mode='topic'):
    from app.models import MockAttempt, MockAttemptQuestion
    from app.access_models import CourseGrant, SourceGrant, AssessmentDelivery
    from app.services.revision_capture import pin_delivery
    from app.services.practice_integrity import question_digest
    db.add_all([CourseGrant(user_id=1,exam_id=1,active=True),
                SourceGrant(user_id=1,source_id='original-fixture',active=True)])
    duration=60 if mode=='full' else 20
    attempt=MockAttempt(user_id=1,exam_id=1,mode=mode,duration_minutes=duration)
    db.add(attempt);db.flush()
    q=question(db)
    db.add(MockAttemptQuestion(attempt_id=attempt.id,question_id=1,section_slug='quant',position=1,selected_option=2))
    db.add(AssessmentDelivery(attempt_id=attempt.id,question_id=1,content_digest=question_digest(q),correct_option=2))
    pin_delivery(db,kind='mock',delivery_id=attempt.id,user_id=1,question=q,
                 blueprint={'positive_marks':2,'negative_marks':0.5,'mode':mode,'duration_minutes':duration,
                            'section_order':['reasoning','general-awareness','quant','english'],'full_section_seconds':900,
                            'curriculum_topic_count':1})
    db.commit()
    return attempt.id


def test_mock_resume_grade_and_review_use_original_revision(setup):
    from app.services.mock_engine import load_mock_attempt,submit_mock_attempt
    from app.routers.mocks import review_mock, _serialize_attempt
    from app.models import QuestionOption
    with Session(setup) as db:
        aid=seeded_pinned_mock(db)
        q=question(db);q.correct_option=3;q.explanation='Later correction';q.question_text='Changed stem'
        db.get(QuestionOption,1).text='Changed option'
        db.get(Exam,1).positive_marks=10;db.commit()
        attempt,rows=load_mock_attempt(db,attempt_id=aid,user_id=1)
        response=_serialize_attempt(attempt,rows).model_dump()
        assert response['questions'][0]['question']['question_text']=='Original fixture 2+2?'
        assert 'correct_option' not in response['questions'][0]['question']
        assert rows[0][1].options[0].text=='3'
        result=submit_mock_attempt(db,attempt=attempt,rows=rows)
        assert result['score']==2 and result['correct']==1
        reviewed=review_mock(aid,db,db.get(User,1))
        assert reviewed['questions'][0]['explanation']=='Four'
        assert reviewed['questions'][0]['correct_option']==2
        assert not reviewed['questions'][0]['original_version_unknown']
        assert reviewed['sections']['quant']['score']==2
        assert db.get(Question,1).explanation=='Later correction'


def test_pinned_dependencies_remain_required_after_rebinding(setup):
    from fastapi import HTTPException
    from app.access_models import SourceGrant
    from app.services.mock_engine import load_mock_attempt
    with Session(setup) as db:
        aid=seeded_pinned_mock(db)
        db.delete(db.get(ContentBinding,('question',1,'original-fixture')))
        db.add(ContentSource(id='replacement',exam_id=1,public_use_approved=True,approval_reference='synthetic-only'))
        db.flush();db.add(ContentBinding(resource_kind='question',resource_id=1,source_id='replacement'))
        question(db).visibility='public'
        db.get(SourceGrant,(1,'original-fixture')).active=False;db.commit()
        with pytest.raises(HTTPException) as error:load_mock_attempt(db,attempt_id=aid,user_id=1)
        assert error.value.status_code==404


def test_pinned_delivery_rejects_wrong_owner_and_revoked_course(setup):
    from fastapi import HTTPException
    from app.access_models import CourseGrant
    from app.services.revision_capture import delivered_question
    with Session(setup) as db:
        aid=seeded_pinned_mock(db)
        with pytest.raises(HTTPException):
            delivered_question(db,kind='mock',delivery_id=aid,user_id=2,current=question(db))
        db.get(CourseGrant,(1,1)).active=False;db.commit()
        with pytest.raises(HTTPException):
            delivered_question(db,kind='mock',delivery_id=aid,user_id=1,current=question(db))


def test_active_pinned_asset_survives_locator_edit_but_not_source_revocation(setup,tmp_path,monkeypatch):
    import hashlib
    from fastapi import HTTPException
    from app.access_models import AssessmentAsset, SourceGrant
    from app.routers.assets import get_private_asset
    data=b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="3"/></svg>'
    (tmp_path/'old.svg').write_bytes(data)
    monkeypatch.setattr(get_settings(),'private_asset_dir',str(tmp_path))
    with Session(setup) as db:
        question(db).question_image_url='private://old.svg'
        db.add(AssessmentAsset(asset_key='old.svg',content_sha256=hashlib.sha256(data).hexdigest(),review_reference='synthetic-only'))
        db.commit();seeded_pinned_mock(db)
        question(db).question_image_url='private://new.svg';db.commit()
        assert get_private_asset('old.svg',db.get(User,1),db).body==data
        (tmp_path/'old.svg').write_bytes(b'changed bytes')
        with pytest.raises(HTTPException) as error:get_private_asset('old.svg',db.get(User,1),db)
        assert error.value.status_code==409
        (tmp_path/'old.svg').write_bytes(data)
        # Current access remains valid after rebinding, but old-source access ends.
        db.delete(db.get(ContentBinding,('question',1,'original-fixture')))
        db.add(ContentSource(id='new-source',exam_id=1,public_use_approved=True,approval_reference='synthetic-only'))
        db.flush();db.add(ContentBinding(resource_kind='question',resource_id=1,source_id='new-source'))
        question(db).visibility='public'
        db.get(SourceGrant,(1,'original-fixture')).active=False;db.commit()
        with pytest.raises(HTTPException) as error:get_private_asset('old.svg',db.get(User,1),db)
        assert error.value.status_code==404


def test_practice_scores_pinned_key_and_retries_without_regrading(setup):
    from app.access_models import CourseGrant, SourceGrant
    from app.routers.practice import submit_practice
    from app.schemas import PracticeSubmit
    from app.models import QuestionAttempt
    from fastapi import HTTPException
    with Session(setup) as db:
        db.add_all([CourseGrant(user_id=1,exam_id=1,active=True),SourceGrant(user_id=1,source_id='original-fixture',active=True)])
        q=question(db);delivery=issue_delivery(db,1,q);token=delivery.id;db.commit()
        q.correct_option=3;q.explanation='Changed explanation';db.commit()
        payload=dict(delivery_token=token,question_id=1,selected_option=2,time_seconds=20)
        result=submit_practice(PracticeSubmit(**payload),db,db.get(User,1))
        assert result.correct and result.correct_option==2 and result.explanation=='Four'
        assert result.coaching is None and result.option_insights==[]
        assert submit_practice(PracticeSubmit(**payload),db,db.get(User,1))==result
        assert len(db.scalars(select(QuestionAttempt)).all())==1
        db.get(SourceGrant,(1,'original-fixture')).active=False;db.commit()
        with pytest.raises(HTTPException) as error:submit_practice(PracticeSubmit(**payload),db,db.get(User,1))
        assert error.value.status_code==404


def test_practice_assistance_uses_original_explanation_and_expiry(setup):
    from datetime import datetime, timedelta
    from app.access_models import CourseGrant, SourceGrant
    from app.routers.practice import assist_delivery
    from fastapi import HTTPException
    with Session(setup) as db:
        db.add_all([CourseGrant(user_id=1,exam_id=1,active=True),SourceGrant(user_id=1,source_id='original-fixture',active=True)])
        q=question(db);delivery=issue_delivery(db,1,q);db.commit()
        q.explanation='New';db.commit()
        result=assist_delivery(delivery.id,'explain',db,db.get(User,1))
        assert result['explanation']=='Four' and result['coaching'] is None
        assert delivery.assisted
        delivery.created_at=datetime.utcnow()-timedelta(hours=5);db.commit()
        with pytest.raises(HTTPException) as error:assist_delivery(delivery.id,'explain',db,db.get(User,1))
        assert error.value.detail=='DELIVERY_EXPIRED'


def test_pinned_retry_does_not_replay_unversioned_supplements(setup,monkeypatch):
    import json
    from app.access_models import CourseGrant, SourceGrant
    from app.routers import practice
    from app.schemas import PracticeSubmit
    with Session(setup) as db:
        db.add_all([CourseGrant(user_id=1,exam_id=1,active=True),SourceGrant(user_id=1,source_id='original-fixture',active=True)])
        delivery=issue_delivery(db,1,question(db));db.commit()
        payload=dict(delivery_token=delivery.id,question_id=1,selected_option=2,time_seconds=20)
        def forbidden(*args,**kwargs):
            raise AssertionError('Unversioned supplements must not enter pinned results')
        monkeypatch.setattr(practice,'build_question_coaching',forbidden)
        monkeypatch.setattr(practice,'published_option_insights',forbidden)
        result=practice.submit_practice(PracticeSubmit(**payload),db,db.get(User,1))
        assert result.coaching is None and not result.option_insights
        # Simulate a previously saved payload: its contributors were never pinned.
        stored=json.loads(delivery.result_json)
        stored['coaching']={'pattern_name':'REVOKED_SUPPLEMENT'}
        delivery.result_json=json.dumps(stored);db.commit()
        replay=practice.submit_practice(PracticeSubmit(**payload),db,db.get(User,1))
        assert replay.coaching is None and not replay.option_insights
        assert 'REVOKED_SUPPLEMENT' in delivery.result_json
        assert replay.attempt_id==result.attempt_id and replay.correct==result.correct


def reviewed_candidate(db, explanation='Reviewed correction'):
    from app.routers.review import create_revision,review_revision,_revision_digest,RevisionDraft,RevisionChanges,RevisionReview
    if db.get(User,2) is None:
        db.add(User(id=2,email='independent@example.invalid',password_hash='no-login'));db.commit()
    payload=RevisionDraft(expected_digest=_revision_digest(db,question(db)),reason='Synthetic correction',
                          changes=RevisionChanges(verification_status='verified',explanation=explanation,correct_option=3))
    cid=create_revision(1,payload,db,db.get(User,1))['candidate_id']
    review_revision(cid,RevisionReview(answer_verified=True,all_options_checked=True,instruction_reviewed=True,
                                     visual_reviewed=True,reference='Synthetic independent review'),db,db.get(User,2))
    return cid


def test_publication_is_atomic_and_preserves_existing_deliveries(setup,monkeypatch):
    from app.services.revision_publication import publish_candidate
    from app.revision_models import EditorialPublication
    from fastapi import HTTPException
    with Session(setup) as db:
        aid=seeded_pinned_mock(db)
        token=issue_delivery(db,1,question(db)).id;db.commit()
        cid=reviewed_candidate(db)
        with pytest.raises(HTTPException):publish_candidate(db,cid,2)
        monkeypatch.setattr(get_settings(),'phase_b_publication_enabled',True)
        result=publish_candidate(db,cid,2)
        assert result['published'] and question(db).correct_option==3
        db.rollback()
        assert question(db).correct_option==2 and db.get(EditorialPublication,cid) is None
        publish_candidate(db,cid,2);db.commit()
        assert question(db).correct_option==3
        assert read_evidence(db,'mock',aid,1)['revision']['question']['correct_option']==2
        assert read_evidence(db,'practice',token,1)['revision']['question']['explanation']=='Four'
        with pytest.raises(HTTPException) as error:publish_candidate(db,cid,2)
        assert error.value.detail=='Candidate already published'
    with pytest.raises(DBAPIError):
        with setup.begin() as c:c.execute(text('DELETE FROM editorial_publications'))


def test_publication_refuses_unpinned_active_delivery(setup,monkeypatch):
    from app.services.revision_publication import publish_candidate
    from fastapi import HTTPException
    with Session(setup) as db:
        monkeypatch.setattr(get_settings(),'phase_b_capture_enabled',False)
        issue_delivery(db,1,question(db));db.commit()
        monkeypatch.setattr(get_settings(),'phase_b_capture_enabled',True)
        monkeypatch.setattr(get_settings(),'phase_b_publication_enabled',True)
        cid=reviewed_candidate(db)
        with pytest.raises(HTTPException) as error:publish_candidate(db,cid,2)
        assert error.value.detail=='UNPINNED_ACTIVE_DELIVERY'
        assert question(db).correct_option==2


def test_two_reviewed_corrections_cannot_both_publish(setup,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from fastapi import HTTPException
    from app.services.revision_publication import publish_candidate
    from app.revision_models import EditorialPublication
    monkeypatch.setattr(get_settings(),'phase_b_publication_enabled',True)
    with Session(setup) as db:
        candidates=[reviewed_candidate(db,'First'),reviewed_candidate(db,'Second')]
    barrier=Barrier(2)
    def publish(cid):
        with Session(setup) as db:
            barrier.wait(timeout=10)
            try:
                publish_candidate(db,cid,2);db.commit();return 'published'
            except HTTPException as error:
                db.rollback();return error.detail
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(publish,candidates))
    assert sorted(results)==['STALE_REVISION','published']
    with Session(setup) as db:
        assert len(db.scalars(select(EditorialPublication)).all())==1


def test_practice_batches_lock_consistently_with_opposite_selection_order(setup,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.routers import practice
    with Session(setup) as db:
        db.add(User(id=2,email='other-learner@example.invalid',password_hash='no-login'))
        db.add(Question(id=2,exam_id=1,subject_id=1,topic_id=1,question_text='Second original',correct_option=2,verification_status='verified'))
        db.flush()
        db.add_all([QuestionOption(id=4+i,question_id=2,position=i,text=str(i)) for i in range(1,5)])
        db.add(ContentBinding(resource_kind='question',resource_id=2,source_id='original-fixture'));db.commit()
    barrier=Barrier(2)
    def selected(db,**kwargs):
        ids=[2,1] if kwargs['user_id']==1 else [1,2]
        rows={q.id:q for q in db.scalars(select(Question).options(selectinload(Question.options))).unique()}
        barrier.wait(timeout=10)
        return [rows[i] for i in ids]
    monkeypatch.setattr(practice,'select_practice_questions',selected)
    def request(uid):
        with Session(setup) as db:
            result=practice.get_practice_questions(topic_id=1,limit=2,mode='guided',similar_to=None,db=db,user=db.get(User,uid))
            return [q.id for q in result]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(request,[1,2]))
    assert results==[[2,1],[1,2]]
    with Session(setup) as db:
        assert len(db.scalars(select(DeliveryRevision)).all())==4


def test_editor_can_inspect_exact_candidate_asset_without_learner_grants(setup,tmp_path,monkeypatch):
    import hashlib
    from fastapi.testclient import TestClient
    from app.main import app
    from app.db import get_db
    from app.access_models import AssessmentAsset
    from app.core.security import create_access_token
    raw=b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="4"/></svg>'
    (tmp_path/'review.svg').write_bytes(raw)
    (tmp_path/'unrelated.svg').write_bytes(raw)
    monkeypatch.setattr(get_settings(),'private_asset_dir',str(tmp_path))
    monkeypatch.setattr(get_settings(),'reviewer_emails','independent@example.invalid')
    with Session(setup) as db:
        q=question(db);q.question_image_url='private://review.svg';q.verification_status='review_required'
        db.add(AssessmentAsset(asset_key='review.svg',content_sha256=hashlib.sha256(raw).hexdigest(),review_reference='synthetic'))
        db.commit();cid=reviewed_candidate(db)
        q.question_image_url=None;db.commit()
    def dependency():
        with Session(setup) as db:yield db
    app.dependency_overrides[get_db]=dependency
    try:
        client=TestClient(app)
        path=f'/api/v1/review/revisions/{cid}/assets/'
        reviewer={'Authorization':'Bearer '+create_access_token('2')}
        outsider={'Authorization':'Bearer '+create_access_token('1')}
        assert client.get(path+'review.svg').status_code==401
        assert client.get(path+'review.svg',headers=outsider).status_code==403
        response=client.get(path+'review.svg',headers=reviewer)
        assert response.status_code==200 and response.content==raw
        assert response.headers['cache-control']=='private, no-store'
        assert client.get(path+'unrelated.svg',headers=reviewer).status_code==404
        (tmp_path/'review.svg').write_bytes(b'altered')
        assert client.get(path+'review.svg',headers=reviewer).status_code==409
    finally:
        app.dependency_overrides.pop(get_db,None)


def test_pinned_mock_timing_survives_changed_runtime_defaults(setup,monkeypatch):
    from datetime import timedelta
    from app.services import mock_engine
    from app.services.revision_capture import bind_mock_timing
    from app.models import MockAttempt
    from app.routers.mocks import active_mock
    with Session(setup) as db:
        aid=seeded_pinned_mock(db,mode='full')
        attempt=db.get(MockAttempt,aid)
        start=attempt.started_at
        bind_mock_timing(db,attempt)
        monkeypatch.setattr(mock_engine,'SECTION_ORDER',['english','quant'])
        monkeypatch.setattr(mock_engine,'FULL_SECTION_SECONDS',60)
        monkeypatch.setattr(mock_engine,'FULL_TOTAL_SECONDS',120)
        timing=mock_engine.mock_timing(attempt,now=start+timedelta(seconds=901))
        assert timing['active_section_slug']=='general-awareness'
        assert timing['section_duration_seconds']==900 and timing['seconds_left']==2699
        assert mock_engine.mock_timing(attempt,now=start+timedelta(seconds=3600))['seconds_left']==0
        attempt.started_at-=timedelta(seconds=901);db.commit()
        status=active_mock(db,db.get(User,1))
        assert status['active_section_slug']=='general-awareness'
        assert status['section_duration_seconds']==900


def test_partial_mock_pins_fail_closed_without_backfilling(setup):
    from fastapi import HTTPException
    from app.models import MockAttempt, MockAttemptQuestion
    from app.services.revision_capture import bind_mock_timing
    with Session(setup) as db:
        aid=seeded_pinned_mock(db)
        db.add(Question(id=2,exam_id=1,subject_id=1,topic_id=1,question_text='Other',correct_option=1));db.flush()
        db.add(MockAttemptQuestion(attempt_id=aid,question_id=2,position=2,section_slug='quant'));db.commit()
        with pytest.raises(HTTPException) as error:bind_mock_timing(db,db.get(MockAttempt,aid))
        assert error.value.detail=='INCOMPLETE_DELIVERY_BLUEPRINT'
        assert len(db.scalars(select(DeliveryRevision)).all())==1


def test_legacy_mock_timing_is_not_reconstructed(setup):
    from app.models import MockAttempt
    from app.services.revision_capture import bind_mock_timing
    with Session(setup) as db:
        attempt=MockAttempt(user_id=1,exam_id=1,mode='topic',duration_minutes=20)
        db.add(attempt);db.commit()
        bind_mock_timing(db,attempt)
        assert not hasattr(attempt,'delivery_timing')
        assert not db.scalars(select(DeliveryRevision)).all()


def test_diagnostic_baseline_uses_pinned_key_difficulty_and_taxonomy(setup):
    from app.services.mock_engine import load_mock_attempt,submit_mock_attempt
    from app.routers.diagnostics import diagnostic_baseline
    from app.access_models import SourceGrant
    from fastapi import HTTPException
    with Session(setup) as db:
        aid=seeded_pinned_mock(db,mode='diagnostic')
        attempt,rows=load_mock_attempt(db,attempt_id=aid,user_id=1)
        submit_mock_attempt(db,attempt=attempt,rows=rows)
        before=diagnostic_baseline(db,db.get(User,1))
        q=question(db);q.correct_option=3;q.difficulty=3;q.topic_id=None
        db.add(Topic(id=2,subject_id=1,slug='new-curriculum-topic',name='New topic'));db.commit()
        after=diagnostic_baseline(db,db.get(User,1))
        assert before==after
        assert after['baseline']['correct']==1 and after['baseline']['sampled_topics']==1
        assert not after['baseline']['original_version_unknown']
        db.get(SourceGrant,(1,'original-fixture')).active=False;db.commit()
        with pytest.raises(HTTPException) as error:diagnostic_baseline(db,db.get(User,1))
        assert error.value.status_code==404


def test_analytics_uses_each_attempt_revision_and_export_keeps_results(setup):
    from app.access_models import CourseGrant, SourceGrant
    from app.routers.practice import submit_practice
    from app.routers.analytics import analytics_summary
    from app.routers.backup import export_user_data
    from app.schemas import PracticeSubmit
    with Session(setup) as db:
        db.add_all([CourseGrant(user_id=1,exam_id=1,active=True),SourceGrant(user_id=1,source_id='original-fixture',active=True)])
        q=question(db);q.expected_time_seconds=60;db.commit()
        token=issue_delivery(db,1,q).id;db.commit()
        submit_practice(PracticeSubmit(delivery_token=token,question_id=1,selected_option=2,time_seconds=30),db,db.get(User,1))
        before=analytics_summary(db,db.get(User,1))
        db.add(Topic(id=2,subject_id=1,slug='changed',name='Changed'));db.flush()
        q.topic_id=2;q.expected_time_seconds=10;q.correct_option=3;db.commit()
        after=analytics_summary(db,db.get(User,1))
        assert before==after
        exported=export_user_data(db,db.get(User,1))
        assert exported['question_attempts'][0]['is_correct'] is True
        assert exported['revision_references'][0]['delivery_id']==token
        assert 'payload' not in exported['revision_references'][0]


def test_active_mock_transition_dry_run_restart_and_compatible_rollback(setup,monkeypatch):
    from app.services.phase_b_transition import transition_active_mocks, legacy_checksum
    from app.services.mock_engine import load_mock_attempt, submit_mock_attempt, mock_timing
    from app.routers.mocks import review_mock
    from app.models import MockAttempt
    settings=get_settings()
    monkeypatch.setattr(settings,'phase_b_capture_enabled',False)
    monkeypatch.setattr(settings,'phase_b_publication_enabled',False)
    with Session(setup) as db:
        aid=seeded_pinned_mock(db,mode='full')
        before=legacy_checksum(db)
        started=db.get(MockAttempt,aid).started_at
    monkeypatch.setattr(settings,'phase_b_capture_enabled',True)
    monkeypatch.setattr(settings,'phase_b_transition_mode',True)
    blueprint={'full':{'duration_minutes':60,'positive_marks':2,'negative_marks':0.5,
        'section_order':['reasoning','general-awareness','quant','english'],'full_section_seconds':900}}
    with Session(setup) as db:
        with pytest.raises(ValueError,match='Coordinated'):
            transition_active_mocks(db,blueprint,exam_id=1,admission_frozen=False)
        report=transition_active_mocks(db,blueprint,exam_id=1,admission_frozen=True)
        assert report['legacy_checksums']==before and report['transitioned_attempt_ids']==[aid]
        db.rollback()
        assert not db.scalars(select(DeliveryRevision)).all()
        assert legacy_checksum(db)==before
    with Session(setup) as db:
        transition_active_mocks(db,blueprint,exam_id=1,admission_frozen=True);db.commit()
    verify(setup)  # Restart with the additive schema retained.
    with Session(setup) as db:
        assert transition_active_mocks(db,blueprint,exam_id=1,admission_frozen=True)['transitioned_attempt_ids']==[]
        assert legacy_checksum(db)==before
        db.rollback()
    monkeypatch.setattr(settings,'phase_b_transition_mode',False)
    # Compatible rollback keeps capture/readers on and publication off.
    with Session(setup) as db:
        question(db).correct_option=3;db.commit()
        attempt,rows=load_mock_attempt(db,attempt_id=aid,user_id=1)
        assert attempt.started_at==started and rows[0][0].selected_option==2
        assert mock_timing(attempt,now=started)['seconds_left']==3600
        assert rows[0][1].original_version_unknown is True
        assert submit_mock_attempt(db,attempt=attempt,rows=rows)['score']==2
        assert review_mock(aid,db,db.get(User,1))['questions'][0]['original_version_unknown']


def test_transition_refuses_changed_legacy_content(setup,monkeypatch):
    from app.services.phase_b_transition import transition_active_mocks
    monkeypatch.setattr(get_settings(),'phase_b_capture_enabled',False)
    with Session(setup) as db:
        seeded_pinned_mock(db)
        question(db).correct_option=3;db.commit()
    monkeypatch.setattr(get_settings(),'phase_b_capture_enabled',True)
    monkeypatch.setattr(get_settings(),'phase_b_transition_mode',True)
    monkeypatch.setattr(get_settings(),'phase_b_publication_enabled',False)
    with Session(setup) as db:
        with pytest.raises(ValueError,match='adjudication'):
            transition_active_mocks(db,{'topic':{'duration_minutes':20,'positive_marks':2,'negative_marks':0.5}},exam_id=1,admission_frozen=True)
        db.rollback()
        assert not db.scalars(select(DeliveryRevision)).all()


def test_reviewed_supplements_pin_payload_and_recheck_every_contributor(setup,monkeypatch):
    from datetime import datetime
    from fastapi import HTTPException
    from app.access_models import CourseGrant, SourceGrant
    from app.models import Lesson
    from app.routers.review import create_supplement,approve_supplement,RevisionReview
    from app.routers.practice import submit_practice,assist_delivery
    from app.schemas import PracticeSubmit
    from app.services.versioned_supplements import SupplementDraft
    from app.revision_models import TeachingSupplement
    monkeypatch.setattr(get_settings(),'phase_b_publication_enabled',True)
    with Session(setup) as db:
        db.add(User(id=2,email='supplement-reviewer@example.invalid',password_hash='no-login'))
        db.add(ContentSource(id='lesson-source',exam_id=1,private_use_approved=True,approval_reference='synthetic-only'))
        db.flush()
        db.add_all([CourseGrant(user_id=1,exam_id=1,active=True),SourceGrant(user_id=1,source_id='original-fixture',active=True),
            SourceGrant(user_id=1,source_id='lesson-source',active=True),
            Lesson(id=1,topic_id=1,title='Synthetic',intro='Intro',concept='Concept',is_published=True)])
        db.flush();db.add(ContentBinding(resource_kind='lesson',resource_id=1,source_id='lesson-source'));db.commit()
        draft=SupplementDraft(coaching={'standard_method':'REVIEWED_METHOD'},
            option_insights=[{'position':1,'insight_type':'misconception','knowledge_text':'REVIEWED_TRAP','source_reference':'synthetic'}],
            source_ids=['original-fixture'],contributors=[{'kind':'lesson','resource_id':1}])
        sid=create_supplement(1,draft,db,db.get(User,1))['supplement_id']
        evidence=RevisionReview(answer_verified=True,all_options_checked=True,instruction_reviewed=True,visual_reviewed=True,reference='synthetic independent check')
        with pytest.raises(HTTPException):approve_supplement(sid,evidence,db,db.get(User,1))
        approve_supplement(sid,evidence,db,db.get(User,2))
        delivery=issue_delivery(db,1,question(db));db.commit()
        assert assist_delivery(delivery.id,'hint',db,db.get(User,1))['coaching']['standard_method']=='REVIEWED_METHOD'
        payload=PracticeSubmit(delivery_token=delivery.id,question_id=1,selected_option=2,time_seconds=20)
        result=submit_practice(payload,db,db.get(User,1))
        assert result.coaching.standard_method=='REVIEWED_METHOD' and result.option_insights[0].knowledge_text=='REVIEWED_TRAP'
        db.get(Lesson,1).concept='Later correction';db.commit()
        assert submit_practice(payload,db,db.get(User,1))==result
        with pytest.raises(DBAPIError):
            db.execute(text('UPDATE teaching_supplements SET payload=:payload WHERE id=:id'),{'payload':'{}','id':sid});db.commit()
        db.rollback()
        assert db.get(TeachingSupplement,sid).created_at <= datetime.utcnow()
        db.get(SourceGrant,(1,'lesson-source')).active=False;db.commit()
        replay=submit_practice(payload,db,db.get(User,1))
        assert replay.correct and replay.explanation=='Four' and replay.coaching is None and replay.option_insights==[]
        db.get(SourceGrant,(1,'lesson-source')).active=True
        db.add(ContentSource(id='new-dependency',exam_id=1,private_use_approved=True,approval_reference='synthetic'))
        db.flush();db.add(ContentBinding(resource_kind='lesson',resource_id=1,source_id='new-dependency'));db.commit()
        assert submit_practice(payload,db,db.get(User,1)).coaching is None
        # A dependency change before independent approval also requires a new draft.
        pending=create_supplement(1,draft,db,db.get(User,1))['supplement_id']
        db.delete(db.get(ContentBinding,('lesson',1,'new-dependency')));db.commit()
        with pytest.raises(HTTPException,match='permissions'):
            approve_supplement(pending,evidence,db,db.get(User,2))


@pytest.mark.parametrize('mutation', ['equivalent_options','missing_solution','unapproved_source'])
def test_common_publication_gate_rejects_invalid_candidate(setup,monkeypatch,mutation):
    from fastapi import HTTPException
    from app.services.revision_publication import publish_candidate
    monkeypatch.setattr(get_settings(),'phase_b_publication_enabled',True)
    with Session(setup) as db:
        if mutation=='equivalent_options':
            q=question(db);q.options[0].text='1/2';q.options[1].text='0.5';db.commit()
        if mutation=='missing_solution':
            question(db).explanation='';db.commit()
        cid=reviewed_candidate(db, explanation='' if mutation=='missing_solution' else 'Reviewed correction')
        if mutation=='unapproved_source':
            db.get(ContentSource,'original-fixture').private_use_approved=False;db.commit()
        with pytest.raises(HTTPException) as error:publish_candidate(db,cid,2)
        assert error.value.status_code==422


def test_phase_b_refuses_direct_verified_import(setup):
    from app.content.import_schema import ImportedQuestion
    from app.services.question_import import import_question
    item=ImportedQuestion(exam_slug='ssc-cgl-tier-1',subject_slug='quant',question_text='Synthetic import',
        pattern_type='synthetic',correct_option=1,verification_status='verified',
        options=[{'position':i,'text':str(i)} for i in range(1,5)])
    with Session(setup) as db:
        with pytest.raises(ValueError,match='independently reviewed publication'):import_question(db,item)
        assert len(db.scalars(select(Question)).all())==1


def test_transition_http_admission_blocks_reads_and_writes(setup,monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(get_settings(),'phase_b_transition_mode',True)
    client=TestClient(app)
    for method,path in [('get','/api/v1/practice/questions'),('post','/api/v1/mocks/start'),('get','/api/v1/review/questions')]:
        response=getattr(client,method)(path)
        assert response.status_code==503 and response.json()['detail']=='MAINTENANCE_TRANSITION'
        assert response.headers['cache-control']=='no-store'
    assert client.get('/health').status_code==200


def test_reviewed_option_reordering_preserves_old_delivery_identity(setup,monkeypatch):
    from app.routers.review import create_revision,review_revision,_revision_digest,RevisionDraft,RevisionChanges,RevisionReview
    from app.services.revision_publication import publish_candidate
    from app.services.revision_capture import delivered_question
    from app.access_models import CourseGrant,SourceGrant
    monkeypatch.setattr(get_settings(),'phase_b_publication_enabled',True)
    with Session(setup) as db:
        db.add(User(id=2,email='order-review@example.invalid',password_hash='no-login'))
        db.add_all([CourseGrant(user_id=1,exam_id=1,active=True),SourceGrant(user_id=1,source_id='original-fixture',active=True)])
        db.commit()
        old=issue_delivery(db,1,question(db)).id;db.commit()
        draft=RevisionDraft(expected_digest=_revision_digest(db,question(db)),reason='Reviewed ordering correction',
            changes=RevisionChanges(verification_status='verified',correct_option=1),option_order=[2,1,3,4])
        cid=create_revision(1,draft,db,db.get(User,1))['candidate_id']
        review_revision(cid,RevisionReview(answer_verified=True,all_options_checked=True,instruction_reviewed=True,
            visual_reviewed=True,reference='Independent ordering check'),db,db.get(User,2))
        publish_candidate(db,cid,2);db.commit()
        new=issue_delivery(db,1,question(db)).id;db.commit()
        prior=delivered_question(db,kind='practice',delivery_id=old,user_id=1,current=question(db))
        latest=delivered_question(db,kind='practice',delivery_id=new,user_id=1,current=question(db))
        assert prior.correct_option==2 and [o.id for o in prior.options]==[1,2,3,4]
        assert latest.correct_option==1 and [o.id for o in latest.options]==[2,1,3,4]
        assert {o.id for o in latest.options}=={o.id for o in prior.options}


def test_additive_supplement_upgrade_preserves_existing_delivery_history(setup):
    from app.revision_models import TeachingSupplement,SupplementReview
    with Session(setup) as db:
        token=issue_delivery(db,1,question(db)).id;db.commit()
        before=read_evidence(db,'practice',token,1)
    # Model the previous Phase B schema, which had no supplement tables.
    with setup.begin() as connection:
        SupplementReview.__table__.drop(connection)
        TeachingSupplement.__table__.drop(connection)
    migrate(setup);migrate(setup);verify(setup)
    with Session(setup) as db:
        assert read_evidence(db,'practice',token,1)==before


def test_transition_keeps_same_duration_course_blueprints_separate(setup,monkeypatch):
    import json
    from app.models import MockAttempt,MockAttemptQuestion
    from app.access_models import CourseGrant,SourceGrant
    from app.services.phase_b_transition import transition_active_mocks
    from app.services.mock_engine import load_mock_attempt,submit_mock_attempt
    monkeypatch.setattr(get_settings(),'phase_b_capture_enabled',False)
    monkeypatch.setattr(get_settings(),'phase_b_publication_enabled',False)
    monkeypatch.setattr(get_settings(),'phase_b_transition_mode',True)
    with Session(setup) as db:
        first=seeded_pinned_mock(db,mode='full')
        db.add_all([Exam(id=2,slug='other-course',name='Other course',duration_minutes=60,positive_marks=5),
            User(id=2,email='other-course@example.invalid',password_hash='no-login')]);db.flush()
        db.add(Subject(id=2,exam_id=2,slug='other',name='Other'));db.flush()
        db.add(Question(id=2,exam_id=2,subject_id=2,question_text='Other course synthetic',correct_option=1,explanation='One',verification_status='verified'));db.flush()
        db.add_all([QuestionOption(id=i+4,question_id=2,position=i,text=str(i)) for i in range(1,5)])
        db.add(ContentSource(id='other-source',exam_id=2,private_use_approved=True,approval_reference='synthetic'));db.flush()
        db.add_all([ContentBinding(resource_kind='question',resource_id=2,source_id='other-source'),
            CourseGrant(user_id=2,exam_id=2,active=True),SourceGrant(user_id=2,source_id='other-source',active=True)])
        second=MockAttempt(user_id=2,exam_id=2,mode='full',duration_minutes=60);db.add(second);db.flush()
        second_id=second.id
        db.add(MockAttemptQuestion(attempt_id=second.id,question_id=2,section_slug='other',position=1,selected_option=1));db.commit()
    monkeypatch.setattr(get_settings(),'phase_b_capture_enabled',True)
    base={'duration_minutes':60,'positive_marks':2,'negative_marks':0.5,
        'section_order':['reasoning','general-awareness','quant','english'],'full_section_seconds':900}
    with Session(setup) as db:
        transition_active_mocks(db,{'full':base},exam_id=1,admission_frozen=True);db.commit()
        assert db.get(DeliveryRevision,('mock',str(second_id),2)) is None
        transition_active_mocks(db,{'full':{**base,'positive_marks':5,'section_order':['other'],'full_section_seconds':3600}},
                                exam_id=2,admission_frozen=True);db.commit()
        assert json.loads(db.get(DeliveryRevision,('mock',str(first),1)).blueprint)['positive_marks']==2
        assert json.loads(db.get(DeliveryRevision,('mock',str(second_id),2)).blueprint)['positive_marks']==5
        for aid,uid,score in [(first,1,2),(second_id,2,5)]:
            attempt,rows=load_mock_attempt(db,attempt_id=aid,user_id=uid)
            assert submit_mock_attempt(db,attempt=attempt,rows=rows)['score']==score
