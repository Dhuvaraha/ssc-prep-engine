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


def seeded_pinned_mock(db):
    from app.models import MockAttempt, MockAttemptQuestion
    from app.access_models import CourseGrant, SourceGrant, AssessmentDelivery
    from app.services.revision_capture import pin_delivery
    from app.services.practice_integrity import question_digest
    db.add_all([CourseGrant(user_id=1,exam_id=1,active=True),
                SourceGrant(user_id=1,source_id='original-fixture',active=True)])
    attempt=MockAttempt(user_id=1,exam_id=1,mode='topic',duration_minutes=20)
    db.add(attempt);db.flush()
    q=question(db)
    db.add(MockAttemptQuestion(attempt_id=attempt.id,question_id=1,section_slug='quant',position=1,selected_option=2))
    db.add(AssessmentDelivery(attempt_id=attempt.id,question_id=1,content_digest=question_digest(q),correct_option=2))
    pin_delivery(db,kind='mock',delivery_id=attempt.id,user_id=1,question=q,
                 blueprint={'positive_marks':2,'negative_marks':0.5})
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
