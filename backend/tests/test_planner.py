from datetime import date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, ExamTarget, Subject, Topic, User
from app.services.planner import generate_today_plan


def test_daily_plan_is_generated_with_study_tasks():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    today = date(2026, 10, 5)

    with Session() as db:
        user = User(email="planner@example.com", password_hash="x")
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
        db.add_all(
            [
                Topic(subject_id=subject.id, slug="coding-decoding", name="Coding-Decoding", priority=5),
                Topic(subject_id=subject.id, slug="number-series", name="Number Series", priority=4),
                Topic(subject_id=subject.id, slug="analogy", name="Analogy", priority=3),
            ]
        )
        db.add(
            ExamTarget(
                user_id=user.id,
                exam_id=exam.id,
                exam_date=today + timedelta(days=10),
                daily_minutes=180,
                is_active=True,
            )
        )
        db.commit()

        target, tasks = generate_today_plan(db, user_id=user.id, today=today)

        assert target.daily_minutes == 180
        assert tasks
        assert any(task.activity_type == "learn" for task in tasks)
        assert any(task.activity_type == "practice" for task in tasks)
        assert sum(task.target_minutes for task in tasks) <= 180
