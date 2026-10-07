from datetime import datetime

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Exam,
    MockAttempt,
    Question,
    QuestionAttempt,
    Subject,
    Topic,
    TopicMastery,
    User,
)
from app.routers.analytics import analytics_summary


def _base_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(email="analytics@example.com", password_hash="x")
    exam = Exam(
        slug="ssc-cgl-tier-1",
        name="SSC CGL Tier I",
        duration_minutes=60,
        positive_marks=2.0,
        negative_marks=0.5,
    )
    db.add_all([user, exam])
    db.flush()

    subject = Subject(
        exam_id=exam.id,
        slug="reasoning",
        name="Reasoning",
        sort_order=1,
    )
    db.add(subject)
    db.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="analogy",
        name="Analogy",
        priority=5,
    )
    db.add(topic)
    db.flush()

    questions = []
    for index in range(25):
        question = Question(
            exam_id=exam.id,
            subject_id=subject.id,
            topic_id=topic.id,
            question_text=f"Question {index}",
            correct_option=1,
            verification_status="verified",
            difficulty=(index % 3) + 1,
            expected_time_seconds=30,
            source_type="official",
        )
        db.add(question)
        questions.append(question)
    db.commit()
    return engine, db, user, exam, topic, questions


def test_analytics_baseline_does_not_present_zero_as_real_readiness():
    _, db, user, _, _, _ = _base_db()
    try:
        payload = analytics_summary(db=db, user=user)

        assert payload["overview"]["practice_attempts"] == 0
        assert payload["coach"]["evidence_level"] == "baseline"
        assert "baseline" in payload["coach"]["headline"].lower()
        assert payload["coach"]["primary_action"]["path"] == "/mocks"
        assert payload["weak_topics"] == []
    finally:
        db.close()


def test_analytics_developing_signal_is_not_overclaimed_as_established():
    _, db, user, _, topic, questions = _base_db()
    try:
        for index in range(10):
            db.add(
                QuestionAttempt(
                    user_id=user.id,
                    question_id=questions[index].id,
                    selected_option=1 if index < 6 else 2,
                    is_correct=index < 6,
                    time_seconds=24 + index,
                    confidence=2,
                    attempted_at=datetime.utcnow(),
                )
            )
        db.add(
            TopicMastery(
                user_id=user.id,
                topic_id=topic.id,
                mastery_score=58,
                attempts=10,
                correct=6,
            )
        )
        db.commit()

        payload = analytics_summary(db=db, user=user)

        assert payload["coach"]["evidence_level"] == "developing"
        assert "early signal" in payload["coach"]["primary_action"]["reason"].lower()
        assert payload["coach"]["secondary_action"]["path"] == "/mocks"
    finally:
        db.close()


def test_analytics_established_coach_is_actionable_and_batches_question_lookup():
    engine, db, user, exam, topic, questions = _base_db()
    question_selects = 0

    def count_question_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        nonlocal question_selects
        normalized = statement.lower()
        if normalized.lstrip().startswith("select") and " from questions" in normalized:
            question_selects += 1

    event.listen(engine, "before_cursor_execute", count_question_selects)
    try:
        for index in range(50):
            correct = index % 5 != 0
            db.add(
                QuestionAttempt(
                    user_id=user.id,
                    question_id=questions[index % len(questions)].id,
                    selected_option=1 if correct else 2,
                    is_correct=correct,
                    time_seconds=26 if correct else 42,
                    confidence=3 if correct else 2,
                    mistake_type=None if correct else "misread",
                    attempted_at=datetime.utcnow(),
                )
            )
        db.add(
            TopicMastery(
                user_id=user.id,
                topic_id=topic.id,
                mastery_score=72,
                attempts=50,
                correct=40,
            )
        )
        db.add(
            MockAttempt(
                user_id=user.id,
                exam_id=exam.id,
                mode="full",
                duration_minutes=60,
                status="submitted",
                submitted_at=datetime.utcnow(),
                score=120,
                correct_count=65,
                incorrect_count=20,
                unattempted_count=15,
            )
        )
        db.commit()

        payload = analytics_summary(db=db, user=user)

        assert payload["coach"]["evidence_level"] == "established"
        assert payload["coach"]["primary_action"]["path"].startswith("/practice?topic_id=")
        assert payload["errors"]["potential_score_gain"] == 25.0
        assert "marks" in payload["coach"]["summary"].lower()
        assert question_selects == 1
    finally:
        event.remove(engine, "before_cursor_execute", count_question_selects)
        db.close()
