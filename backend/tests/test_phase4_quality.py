from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload
from sqlalchemy import select

from app.db import Base
from app.models import Exam, Question, QuestionOption, Subject, Topic, User
from app.services.practice_selector import select_practice_questions
from app.services.question_quality import question_content_signature, unique_questions


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    user = User(email="phase4@example.com", password_hash="x")
    exam = Exam(slug="ssc-cgl-tier-1", name="SSC CGL", duration_minutes=60)
    db.add_all([user, exam])
    db.flush()
    subject = Subject(exam_id=exam.id, slug="quant", name="Quant", sort_order=1)
    db.add(subject)
    db.flush()
    topic = Topic(subject_id=subject.id, slug="trains", name="Trains", priority=5)
    db.add(topic)
    db.flush()
    db.commit()
    return db, user, exam, subject, topic


def _add_question(db, exam, subject, topic, text, *, image=None, suffix=""):
    question = Question(
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=topic.id,
        question_text=text,
        question_image_url=image,
        correct_option=1,
        verification_status="verified",
        difficulty=2,
    )
    db.add(question)
    db.flush()
    for position, value in enumerate(["10", "20", "30", "40"], start=1):
        db.add(
            QuestionOption(
                question_id=question.id,
                position=position,
                text=value + suffix,
            )
        )
    db.commit()
    return db.scalar(
        select(Question)
        .options(selectinload(Question.options))
        .where(Question.id == question.id)
    )


def test_question_signature_collapses_exact_duplicate_content():
    db, _, exam, subject, topic = _db()
    try:
        first = _add_question(db, exam, subject, topic, "  Same   question ")
        second = _add_question(db, exam, subject, topic, "same question")
        assert question_content_signature(first) == question_content_signature(second)
        assert len(unique_questions([first, second])) == 1
    finally:
        db.close()


def test_question_signature_keeps_visual_variants_distinct():
    db, _, exam, subject, topic = _db()
    try:
        first = _add_question(db, exam, subject, topic, "Choose the figure", image="private://a.png")
        second = _add_question(db, exam, subject, topic, "Choose the figure", image="private://b.png")
        assert question_content_signature(first) != question_content_signature(second)
        assert len(unique_questions([first, second])) == 2
    finally:
        db.close()


def test_practice_pool_never_returns_exact_duplicates():
    db, user, exam, subject, topic = _db()
    try:
        _add_question(db, exam, subject, topic, "Repeated question")
        _add_question(db, exam, subject, topic, "Repeated question")
        _add_question(db, exam, subject, topic, "Unique question", suffix="-u")

        selected = select_practice_questions(
            db,
            user_id=user.id,
            topic_id=topic.id,
            limit=10,
            mode="guided",
        )

        assert len(selected) == 2
        assert len({question_content_signature(item) for item in selected}) == 2
    finally:
        db.close()
