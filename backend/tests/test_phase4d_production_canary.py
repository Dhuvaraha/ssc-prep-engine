from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import (
    Bookmark,
    DailyPlanTask,
    Exam,
    ExamTarget,
    Flashcard,
    FlashcardProgress,
    Lesson,
    MockAttempt,
    Question,
    QuestionAttempt,
    QuestionOption,
    RevisionItem,
    Subject,
    Topic,
    TopicMastery,
    User,
)
from app.services.learner_canary import run_production_learner_canary


def _seed_canary_database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with Session() as db:
        exam = Exam(
            slug="ssc-cgl-tier-1",
            name="SSC CGL Tier I",
            duration_minutes=60,
            positive_marks=2.0,
            negative_marks=0.5,
        )
        db.add(exam)
        db.flush()

        section_specs = [
            ("reasoning", "Reasoning", "analogy", "Analogy", 10),
            ("general-awareness", "General Awareness", "science", "Science", 2),
            ("quant", "Quantitative Aptitude", "percentage", "Percentage", 2),
            ("english", "English", "grammar", "Grammar", 2),
        ]

        for sort_order, (subject_slug, subject_name, topic_slug, topic_name, priority) in enumerate(section_specs, start=1):
            subject = Subject(
                exam_id=exam.id,
                slug=subject_slug,
                name=subject_name,
                sort_order=sort_order,
            )
            db.add(subject)
            db.flush()

            topic = Topic(
                subject_id=subject.id,
                slug=topic_slug,
                name=topic_name,
                priority=priority,
            )
            db.add(topic)
            db.flush()

            db.add(
                Lesson(
                    topic_id=topic.id,
                    title=f"{topic_name} lesson",
                    intro="Intro",
                    concept="Concept",
                    shortcut="Shortcut",
                    worked_example="Worked example",
                    estimated_minutes=10,
                    sort_order=1,
                    is_published=True,
                )
            )

            question_count = 10 if subject_slug == "reasoning" else 1
            for index in range(question_count):
                question = Question(
                    exam_id=exam.id,
                    subject_id=subject.id,
                    topic_id=topic.id,
                    question_text=f"{subject_slug} canary question {index}",
                    correct_option=1,
                    explanation="Explanation",
                    fast_method="Fast method",
                    difficulty=(index % 3) + 1,
                    expected_time_seconds=30,
                    pattern_type=f"{topic_slug}-pattern-{index % 2}",
                    verification_status="verified",
                )
                db.add(question)
                db.flush()
                for position in range(1, 5):
                    db.add(
                        QuestionOption(
                            question_id=question.id,
                            position=position,
                            text=f"Option {position}",
                        )
                    )

            db.add(
                Flashcard(
                    topic_id=topic.id,
                    front=f"{topic_name} recall",
                    back="Answer",
                    card_type="fact",
                    is_published=True,
                )
            )

        db.commit()

    return engine


def test_phase4d_production_canary_exercises_full_loop_and_rolls_back():
    engine = _seed_canary_database()

    report = run_production_learner_canary(engine)

    assert report["status"] == "passed"
    assert report["rollback_verified"] is True
    assert report["practice_attempts"] == 10
    assert report["practice_correct"] == 6
    assert report["practice_incorrect"] == 4
    assert report["revision_items_created"] >= 4
    assert report["bookmark_round_trip"] is True
    assert report["flashcard_reviewed"] is True
    assert report["mock_questions"] == 4
    assert report["mock_correct"] == 3
    assert report["mock_incorrect"] == 1
    assert report["analytics_accuracy"] == 60.0
    assert report["analytics_mock_accuracy"] == 75.0
    assert report["analytics_weak_topics"] >= 1
    assert report["analytics_next_actions"] >= 1
    assert report["planner_adapted_to_practice_topic"] is True

    Session = sessionmaker(bind=engine)
    with Session() as db:
        learner_models = [
            User,
            ExamTarget,
            DailyPlanTask,
            QuestionAttempt,
            TopicMastery,
            RevisionItem,
            MockAttempt,
            Bookmark,
            FlashcardProgress,
        ]
        for model in learner_models:
            assert db.scalar(select(func.count()).select_from(model)) == 0
