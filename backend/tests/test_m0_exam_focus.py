"""M0-02: per-user exam focus does not mix or destroy learning data."""

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, ExamTarget, User, UserExamFocus
from app.routers.exams import ExamFocusUpdate, current_exam_focus, set_exam_focus


def test_focus_defaults_to_existing_cgl_without_writing_or_changing_targets():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        learner = User(email="focus-one@example.com", password_hash="x")
        exam = Exam(slug="ssc-cgl-tier-1", name="CGL", duration_minutes=60)
        db.add_all([learner, exam])
        db.flush()
        from datetime import date, timedelta
        target = ExamTarget(
            user_id=learner.id, exam_id=exam.id, exam_date=date.today() + timedelta(days=30),
            daily_minutes=120, is_active=True,
        )
        db.add(target)
        db.commit()

        result = current_exam_focus(db=db, user=learner)
        assert result["exam_slug"] == "ssc-cgl-tier-1"
        assert db.get(UserExamFocus, learner.id) is None

        result = set_exam_focus(
            ExamFocusUpdate(exam_slug="ssc-cgl-tier-1"), db=db, user=learner,
        )
        assert result["exam"]["status"] == "ready"
        assert db.get(UserExamFocus, learner.id).exam_slug == "ssc-cgl-tier-1"
        assert db.get(ExamTarget, target.id).is_active is True
        assert db.get(ExamTarget, target.id).daily_minutes == 120


def test_unpublished_stages_cannot_be_selected_even_by_direct_api_call():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        learner = User(email="focus-two@example.com", password_hash="x")
        db.add(learner)
        db.commit()
        for slug in (
            "ssc-cgl-tier-2", "ssc-je-telecom-paper-1", "ssc-je-telecom-paper-2"
        ):
            with pytest.raises(HTTPException) as exc:
                set_exam_focus(ExamFocusUpdate(exam_slug=slug), db=db, user=learner)
            assert exc.value.status_code == 409
        assert db.get(UserExamFocus, learner.id) is None


def test_focus_is_isolated_between_users_and_unknown_stage_is_404():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        first = User(email="first-focus@example.com", password_hash="x")
        second = User(email="second-focus@example.com", password_hash="x")
        db.add_all([first, second])
        db.commit()
        set_exam_focus(
            ExamFocusUpdate(exam_slug="ssc-cgl-tier-1"), db=db, user=first,
        )
        assert db.get(UserExamFocus, second.id) is None
        assert current_exam_focus(db=db, user=second)["exam_slug"] == "ssc-cgl-tier-1"
        with pytest.raises(HTTPException) as exc:
            set_exam_focus(
                ExamFocusUpdate(exam_slug="unlisted-exam"), db=db, user=second,
            )
        assert exc.value.status_code == 404
