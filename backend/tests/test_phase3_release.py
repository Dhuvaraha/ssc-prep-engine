from datetime import date, timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db import Base
from app.deps import get_content_reviewer
from app.models import Exam, Question, Subject, Topic, User
from app.routers.mocks import active_mock, review_mock
from app.routers.planner import PlannerConfig
from app.schemas import MockResponseUpdate, PracticeSubmit
from app.services.mock_engine import create_mock_attempt, submit_mock_attempt


def _build_release_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(email="phase3@example.com", password_hash="x")
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

    for idx in range(10):
        db.add(
            Question(
                exam_id=exam.id,
                subject_id=subject.id,
                topic_id=topic.id,
                question_text=f"release question {idx}",
                correct_option=1,
                verification_status="verified",
                difficulty=1 if idx == 1 else 2,
                expected_time_seconds=30,
                pattern_type="analogy-pattern" if idx == 1 else "general-pattern",
            )
        )

    db.commit()
    return db, user, topic


def test_active_mock_resume_endpoint_does_not_run_review_scoring():
    db, user, topic = _build_release_db()
    try:
        attempt, _ = create_mock_attempt(
            db,
            user_id=user.id,
            mode="topic",
            subject_slug=None,
            topic_id=topic.id,
        )

        payload = active_mock(db=db, user=user)

        assert payload["attempt_id"] == attempt.id
        assert payload["mode"] == "topic"
        assert 0 <= payload["seconds_left"] <= 20 * 60
    finally:
        db.close()


def test_mock_review_includes_section_score_and_accuracy():
    db, user, topic = _build_release_db()
    try:
        attempt, rows = create_mock_attempt(
            db,
            user_id=user.id,
            mode="topic",
            subject_slug=None,
            topic_id=topic.id,
        )
        # Topic mocks order easier questions first, so miss the first (easy) item
        # and answer the next item correctly. This also exercises slow-question
        # and weak-pattern reporting for the same missed question.
        rows[0][0].selected_option = 2
        rows[0][0].time_seconds = 50
        rows[1][0].selected_option = 1
        rows[1][0].time_seconds = 10
        db.commit()

        submit_mock_attempt(db, attempt=attempt, rows=rows)
        payload = review_mock(attempt.id, db=db, user=user)
        section = payload["sections"]["reasoning"]

        assert section["correct"] == 1
        assert section["incorrect"] == 1
        assert section["unattempted"] == 8
        assert section["score"] == 1.5
        assert section["accuracy"] == 50.0
        assert payload["easy_missed"] == 1
        assert payload["slow_questions"] == 1
        assert payload["weak_patterns"][0] == {
            "pattern": "analogy-pattern",
            "missed": 1,
        }
    finally:
        db.close()



def test_release_request_schemas_reject_impossible_option_positions():
    with pytest.raises(ValidationError):
        PracticeSubmit(
            question_id=1,
            selected_option=5,
            time_seconds=1,
            confidence=2,
        )

    with pytest.raises(ValidationError):
        MockResponseUpdate(question_id=1, selected_option=0)


def test_planner_config_rejects_past_exam_date():
    with pytest.raises(ValidationError):
        PlannerConfig(
            exam_date=date.today() - timedelta(days=1),
            daily_minutes=180,
        )


def test_content_review_requires_explicit_reviewer_allowlist(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "reviewer_emails", "reviewer@example.com")

    reviewer = User(email="reviewer@example.com", password_hash="x")
    ordinary = User(email="learner@example.com", password_hash="x")

    assert get_content_reviewer(reviewer) is reviewer
    with pytest.raises(HTTPException) as exc:
        get_content_reviewer(ordinary)
    assert exc.value.status_code == 403
