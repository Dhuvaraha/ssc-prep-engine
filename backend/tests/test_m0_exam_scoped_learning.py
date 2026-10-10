"""M0-03 cross-exam isolation and honest difficulty coverage tests."""
from datetime import datetime

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Exam, MockAttempt, Question, QuestionAttempt, Subject, Topic, TopicMastery, User,
)
from app.routers.analytics import analytics_summary
from app.routers.practice import get_practice_questions, submit_practice
from app.services.practice_integrity import issue_delivery
from app.schemas import PracticeSubmit
from app.services.practice_selector import select_practice_questions


def _seed():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="isolation@example.com", password_hash="x")
    cgl = Exam(slug="ssc-cgl-tier-1", name="CGL I", duration_minutes=60)
    je = Exam(slug="ssc-je-telecom-paper-1", name="JE telecom", duration_minutes=120)
    db.add_all([user, cgl, je])
    db.flush()
    cgl_subject = Subject(exam_id=cgl.id, slug="quant", name="Quant", sort_order=1)
    je_subject = Subject(exam_id=je.id, slug="telecom-technical", name="Technical", sort_order=1)
    db.add_all([cgl_subject, je_subject])
    db.flush()
    ct = Topic(subject_id=cgl_subject.id, slug="percentages", name="Percentage")
    jt = Topic(subject_id=je_subject.id, slug="networks", name="Network analysis")
    db.add_all([ct, jt])
    db.flush()
    return db, user, cgl, je, ct, jt


def _question(db, exam, topic, n, difficulty):
    # Keep questions unique so duplicate guards don't hide a difficulty.
    return Question(
        exam_id=exam.id,
        subject_id=topic.subject_id,
        topic_id=topic.id,
        question_text=f"{exam.slug}: question {n} difficulty {difficulty}",
        correct_option=1,
        explanation="Verified worked solution and reasoning",
        difficulty=difficulty,
        expected_time_seconds=45,
        verification_status="verified",
    )


def test_cgl_practice_does_not_return_je_questions_even_mixed_or_similar():
    db, user, cgl, je, ct, jt = _seed()
    try:
        for i in range(15):
            db.add(_question(db, cgl, ct, i, i % 3 + 1))
            db.add(_question(db, je, jt, i, i % 3 + 1))
        db.commit()

        mixed = get_practice_questions(topic_id=None, limit=10, mode="mixed", similar_to=None, db=db, user=user)
        assert len(mixed) == 10
        assert all(db.get(Question, item.id).exam_id == cgl.id for item in mixed)

        wrong_question = db.query(Question).filter(Question.exam_id == je.id).first()
        assert wrong_question is not None
        with pytest.raises(HTTPException) as error:
            get_practice_questions(topic_id=jt.id, limit=5, mode="guided", similar_to=None, db=db, user=user)
        assert error.value.status_code == 404
        with pytest.raises(HTTPException) as error:
            get_practice_questions(topic_id=None, limit=5, mode="adaptive", similar_to=wrong_question.id, db=db, user=user)
        assert error.value.status_code == 404

        with pytest.raises(HTTPException) as error:
            submit_practice(
                payload=PracticeSubmit(
                    delivery_token=issue_delivery(db, user.id, wrong_question).id, question_id=wrong_question.id, selected_option=1,
                    time_seconds=15, confidence=3, used_hint=False,
                ), db=db, user=user,
            )
        assert error.value.status_code == 404
        assert db.query(QuestionAttempt).count() == 0
    finally:
        db.close()


def test_analytics_never_merge_je_questions_or_mock_score_into_cgl():
    db, user, cgl, je, ct, jt = _seed()
    try:
        cglq = _question(db, cgl, ct, 1, 1)
        jeq = _question(db, je, jt, 2, 3)
        db.add_all([cglq, jeq])
        db.flush()
        for i in range(3):
            db.add(QuestionAttempt(
                user_id=user.id, question_id=cglq.id,
                selected_option=1, is_correct=True, time_seconds=10, confidence=3,
                attempted_at=datetime.utcnow(),
            ))
        for i in range(15):
            db.add(QuestionAttempt(
                user_id=user.id, question_id=jeq.id,
                selected_option=2, is_correct=False, time_seconds=45, confidence=1,
                attempted_at=datetime.utcnow(),
            ))
        db.add_all([
            TopicMastery(user_id=user.id, topic_id=ct.id, mastery_score=70, attempts=3, correct=3),
            TopicMastery(user_id=user.id, topic_id=jt.id, mastery_score=0, attempts=15, correct=0),
            MockAttempt(user_id=user.id, exam_id=je.id, mode="full",
                        duration_minutes=120, status="submitted", correct_count=80,
                        incorrect_count=10, unattempted_count=10),
        ])
        db.commit()
        summary = analytics_summary(db=db, user=user)
        assert summary["overview"]["practice_attempts"] == 3
        assert summary["overview"]["accuracy"] == 100.0
        assert summary["overview"]["mastery"] == 70.0
        assert summary["recent_mocks"] == []
        assert summary["overview"]["readiness"] is None
        assert {item["subject_slug"] for item in summary["subject_breakdown"]} == {"quant"}
    finally:
        db.close()


def test_difficulty_ladder_can_reach_medium_and_hard_after_large_easy_bank():
    db, user, cgl, _, topic, _ = _seed()
    try:
        for difficulty, count in ((1, 170), (2, 20), (3, 20)):
            for i in range(count):
                db.add(_question(db, cgl, topic, difficulty * 1000 + i, difficulty))
        db.commit()
        chosen = select_practice_questions(
            db, user_id=user.id, topic_id=topic.id, limit=9,
            mode="ladder", exam_id=cgl.id,
        )
        assert len(chosen) == 9
        assert [q.difficulty for q in chosen] == [1, 2, 3] * 3
        assert all(q.exam_id == cgl.id for q in chosen)
    finally:
        db.close()
