from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.study_time import current_study_date, utc_naive_to_study_date
from app.db import Base
from app.models import (
    Exam,
    ExamTarget,
    Question,
    RevisionItem,
    Subject,
    Topic,
    User,
)
from app.routers.revision import review_revision_item
from app.services.planner import generate_today_plan, rebuild_today_plan


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _add_exam(db, *, slug: str, name: str):
    exam = Exam(
        slug=slug,
        name=name,
        duration_minutes=60,
        positive_marks=2.0,
        negative_marks=0.5,
    )
    db.add(exam)
    db.flush()
    return exam


def _add_topic(db, *, exam: Exam, subject_slug: str, topic_slug: str, priority: int):
    subject = Subject(
        exam_id=exam.id,
        slug=subject_slug,
        name=subject_slug.replace("-", " ").title(),
        sort_order=1,
    )
    db.add(subject)
    db.flush()
    topic = Topic(
        subject_id=subject.id,
        slug=topic_slug,
        name=topic_slug.replace("-", " ").title(),
        priority=priority,
    )
    db.add(topic)
    db.flush()
    return subject, topic


def test_rebuild_preserves_completed_work_and_rebalances_remaining_budget():
    db = _session()
    try:
        today = date(2026, 10, 7)
        user = User(email="phase4c-rebalance@example.com", password_hash="x")
        db.add(user)
        exam = _add_exam(db, slug="ssc-cgl-tier-1", name="SSC CGL Tier I")
        subject = Subject(exam_id=exam.id, slug="reasoning", name="Reasoning", sort_order=1)
        db.add(subject)
        db.flush()
        for index, priority in enumerate((5, 4, 3), start=1):
            db.add(
                Topic(
                    subject_id=subject.id,
                    slug=f"topic-{index}",
                    name=f"Topic {index}",
                    priority=priority,
                )
            )
        db.flush()
        db.add(
            ExamTarget(
                user_id=user.id,
                exam_id=exam.id,
                exam_date=today + timedelta(days=30),
                daily_minutes=180,
                is_active=True,
            )
        )
        db.commit()

        _, initial = generate_today_plan(db, user_id=user.id, today=today)
        assert initial
        completed = initial[0]
        completed.status = "completed"
        db.commit()
        completed_id = completed.id
        completed_minutes = completed.target_minutes

        _, rebuilt = rebuild_today_plan(db, user_id=user.id, today=today)

        assert any(task.id == completed_id and task.status == "completed" for task in rebuilt)
        assert any(task.status == "pending" for task in rebuilt)
        assert sum(task.target_minutes for task in rebuilt) <= 180
        assert sum(
            task.target_minutes for task in rebuilt if task.status == "completed"
        ) == completed_minutes
    finally:
        db.close()


def test_planner_never_selects_topics_from_another_exam():
    db = _session()
    try:
        today = date(2026, 10, 7)
        user = User(email="phase4c-scope@example.com", password_hash="x")
        db.add(user)
        cgl = _add_exam(db, slug="ssc-cgl-tier-1", name="SSC CGL Tier I")
        je = _add_exam(db, slug="ssc-je", name="SSC JE")
        _, cgl_topic = _add_topic(
            db,
            exam=cgl,
            subject_slug="reasoning",
            topic_slug="cgl-analogy",
            priority=1,
        )
        _, je_topic = _add_topic(
            db,
            exam=je,
            subject_slug="technical",
            topic_slug="je-high-priority",
            priority=99,
        )
        db.add(
            ExamTarget(
                user_id=user.id,
                exam_id=cgl.id,
                exam_date=today + timedelta(days=60),
                daily_minutes=120,
                is_active=True,
            )
        )
        db.commit()

        _, tasks = generate_today_plan(db, user_id=user.id, today=today)
        topic_ids = {task.topic_id for task in tasks if task.topic_id is not None}

        assert cgl_topic.id in topic_ids
        assert je_topic.id not in topic_ids
    finally:
        db.close()


def test_revision_success_spacing_uses_real_exam_distance():
    db = _session()
    try:
        today = current_study_date()
        user = User(email="phase4c-revision@example.com", password_hash="x")
        db.add(user)
        exam = _add_exam(db, slug="ssc-cgl-tier-1", name="SSC CGL Tier I")
        subject, topic = _add_topic(
            db,
            exam=exam,
            subject_slug="quant",
            topic_slug="percentage",
            priority=5,
        )
        db.flush()
        question = Question(
            exam_id=exam.id,
            subject_id=subject.id,
            topic_id=topic.id,
            question_text="Revision spacing question",
            correct_option=1,
            verification_status="verified",
            pattern_type="percentage-core",
        )
        db.add(question)
        db.flush()
        item = RevisionItem(
            user_id=user.id,
            question_id=question.id,
            reason="wrong",
            successful_reviews=2,
            next_review_at=datetime.combine(today, datetime.min.time()),
            is_active=True,
        )
        db.add(item)
        db.add(
            ExamTarget(
                user_id=user.id,
                exam_id=exam.id,
                exam_date=today + timedelta(days=60),
                daily_minutes=180,
                is_active=True,
            )
        )
        db.commit()

        result = review_revision_item(item.id, success=True, db=db, user=user)

        assert result["successful_reviews"] == 3
        assert datetime.fromisoformat(result["next_review_at"]).date() == today + timedelta(days=14)
    finally:
        db.close()


def test_analytics_study_day_rolls_over_at_india_midnight():
    assert utc_naive_to_study_date(datetime(2026, 10, 6, 17, 59)) == date(2026, 10, 6)
    assert utc_naive_to_study_date(datetime(2026, 10, 6, 18, 30)) == date(2026, 10, 7)
