from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.study_time import current_study_date
from app.db import Base
from app.models import (
    Exam,
    ExamTarget,
    Lesson,
    LessonBlock,
    Question,
    QuestionArchetype,
    Subject,
    Topic,
    User,
)
from app.services.planner import _sprint_stage, generate_today_plan
from app.services.teacher_readiness import collect_teacher_readiness


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed_topic(db, *, subject_slug="quant"):
    user = User(email="closure@example.com", password_hash="x")
    exam = Exam(slug="ssc-cgl-tier-1", name="SSC CGL Tier I", duration_minutes=60)
    db.add_all([user, exam])
    db.flush()
    subject = Subject(exam_id=exam.id, slug=subject_slug, name=subject_slug, sort_order=1)
    db.add(subject)
    db.flush()
    topic = Topic(subject_id=subject.id, slug="percentage", name="Percentage", priority=5)
    db.add(topic)
    db.flush()
    return user, exam, subject, topic


def test_sprint_stage_progression_is_explicit():
    assert _sprint_stage(8) == "normal"
    assert _sprint_stage(7) == "coverage"
    assert _sprint_stage(5) == "consolidate"
    assert _sprint_stage(3) == "test_and_repair"
    assert _sprint_stage(1) == "final_day"
    assert _sprint_stage(0) == "exam_day"


def test_final_day_avoids_full_mock_and_new_learning():
    db = _db()
    try:
        user, exam, _, topic = _seed_topic(db)
        today = current_study_date()
        db.add(
            ExamTarget(
                user_id=user.id,
                exam_id=exam.id,
                exam_date=today + timedelta(days=1),
                daily_minutes=180,
                is_active=True,
            )
        )
        db.commit()

        _, tasks = generate_today_plan(db, user_id=user.id, today=today)
        titles = [task.title.lower() for task in tasks]

        assert not any("full tier-i simulation" in title for title in titles)
        assert not any(task.activity_type == "learn" for task in tasks)
        assert any("final error-log revision" in title for title in titles)
        assert any(task.activity_type == "mock" and "sectional" in task.title.lower() for task in tasks)
        assert sum(task.target_minutes for task in tasks) >= 170
    finally:
        db.close()


def test_teacher_readiness_requires_teacher_blocks_archetype_and_three_verified_levels():
    db = _db()
    try:
        _, exam, subject, topic = _seed_topic(db)
        lesson = Lesson(
            topic_id=topic.id,
            title="Percentage",
            intro="Intro",
            concept="Concept",
            estimated_minutes=20,
            is_published=True,
        )
        db.add(lesson)
        db.flush()
        for order, block_type in enumerate(("concept", "recognition", "method", "shortcut", "trap"), start=1):
            db.add(
                LessonBlock(
                    lesson_id=lesson.id,
                    block_type=block_type,
                    title=block_type,
                    body=f"{block_type} body",
                    sort_order=order,
                    is_published=True,
                )
            )
        db.add(
            QuestionArchetype(
                topic_id=topic.id,
                slug="percentage-core",
                name="Percentage core",
                skill="percentage",
                recognition_cues="percent cue",
                canonical_method="normal method",
                shortcut_method="shortcut",
                common_trap="base trap",
                expected_time_seconds=45,
                is_published=True,
            )
        )
        for level in (1, 2, 3):
            db.add(
                Question(
                    exam_id=exam.id,
                    subject_id=subject.id,
                    topic_id=topic.id,
                    question_text=f"Level {level}",
                    correct_option=1,
                    explanation=f"Verified explanation {level}",
                    difficulty=level,
                    verification_status="verified",
                )
            )
        db.commit()

        report = collect_teacher_readiness(db)
        assert report["status"] == "ready"
        assert report["topics"] == 1
        assert report["ready_topics"] == 1

        lesson_block = db.query(LessonBlock).filter(LessonBlock.block_type == "shortcut").one()
        db.delete(lesson_block)
        db.commit()
        report = collect_teacher_readiness(db)
        assert report["status"] == "ready"
        assert "shortcut" in report["items"][0]["archetype_capabilities"]

        archetype = db.query(QuestionArchetype).one()
        archetype.shortcut_method = None
        db.commit()
        report = collect_teacher_readiness(db)
        assert report["status"] == "attention"
        assert report["items"][0]["failures"] == ["missing_blocks:shortcut"]
    finally:
        db.close()
