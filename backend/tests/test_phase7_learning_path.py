"""Stage promotion needs independent concept evidence, not repeated easy accuracy."""
from datetime import datetime, timedelta

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, Question, QuestionAttempt, Subject, Topic, User
from app.routers.practice import get_practice_questions, topic_learning_path
from app.services.learning_path import get_topic_learning_path


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="ladder@example.com", password_hash="x")
    exam = Exam(slug="ssc-cgl-tier-1", name="SSC CGL Tier I", duration_minutes=60)
    other = Exam(slug="ssc-je-telecom-paper-1", name="JE", duration_minutes=120)
    db.add_all([user, exam, other])
    db.flush()
    subject = Subject(exam_id=exam.id, slug="quant", name="Quant")
    other_subject = Subject(exam_id=other.id, slug="telecom-technical", name="Telecom")
    db.add_all([subject, other_subject])
    db.flush()
    topic = Topic(subject_id=subject.id, slug="percentage", name="Percentage")
    other_topic = Topic(subject_id=other_subject.id, slug="signals", name="Signals")
    db.add_all([topic, other_topic])
    db.flush()
    for difficulty in (1, 2, 3):
        for index in range(16):
            db.add(Question(
                exam_id=exam.id, subject_id=subject.id, topic_id=topic.id,
                question_text=f"Percentage {difficulty} question {index}",
                pattern_type=f"pattern-{index%4}",
                correct_option=1, difficulty=difficulty,
                verification_status="verified", explanation="Detailed verified calculation",
            ))
    db.add(Question(exam_id=other.id, subject_id=other_subject.id, topic_id=other_topic.id,
                    question_text="JE signal question", correct_option=1,
                    difficulty=3, verification_status="verified"))
    db.commit()
    return db, user, exam, other, topic, other_topic


def _answer(db, user, topic, difficulty, outcomes, *, hints=None, confidence=None):
    questions = db.query(Question).filter(
        Question.topic_id == topic.id, Question.difficulty == difficulty,
    ).order_by(Question.id).all()
    for index, correct in enumerate(outcomes):
        db.add(QuestionAttempt(
            user_id=user.id, question_id=questions[index].id,
            selected_option=1 if correct else 2, is_correct=correct,
            time_seconds=30, used_hint=bool(hints and hints[index]),
            confidence=(confidence[index] if confidence else 3),
            attempted_at=datetime.utcnow() + timedelta(seconds=index),
        ))
    db.commit()


def test_beginner_does_not_see_medium_or_hard_until_easy_evidence():
    db, user, exam, _, topic, _ = _session()
    try:
        initial = topic_learning_path(topic_id=topic.id, db=db, user=user)
        assert initial["level"] == 1
        assert initial["stage"] == "Foundation"
        first = get_practice_questions(
            topic_id=topic.id, mode="path", limit=10, similar_to=None, db=db, user=user,
        )
        assert len(first) == 10
        assert set(q.difficulty for q in first) == {1}

        _answer(db, user, topic, 1, [True, True, True, True, False])
        next_stage = topic_learning_path(topic_id=topic.id, db=db, user=user)
        assert next_stage["level"] == 2
        assert next_stage["levels"][1]["independent_correct"] == 4
        second = get_practice_questions(
            topic_id=topic.id, mode="path", limit=8, similar_to=None, db=db, user=user,
        )
        assert len(second) == 8
        assert set(q.difficulty for q in second) == {2}

        _answer(db, user, topic, 2, [True, True, True, False, True])
        advanced = topic_learning_path(topic_id=topic.id, db=db, user=user)
        assert advanced["level"] == 3
        assert all(q.difficulty == 3 for q in get_practice_questions(
            topic_id=topic.id, mode="path", limit=8, similar_to=None, db=db, user=user,
        ))
        assert "not full exam mastery" in advanced["next_unlock"]
    finally:
        db.close()


def test_repeated_same_question_and_hint_correct_do_not_unlock():
    db, user, exam, _, topic, _ = _session()
    try:
        q = db.query(Question).filter(Question.topic_id == topic.id).first()
        for _ in range(10):
            db.add(QuestionAttempt(
                user_id=user.id, question_id=q.id, selected_option=1,
                is_correct=True, time_seconds=15, confidence=3, used_hint=False,
                attempted_at=datetime.utcnow(),
            ))
        db.commit()
        assert get_topic_learning_path(
            db, user_id=user.id, topic_id=topic.id, exam_id=exam.id,
        )["levels"][1]["distinct_attempts"] == 1
        assert topic_learning_path(topic_id=topic.id, db=db, user=user)["level"] == 1

        _answer(db, user, topic, 1, [True, True, True, True, True],
                hints=[True, True, False, False, False],
                confidence=[3, 3, 3, 1, 3])
        state = topic_learning_path(topic_id=topic.id, db=db, user=user)
        assert state["level"] == 1
        assert state["levels"][1]["passed"] is False
    finally:
        db.close()


def test_unrelated_exam_stage_cannot_create_learning_evidence_or_see_topic():
    db, user, exam, other, topic, other_topic = _session()
    try:
        je_question = db.query(Question).filter(Question.exam_id == other.id).first()
        db.add(QuestionAttempt(
            user_id=user.id, question_id=je_question.id,
            selected_option=1, is_correct=True, confidence=3, used_hint=False,
            time_seconds=10, attempted_at=datetime.utcnow(),
        ))
        db.commit()
        assert topic_learning_path(topic_id=topic.id, db=db, user=user)["level"] == 1
        with pytest.raises(HTTPException) as error:
            topic_learning_path(topic_id=other_topic.id, db=db, user=user)
        assert error.value.status_code == 404
        with pytest.raises(HTTPException) as error:
            get_practice_questions(
                topic_id=None, limit=10, mode="path",
                similar_to=None, db=db, user=user,
            )
        assert error.value.status_code == 400
    finally:
        db.close()



def test_sparse_advanced_bank_does_not_falsely_unlock_challenge():
    db, user, exam, _, topic, _ = _session()
    try:
        hard_questions = db.query(Question).filter(
            Question.topic_id == topic.id, Question.difficulty == 3
        ).order_by(Question.id).all()
        for question in hard_questions[4:]:
            db.delete(question)
        db.commit()
        _answer(db, user, topic, 1, [True, True, True, True, False])
        _answer(db, user, topic, 2, [True, True, True, False, True])
        progress = topic_learning_path(topic_id=topic.id, db=db, user=user)
        assert progress["levels"][2]["passed"] is True
        assert progress["available_questions"][3] == 4
        assert progress["level"] == 2
        assert progress["content_blocked"] is True
        assert progress["blocked_level"] == 3
        assert "verified questions" in progress["next_unlock"]
    finally:
        db.close()
