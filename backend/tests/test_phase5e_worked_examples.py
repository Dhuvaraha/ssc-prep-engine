from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Exam,
    Lesson,
    Question,
    QuestionOption,
    Subject,
    Topic,
)
from app.routers.learn import topic_package


def test_topic_package_returns_verified_easy_medium_hard_walkthroughs():
    engine = create_engine("sqlite:///:memory:")
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
        subject = Subject(exam_id=exam.id, slug="quant", name="Quant", sort_order=1)
        db.add(subject)
        db.flush()
        topic = Topic(subject_id=subject.id, slug="percentage", name="Percentage", priority=5)
        db.add(topic)
        db.flush()
        db.add(
            Lesson(
                topic_id=topic.id,
                title="Percentage",
                intro="Intro",
                concept="Concept",
                estimated_minutes=10,
                is_published=True,
            )
        )

        for index in range(30):
            question = Question(
                exam_id=exam.id,
                subject_id=subject.id,
                topic_id=topic.id,
                question_text=f"easy {index}",
                correct_option=1,
                explanation=f"easy explanation {index}",
                fast_method=f"easy fast {index}",
                difficulty=1,
                verification_status="verified",
            )
            db.add(question)
            db.flush()
            for pos in range(1, 5):
                db.add(QuestionOption(question_id=question.id, position=pos, text=f"E{index}-{pos}"))

        for difficulty, label in ((2, "medium"), (3, "hard")):
            question = Question(
                exam_id=exam.id,
                subject_id=subject.id,
                topic_id=topic.id,
                question_text=label,
                correct_option=2,
                explanation=f"{label} explanation",
                fast_method=f"{label} fast",
                difficulty=difficulty,
                verification_status="verified",
            )
            db.add(question)
            db.flush()
            for pos in range(1, 5):
                db.add(QuestionOption(question_id=question.id, position=pos, text=f"{label}-{pos}"))
        db.commit()

        payload = topic_package(topic.id, db=db)
        worked = payload["worked_questions"]

        assert len(worked) == 3
        assert [item["difficulty"] for item in worked] == [1, 2, 3]
        assert all(item["explanation"] for item in worked)
        assert all(len(item["options"]) == 4 for item in worked)
        assert worked[1]["correct_option"] == 2
        assert worked[1]["fast_method"] == "medium fast"


def test_unverified_or_missing_solution_questions_are_not_teacher_examples():
    engine = create_engine("sqlite:///:memory:")
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

        db.add_all(
            [
                Question(
                    exam_id=exam.id,
                    subject_id=subject.id,
                    topic_id=topic.id,
                    question_text="raw",
                    correct_option=1,
                    explanation="not approved",
                    difficulty=1,
                    verification_status="raw",
                ),
                Question(
                    exam_id=exam.id,
                    subject_id=subject.id,
                    topic_id=topic.id,
                    question_text="missing explanation",
                    correct_option=1,
                    explanation=None,
                    difficulty=1,
                    verification_status="verified",
                ),
            ]
        )
        db.commit()

        payload = topic_package(topic.id, db=db)
        assert payload["worked_questions"] == []
