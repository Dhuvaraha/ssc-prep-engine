from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, Question, QuestionAttempt, Subject, Topic, User
from app.routers.analytics import analytics_summary
from app.services.mock_engine import _difficulty_targets, _questions_for_subject
from app.services.mock_readiness import collect_mock_readiness
from app.services.practice_selector import select_practice_questions


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_mock_blueprint_balances_difficulty_and_prefers_official_content():
    db = _db()
    try:
        exam = Exam(slug="ssc-cgl-tier-1", name="CGL", duration_minutes=60)
        db.add(exam)
        db.flush()
        subject = Subject(exam_id=exam.id, slug="reasoning", name="Reasoning", sort_order=1)
        db.add(subject)
        db.flush()

        for difficulty in (1, 2, 3):
            for index in range(15):
                db.add(
                    Question(
                        exam_id=exam.id,
                        subject_id=subject.id,
                        question_text=f"official d{difficulty} {index}",
                        correct_option=1,
                        difficulty=difficulty,
                        year=2025,
                        source_type="official",
                        source_reference="ssc-official-fixture",
                        pattern_type=f"reasoning-d{difficulty}",
                        explanation="Verified worked explanation",
                        expected_time_seconds=45,
                        verification_status="verified",
                    )
                )
            for index in range(20):
                db.add(
                    Question(
                        exam_id=exam.id,
                        subject_id=subject.id,
                        question_text=f"original d{difficulty} {index}",
                        correct_option=1,
                        difficulty=difficulty,
                        source_type="original",
                        source_reference="original-fixture-v1",
                        pattern_type=f"reasoning-d{difficulty}",
                        explanation="Verified worked explanation",
                        expected_time_seconds=45,
                        verification_status="verified",
                    )
                )
        db.commit()

        selected = _questions_for_subject(
            db,
            exam_id=exam.id,
            subject_slug="reasoning",
            count=25,
        )

        assert len(selected) == 25
        assert all(question.source_type == "official" for question in selected)
        expected = _difficulty_targets(25)
        actual = {
            difficulty: sum(question.difficulty == difficulty for question in selected)
            for difficulty in (1, 2, 3)
        }
        assert actual == expected == {1: 7, 2: 12, 3: 6}

        readiness = collect_mock_readiness(db)
        section = readiness["sections"][0]
        assert readiness["status"] == "attention"
        assert section["subject"] == "reasoning"
        assert section["ready"] is True
        assert section["exam_ready"] >= 25
        assert section["high_fidelity"] >= 25
        assert section["pyq_priority_available"] is True
    finally:
        db.close()


def test_similar_question_selector_prefers_same_verified_pattern_and_excludes_anchor():
    db = _db()
    try:
        user = User(email="similar@example.com", password_hash="x")
        exam = Exam(slug="ssc-cgl-tier-1", name="CGL", duration_minutes=60)
        db.add_all([user, exam])
        db.flush()
        subject = Subject(exam_id=exam.id, slug="quant", name="Quant", sort_order=1)
        db.add(subject)
        db.flush()
        topic = Topic(subject_id=subject.id, slug="ratio", name="Ratio", priority=5)
        db.add(topic)
        db.flush()
        anchor = Question(
            exam_id=exam.id,
            subject_id=subject.id,
            topic_id=topic.id,
            pattern_type="ratio-core",
            question_text="anchor",
            correct_option=1,
            verification_status="verified",
        )
        same = Question(
            exam_id=exam.id,
            subject_id=subject.id,
            topic_id=topic.id,
            pattern_type="ratio-core",
            question_text="same pattern",
            correct_option=1,
            verification_status="verified",
        )
        other = Question(
            exam_id=exam.id,
            subject_id=subject.id,
            topic_id=topic.id,
            pattern_type="ratio-variation",
            question_text="other pattern",
            correct_option=1,
            verification_status="verified",
        )
        db.add_all([anchor, same, other])
        db.commit()

        selected = select_practice_questions(
            db,
            user_id=user.id,
            topic_id=topic.id,
            limit=1,
            mode="adaptive",
            similar_to_question_id=anchor.id,
        )

        assert [question.id for question in selected] == [same.id]
    finally:
        db.close()


def test_analytics_exposes_first_vs_repeat_gain_and_time_leakage():
    db = _db()
    try:
        user = User(email="curve@example.com", password_hash="x")
        exam = Exam(slug="ssc-cgl-tier-1", name="CGL", duration_minutes=60)
        db.add_all([user, exam])
        db.flush()
        subject = Subject(exam_id=exam.id, slug="quant", name="Quant", sort_order=1)
        db.add(subject)
        db.flush()
        topic = Topic(subject_id=subject.id, slug="percentage", name="Percentage", priority=5)
        db.add(topic)
        db.flush()
        q1 = Question(
            exam_id=exam.id,
            subject_id=subject.id,
            topic_id=topic.id,
            question_text="q1",
            correct_option=1,
            expected_time_seconds=30,
            verification_status="verified",
        )
        q2 = Question(
            exam_id=exam.id,
            subject_id=subject.id,
            topic_id=topic.id,
            question_text="q2",
            correct_option=1,
            expected_time_seconds=30,
            verification_status="verified",
        )
        db.add_all([q1, q2])
        db.flush()
        start = datetime(2026, 10, 7, 10, 0, 0)
        db.add_all(
            [
                QuestionAttempt(user_id=user.id, question_id=q1.id, selected_option=2, is_correct=False, time_seconds=60, confidence=3, attempted_at=start),
                QuestionAttempt(user_id=user.id, question_id=q2.id, selected_option=1, is_correct=True, time_seconds=25, confidence=3, attempted_at=start + timedelta(minutes=1)),
                QuestionAttempt(user_id=user.id, question_id=q1.id, selected_option=1, is_correct=True, time_seconds=20, confidence=3, attempted_at=start + timedelta(minutes=2)),
            ]
        )
        db.commit()

        payload = analytics_summary(db=db, user=user)
        curve = payload["learning_curve"]

        assert curve["first_attempts"] == 2
        assert curve["first_attempt_accuracy"] == 50.0
        assert curve["repeat_attempts"] == 1
        assert curve["repeat_attempt_accuracy"] == 100.0
        assert curve["repeat_gain"] == 50.0
        assert curve["slow_attempts"] == 1
        assert curve["time_over_target_seconds"] == 30.0
    finally:
        db.close()
