from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, ExamTarget, Question, Subject, User
from app.routers.mocks import get_mock_state, save_mock_response, start_mock, submit_mock
from app.schemas import MockResponseUpdate, MockStartRequest
from app.services.mock_engine import SECTION_ORDER, create_mock_attempt
from app.services.planner import ensure_exam_target


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed_full_mock(db):
    user = User(email="phase6b@example.com", password_hash="x")
    exam = Exam(
        slug="ssc-cgl-tier-1",
        name="SSC CGL Tier I",
        duration_minutes=60,
        positive_marks=2.0,
        negative_marks=0.5,
    )
    db.add_all([user, exam])
    db.flush()
    for order, slug in enumerate(SECTION_ORDER, start=1):
        subject = Subject(exam_id=exam.id, slug=slug, name=slug, sort_order=order)
        db.add(subject)
        db.flush()
        for index in range(25):
            db.add(
                Question(
                    exam_id=exam.id,
                    subject_id=subject.id,
                    question_text=("Long question " + ("context " * 150)) if index == 0 else f"{slug} q{index}",
                    question_image_url="private://question.svg" if index == 0 else None,
                    correct_option=1,
                    verification_status="verified",
                    difficulty=(index % 3) + 1,
                )
            )
    db.commit()
    return user, exam


def test_exam_target_update_collapses_duplicate_active_targets():
    db = _db()
    try:
        user = User(email="targets@example.com", password_hash="x")
        cgl = Exam(slug="ssc-cgl-tier-1", name="CGL", duration_minutes=60)
        je = Exam(slug="ssc-je", name="JE", duration_minutes=120)
        db.add_all([user, cgl, je])
        db.flush()
        db.add_all(
            [
                ExamTarget(user_id=user.id, exam_id=cgl.id, exam_date=datetime.utcnow().date() + timedelta(days=10), daily_minutes=120, is_active=True),
                ExamTarget(user_id=user.id, exam_id=je.id, exam_date=datetime.utcnow().date() + timedelta(days=20), daily_minutes=120, is_active=True),
            ]
        )
        db.commit()

        target = ensure_exam_target(
            db,
            user_id=user.id,
            exam_slug="ssc-cgl-tier-1",
            exam_date=datetime.utcnow().date() + timedelta(days=7),
            daily_minutes=240,
        )

        active = list(db.scalars(select(ExamTarget).where(ExamTarget.user_id == user.id, ExamTarget.is_active.is_(True))))
        assert len(active) == 1
        assert active[0].id == target.id
        assert target.daily_minutes == 240
    finally:
        db.close()


def test_mock_resume_round_trips_saved_response_and_long_visual_question():
    db = _db()
    try:
        user, _ = _seed_full_mock(db)
        attempt, rows = create_mock_attempt(db, user_id=user.id, mode="full", subject_slug=None)
        first = rows[0][0]
        save_mock_response(
            attempt.id,
            MockResponseUpdate(
                question_id=first.question_id,
                selected_option=2,
                marked_for_review=True,
                time_seconds=47.5,
            ),
            db=db,
            user=user,
        )

        state = get_mock_state(attempt.id, db=db, user=user)
        restored = next(item for item in state["responses"] if item["question_id"] == first.question_id)
        assert restored == {
            "question_id": first.question_id,
            "selected_option": 2,
            "marked_for_review": True,
            "time_seconds": 47.5,
        }
        assert len(rows[0][1].question_text) > 500
        assert rows[0][1].question_image_url == "private://question.svg"
    finally:
        db.close()


def test_expired_full_mock_rejects_late_write_but_submits_once_idempotently():
    db = _db()
    try:
        user, _ = _seed_full_mock(db)
        attempt, rows = create_mock_attempt(db, user_id=user.id, mode="full", subject_slug=None)
        attempt.started_at = datetime.utcnow() - timedelta(seconds=3605)
        db.commit()

        with pytest.raises(HTTPException) as late:
            save_mock_response(
                attempt.id,
                MockResponseUpdate(question_id=rows[-1][0].question_id, selected_option=1),
                db=db,
                user=user,
            )
        assert late.value.status_code == 409
        assert "time is over" in str(late.value.detail).lower()

        first = submit_mock(attempt.id, db=db, user=user)
        second = submit_mock(attempt.id, db=db, user=user)
        assert first == second
        assert first["total_questions"] == 100
        assert first["unattempted"] == 100
    finally:
        db.close()


def test_mock_state_isolated_between_users():
    db = _db()
    try:
        user, _ = _seed_full_mock(db)
        other = User(email="other@example.com", password_hash="x")
        db.add(other)
        db.commit()
        attempt, _ = create_mock_attempt(db, user_id=user.id, mode="full", subject_slug=None)

        with pytest.raises(HTTPException) as denied:
            get_mock_state(attempt.id, db=db, user=other)
        assert denied.value.status_code == 404
    finally:
        db.close()


def test_duplicate_start_returns_existing_active_attempt_instead_of_creating_two():
    db = _db()
    try:
        user, _ = _seed_full_mock(db)
        payload = MockStartRequest(mode="full", subject_slug=None, topic_id=None)
        first = start_mock(payload, db=db, user=user)
        second = start_mock(payload, db=db, user=user)

        assert first.attempt_id == second.attempt_id
        active = list(db.scalars(select(__import__("app.models", fromlist=["MockAttempt"]).MockAttempt).where(
            __import__("app.models", fromlist=["MockAttempt"]).MockAttempt.user_id == user.id,
            __import__("app.models", fromlist=["MockAttempt"]).MockAttempt.status == "in_progress",
        )))
        assert len(active) == 1
