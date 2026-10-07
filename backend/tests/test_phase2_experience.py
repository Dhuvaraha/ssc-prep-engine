from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Exam,
    Question,
    RevisionItem,
    Subject,
    Topic,
    TopicMastery,
    User,
)
from app.services.mock_engine import create_mock_attempt
from app.services.practice_selector import select_practice_questions


def _build_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(email="phase2@example.com", password_hash="x")
    exam = Exam(
        slug="ssc-cgl-tier-1",
        name="SSC CGL Tier I",
        duration_minutes=60,
        positive_marks=2.0,
        negative_marks=0.5,
    )
    db.add_all([user, exam])
    db.flush()

    reasoning = Subject(exam_id=exam.id, slug="reasoning", name="Reasoning", sort_order=1)
    quant = Subject(exam_id=exam.id, slug="quant", name="Quant", sort_order=2)
    english = Subject(exam_id=exam.id, slug="english", name="English", sort_order=3)
    ga = Subject(exam_id=exam.id, slug="general-awareness", name="GA", sort_order=4)
    db.add_all([reasoning, quant, english, ga])
    db.flush()

    topic = Topic(subject_id=reasoning.id, slug="analogy", name="Analogy", priority=5)
    second = Topic(subject_id=reasoning.id, slug="series", name="Series", priority=4)
    db.add_all([topic, second])
    db.flush()

    questions = []
    for idx in range(30):
        q = Question(
            exam_id=exam.id,
            subject_id=reasoning.id,
            topic_id=topic.id if idx < 20 else second.id,
            question_text=f"reasoning {idx}",
            correct_option=1,
            verification_status="verified",
            difficulty=(idx % 3) + 1,
            expected_time_seconds=20 + idx,
            year=2024 if idx % 2 == 0 else None,
            source_type="official" if idx % 2 == 0 else "original",
            pattern_type=f"pattern-{idx % 5}",
        )
        db.add(q)
        questions.append(q)

    for subject in [quant, english, ga]:
        for idx in range(25):
            db.add(
                Question(
                    exam_id=exam.id,
                    subject_id=subject.id,
                    question_text=f"{subject.slug} {idx}",
                    correct_option=1,
                    verification_status="verified",
                    difficulty=(idx % 3) + 1,
                    expected_time_seconds=30,
                )
            )

    db.flush()
    db.add(TopicMastery(user_id=user.id, topic_id=topic.id, mastery_score=20, attempts=5, correct=1))
    db.add(
        RevisionItem(
            user_id=user.id,
            question_id=questions[0].id,
            reason="wrong",
            next_review_at=datetime.utcnow() - timedelta(minutes=1),
            is_active=True,
        )
    )
    db.commit()
    return db, user, topic


def test_phase2_practice_modes_return_valid_sets():
    db, user, topic = _build_db()
    try:
        for mode in ["guided", "topic", "adaptive", "pyq", "mixed", "weak", "revision", "speed", "ladder", "timed"]:
            selected = select_practice_questions(
                db,
                user_id=user.id,
                topic_id=topic.id if mode in {"guided", "topic", "pyq", "speed", "ladder", "timed"} else None,
                limit=8,
                mode=mode,
            )
            assert selected, mode
            assert len(selected) <= 8
            assert all(q.correct_option is not None for q in selected)

        revision = select_practice_questions(
            db,
            user_id=user.id,
            topic_id=None,
            limit=8,
            mode="revision",
        )
        assert revision[0].question_text == "reasoning 0"
    finally:
        db.close()


def test_topic_mock_builds_focused_test():
    db, user, topic = _build_db()
    try:
        attempt, rows = create_mock_attempt(
            db,
            user_id=user.id,
            mode="topic",
            subject_slug=None,
            topic_id=topic.id,
        )
        assert attempt.duration_minutes == 20
        assert len(rows) == 20
        assert all(question.topic_id == topic.id for _, question in rows)
        assert all(row.section_slug == "reasoning" for row, _ in rows)
    finally:
        db.close()
