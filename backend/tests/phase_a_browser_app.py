"""Synthetic-only browser test server. Never uses the configured DB engine."""
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.access_models import ContentBinding, ContentSource, CourseGrant, SourceGrant
from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import Exam, Lesson, Question, QuestionOption, Subject, Topic, User


fixture_directory = TemporaryDirectory(prefix="ssc_phase_a_browser_")
engine = create_engine("sqlite:///" + (Path(fixture_directory.name)/"synthetic.db").as_posix(), connect_args={"check_same_thread":False})
Base.metadata.create_all(engine)
factory = sessionmaker(engine)
with factory() as db:
    exam = Exam(slug="ssc-cgl-tier-1", name="Synthetic CGL", duration_minutes=60)
    db.add(exam); db.flush()
    user = User(email="browser-a@example.com", password_hash=hash_password("Synthetic-test-only-123!"))
    outsider = User(email="browser-b@example.com", password_hash=hash_password("Synthetic-test-only-123!"))
    db.add_all([user, outsider]); db.flush()
    source = ContentSource(id="browser-original", exam_id=exam.id, private_use_approved=True, approval_reference="original arithmetic fixture reviewed by construction")
    db.add(source); db.flush()
    db.add(CourseGrant(user_id=user.id, exam_id=exam.id, active=True))
    db.add(SourceGrant(user_id=user.id, source_id=source.id, active=True))
    for slug in ("reasoning", "general-awareness", "quant", "english"):
        subject = Subject(exam_id=exam.id, slug=slug, name="Synthetic "+slug)
        db.add(subject); db.flush()
        topic = Topic(subject_id=subject.id, slug="synthetic-"+slug, name="Original fixture "+slug)
        db.add(topic); db.flush()
        lesson = Lesson(topic_id=topic.id, title="SYNTHETIC_ACCOUNT_A_ONLY", intro="Original synthetic arithmetic for security testing.", concept="SYNTHETIC_ACCOUNT_A_ONLY: One plus one equals two.")
        db.add(lesson); db.flush()
        db.add(ContentBinding(resource_kind="lesson", resource_id=lesson.id, source_id=source.id))
        for i in range(10):
            q = Question(exam_id=exam.id,subject_id=subject.id,topic_id=topic.id,question_text=f"Synthetic {slug} fixture: {i}+1 = ?",correct_option=1,explanation=f"SYNTHETIC_ANSWER: {i}+1={i+1}.",difficulty=1 if i<3 else 2 if i<8 else 3,verification_status="verified",visibility="private")
            db.add(q); db.flush()
            db.add_all([QuestionOption(question_id=q.id,position=j,text=str(i+j)) for j in range(1,5)])
            db.add(ContentBinding(resource_kind="question",resource_id=q.id,source_id=source.id))
    db.commit()


def synthetic_db():
    with factory() as db:
        yield db


@asynccontextmanager
async def synthetic_lifespan(_):
    yield  # Deliberately does not invoke production startup/migration code.
    engine.dispose()
    fixture_directory.cleanup()


app.dependency_overrides[get_db] = synthetic_db
app.router.lifespan_context = synthetic_lifespan
