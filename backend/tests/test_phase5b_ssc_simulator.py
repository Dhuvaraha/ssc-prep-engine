from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, Question, Subject, User
from app.routers.mocks import get_mock_state, save_mock_response, submit_mock
from app.schemas import MockResponseUpdate
from app.services.mock_engine import (
    FULL_SECTION_SECONDS,
    SECTION_ORDER,
    create_mock_attempt,
    mock_timing,
)


def _full_mock_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(email="phase5b@example.com", password_hash="x")
    exam = Exam(
        slug="ssc-cgl-tier-1",
        name="SSC CGL Tier I",
        duration_minutes=60,
        positive_marks=2.0,
        negative_marks=0.5,
    )
    db.add_all([user, exam])
    db.flush()

    for sort_order, slug in enumerate(SECTION_ORDER, start=1):
        subject = Subject(
            exam_id=exam.id,
            slug=slug,
            name=slug,
            sort_order=sort_order,
        )
        db.add(subject)
        db.flush()
        for index in range(25):
            db.add(
                Question(
                    exam_id=exam.id,
                    subject_id=subject.id,
                    question_text=f"{slug} simulator question {index}",
                    correct_option=1,
                    verification_status="verified",
                    difficulty=(index % 3) + 1,
                    source_type="official" if index < 5 else "original",
                )
            )
    db.commit()
    return db, user


def test_full_mock_has_100_questions_and_25_per_section():
    db, user = _full_mock_db()
    try:
        attempt, rows = create_mock_attempt(
            db,
            user_id=user.id,
            mode="full",
            subject_slug=None,
        )

        assert attempt.duration_minutes == 60
        assert len(rows) == 100
        for slug in SECTION_ORDER:
            assert sum(row.section_slug == slug for row, _ in rows) == 25
    finally:
        db.close()


def test_full_mock_section_clock_advances_every_15_minutes():
    db, user = _full_mock_db()
    try:
        attempt, _ = create_mock_attempt(
            db,
            user_id=user.id,
            mode="full",
            subject_slug=None,
        )
        started = datetime(2026, 10, 7, 12, 0, 0)
        attempt.started_at = started

        cases = [
            (0, "reasoning", 0, 900, 3600),
            (899, "reasoning", 0, 1, 2701),
            (900, "general-awareness", 1, 900, 2700),
            (1799, "general-awareness", 1, 1, 1801),
            (1800, "quant", 2, 900, 1800),
            (2700, "english", 3, 900, 900),
            (3599, "english", 3, 1, 1),
        ]

        for elapsed, slug, index, section_left, total_left in cases:
            timing = mock_timing(attempt, now=started + timedelta(seconds=elapsed))
            assert timing["active_section_slug"] == slug
            assert timing["section_index"] == index
            assert timing["section_seconds_left"] == section_left
            assert timing["seconds_left"] == total_left

        finished = mock_timing(attempt, now=started + timedelta(seconds=3600))
        assert finished["active_section_slug"] is None
        assert finished["section_index"] is None
        assert finished["section_seconds_left"] == 0
        assert finished["seconds_left"] == 0
        assert finished["section_duration_seconds"] == FULL_SECTION_SECONDS
    finally:
        db.close()


def test_backend_rejects_answers_outside_active_full_mock_section():
    db, user = _full_mock_db()
    try:
        attempt, rows = create_mock_attempt(
            db,
            user_id=user.id,
            mode="full",
            subject_slug=None,
        )
        reasoning = next(row for row, _ in rows if row.section_slug == "reasoning")
        ga = next(row for row, _ in rows if row.section_slug == "general-awareness")

        with pytest.raises(HTTPException) as future:
            save_mock_response(
                attempt.id,
                MockResponseUpdate(question_id=ga.question_id, selected_option=1),
                db=db,
                user=user,
            )
        assert future.value.status_code == 409
        assert "locked" in str(future.value.detail).lower()

        save_mock_response(
            attempt.id,
            MockResponseUpdate(question_id=reasoning.question_id, selected_option=1),
            db=db,
            user=user,
        )

        attempt.started_at = datetime.utcnow() - timedelta(seconds=901)
        db.commit()

        with pytest.raises(HTTPException) as previous:
            save_mock_response(
                attempt.id,
                MockResponseUpdate(question_id=reasoning.question_id, selected_option=1),
                db=db,
                user=user,
            )
        assert previous.value.status_code == 409

        saved = save_mock_response(
            attempt.id,
            MockResponseUpdate(question_id=ga.question_id, selected_option=1),
            db=db,
            user=user,
        )
        assert saved["selected_option"] == 1
    finally:
        db.close()


def test_full_mock_state_exposes_server_authoritative_section_clock():
    db, user = _full_mock_db()
    try:
        attempt, _ = create_mock_attempt(
            db,
            user_id=user.id,
            mode="full",
            subject_slug=None,
        )
        attempt.started_at = datetime.utcnow() - timedelta(seconds=1805)
        db.commit()

        state = get_mock_state(attempt.id, db=db, user=user)

        assert state["active_section_slug"] == "quant"
        assert state["section_index"] == 2
        assert 890 <= state["section_seconds_left"] <= 895
        assert 1790 <= state["seconds_left"] <= 1795
    finally:
        db.close()


def test_full_mock_cannot_submit_before_final_section():
    db, user = _full_mock_db()
    try:
        attempt, _ = create_mock_attempt(
            db,
            user_id=user.id,
            mode="full",
            subject_slug=None,
        )

        with pytest.raises(HTTPException) as early:
            submit_mock(attempt.id, db=db, user=user)
        assert early.value.status_code == 409
        assert "final section" in str(early.value.detail).lower()

        attempt.started_at = datetime.utcnow() - timedelta(seconds=2701)
        db.commit()

        result = submit_mock(attempt.id, db=db, user=user)
        assert result["total_questions"] == 100
        assert result["unattempted"] == 100
    finally:
        db.close()
