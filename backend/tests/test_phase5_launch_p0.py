from datetime import timedelta

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.study_time import current_study_date
from app.db import Base
from app.models import (
    DailyPlanTask,
    Exam,
    ExamTarget,
    Lesson,
    MockAttempt,
    MockAttemptQuestion,
    Question,
    Subject,
    Topic,
    User,
)
from app.routers.content import content_tree
from app.routers.planner import _serialize
from app.services.mock_engine import load_mock_attempt
from app.services.planner import generate_today_plan
from app.services.practice_selector import select_practice_questions


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def _seed_exam(db):
    user = User(email="phase5@example.com", password_hash="x")
    exam = Exam(
        slug="ssc-cgl-tier-1",
        name="SSC CGL Tier I",
        duration_minutes=60,
        positive_marks=2.0,
        negative_marks=0.5,
    )
    db.add_all([user, exam])
    db.flush()
    return user, exam


def test_learn_tree_never_scans_question_bank():
    engine, db = _session()
    try:
        _, exam = _seed_exam(db)
        subject = Subject(exam_id=exam.id, slug="reasoning", name="Reasoning", sort_order=1)
        db.add(subject)
        db.flush()
        topic = Topic(subject_id=subject.id, slug="analogy", name="Analogy", priority=5)
        db.add(topic)
        db.flush()
        db.add(
            Lesson(
                topic_id=topic.id,
                title="Analogy",
                intro="Intro",
                concept="Concept",
                estimated_minutes=10,
                is_published=True,
            )
        )
        for index in range(250):
            db.add(
                Question(
                    exam_id=exam.id,
                    subject_id=subject.id,
                    topic_id=topic.id,
                    question_text=f"question {index}",
                    correct_option=1,
                    verification_status="verified",
                )
            )
        db.commit()

        statements: list[str] = []

        def record(_conn, _cursor, statement, _parameters, _context, _executemany):
            statements.append(statement.lower())

        event.listen(engine, "before_cursor_execute", record)
        result = content_tree(db=db)
        event.remove(engine, "before_cursor_execute", record)

        assert result["totals"]["topics"] == 1
        assert result["totals"]["lessons"] == 1
        assert all("questions" not in statement for statement in statements)
        assert all("question_options" not in statement for statement in statements)
    finally:
        db.close()


def test_broad_practice_uses_bounded_candidate_pool(monkeypatch):
    _, db = _session()
    try:
        user, exam = _seed_exam(db)
        question_count = 0
        for topic_index in range(50):
            subject = Subject(
                exam_id=exam.id,
                slug=f"subject-{topic_index}",
                name=f"Subject {topic_index}",
                sort_order=topic_index,
            )
            db.add(subject)
            db.flush()
            topic = Topic(
                subject_id=subject.id,
                slug=f"topic-{topic_index}",
                name=f"Topic {topic_index}",
                priority=3,
            )
            db.add(topic)
            db.flush()
            for question_index in range(10):
                db.add(
                    Question(
                        exam_id=exam.id,
                        subject_id=subject.id,
                        topic_id=topic.id,
                        question_text=f"q-{topic_index}-{question_index}",
                        correct_option=1,
                        verification_status="verified",
                        difficulty=(question_index % 3) + 1,
                    )
                )
                question_count += 1
        db.commit()
        assert question_count == 500

        import app.services.practice_selector as selector

        original = selector._hydrate_questions
        hydrated_sizes: list[int] = []

        def tracked(session, ids):
            hydrated_sizes.append(len(ids))
            return original(session, ids)

        monkeypatch.setattr(selector, "_hydrate_questions", tracked)

        selected = select_practice_questions(
            db,
            user_id=user.id,
            topic_id=None,
            limit=10,
            mode="mixed",
        )

        assert len(selected) == 10
        assert hydrated_sizes
        assert max(hydrated_sizes) <= 320
    finally:
        db.close()


def test_mock_resume_batches_question_loading():
    engine, db = _session()
    try:
        user, exam = _seed_exam(db)
        subject = Subject(exam_id=exam.id, slug="reasoning", name="Reasoning", sort_order=1)
        db.add(subject)
        db.flush()
        attempt = MockAttempt(
            user_id=user.id,
            exam_id=exam.id,
            mode="full",
            duration_minutes=60,
        )
        db.add(attempt)
        db.flush()

        for index in range(100):
            question = Question(
                exam_id=exam.id,
                subject_id=subject.id,
                question_text=f"mock question {index}",
                correct_option=1,
                verification_status="verified",
            )
            db.add(question)
            db.flush()
            db.add(
                MockAttemptQuestion(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    section_slug="reasoning",
                    position=index + 1,
                )
            )
        db.commit()
        attempt_id = attempt.id
        user_id = user.id
        db.expire_all()

        count = 0

        def record(_conn, _cursor, _statement, _parameters, _context, _executemany):
            nonlocal count
            count += 1

        event.listen(engine, "before_cursor_execute", record)
        loaded, rows = load_mock_attempt(db, attempt_id=attempt_id, user_id=user_id)
        event.remove(engine, "before_cursor_execute", record)

        assert loaded.id == attempt_id
        assert len(rows) == 100
        assert count <= 5
    finally:
        db.close()


def test_planner_fills_declared_budget_and_orders_learning_before_practice():
    _, db = _session()
    try:
        today = current_study_date()
        user, exam = _seed_exam(db)
        subject = Subject(exam_id=exam.id, slug="reasoning", name="Reasoning", sort_order=1)
        db.add(subject)
        db.flush()
        for index, priority in enumerate((5, 4, 3, 2), start=1):
            db.add(
                Topic(
                    subject_id=subject.id,
                    slug=f"topic-{index}",
                    name=f"Topic {index}",
                    priority=priority,
                )
            )
        db.add(
            ExamTarget(
                user_id=user.id,
                exam_id=exam.id,
                exam_date=today + timedelta(days=8),
                daily_minutes=240,
                is_active=True,
            )
        )
        db.commit()

        target, tasks = generate_today_plan(db, user_id=user.id, today=today)
        planned = sum(task.target_minutes for task in tasks)

        assert target.daily_minutes == 240
        assert 230 <= planned <= 240
        assert tasks[0].activity_type == "learn"
        assert tasks[1].activity_type == "practice"
        assert tasks[0].topic_id == tasks[1].topic_id
        assert all("weak" not in task.title.lower() for task in tasks)

        payload = _serialize(target, tasks)
        assert payload["target"]["days_left"] == 8
        assert payload["target"]["full_study_days"] == 7
    finally:
        db.close()


def test_existing_plan_is_returned_in_learning_sequence():
    _, db = _session()
    try:
        today = current_study_date()
        user, exam = _seed_exam(db)
        db.add(
            ExamTarget(
                user_id=user.id,
                exam_id=exam.id,
                exam_date=today + timedelta(days=20),
                daily_minutes=120,
                is_active=True,
            )
        )
        db.flush()
        db.add_all(
            [
                DailyPlanTask(
                    user_id=user.id,
                    plan_date=today,
                    activity_type="learn",
                    title="Learn first",
                    target_minutes=20,
                    priority=3,
                ),
                DailyPlanTask(
                    user_id=user.id,
                    plan_date=today,
                    activity_type="practice",
                    title="Practice second",
                    target_minutes=20,
                    priority=5,
                ),
            ]
        )
        db.commit()

        _, tasks = generate_today_plan(db, user_id=user.id, today=today)

        assert [task.title for task in tasks] == ["Learn first", "Practice second"]
    finally:
        db.close()
