from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, Lesson, Question, QuestionOption, Subject, Topic
from app.routers.learn import topic_package


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    exam = Exam(
        slug="ssc-cgl-tier-1",
        name="SSC CGL Tier I",
        duration_minutes=60,
        positive_marks=2.0,
        negative_marks=0.5,
    )
    db.add(exam)
    db.flush()

    subject = Subject(
        exam_id=exam.id,
        slug="quant",
        name="Quantitative Aptitude",
        sort_order=1,
    )
    db.add(subject)
    db.flush()

    topic = Topic(
        subject_id=subject.id,
        slug="percentage",
        name="Percentage",
        priority=5,
    )
    db.add(topic)
    db.flush()

    db.add(
        Lesson(
            topic_id=topic.id,
            title="Percentage",
            intro="Learn the base first.",
            concept="A percentage is a ratio out of 100.",
            estimated_minutes=12,
            is_published=True,
        )
    )

    def question(
        text: str,
        *,
        difficulty: int,
        correct: int,
        explanation: str,
        source_type: str = "official",
        year: int | None = 2025,
        pattern: str | None = None,
    ):
        item = Question(
            exam_id=exam.id,
            subject_id=subject.id,
            topic_id=topic.id,
            question_text=text,
            correct_option=correct,
            explanation=explanation,
            fast_method="Use the shortest reliable percentage conversion.",
            difficulty=difficulty,
            expected_time_seconds=30 + difficulty * 5,
            year=year,
            source_type=source_type,
            pattern_type=pattern,
            verification_status="verified",
        )
        db.add(item)
        db.flush()
        for position, option_text in enumerate(("10", "20", "25", "40"), start=1):
            db.add(
                QuestionOption(
                    question_id=item.id,
                    position=position,
                    text=option_text,
                )
            )
        return item

    easy = question(
        "What is 25% of 80?",
        difficulty=1,
        correct=2,
        explanation="25% is one fourth, so 80 divided by 4 is 20.",
        pattern="percentage-direct",
    )
    medium = question(
        "A value rises from 80 to 100. Find the percentage increase.",
        difficulty=2,
        correct=3,
        explanation="Increase is 20. Divide by the original 80 and multiply by 100 to get 25%.",
        pattern="percentage-change",
    )
    hard = question(
        "A price rises by 25%. By what percent must consumption fall to keep expenditure unchanged?",
        difficulty=3,
        correct=2,
        explanation="New price factor is 1.25, so consumption factor is 0.8: a 20% fall.",
        pattern="constant-expenditure",
    )

    duplicate = question(
        "What is 25% of 80?",
        difficulty=1,
        correct=2,
        explanation="25% is one fourth, so 80 divided by 4 is 20.",
        source_type="original",
        year=None,
        pattern="percentage-direct",
    )

    db.commit()
    return db, topic, easy, medium, hard, duplicate


def test_topic_package_attaches_verified_easy_medium_hard_solved_examples():
    db, topic, easy, medium, hard, _ = _db()
    try:
        payload = topic_package(topic.id, db=db)
        examples = payload["solved_examples"]

        assert len(examples) == 3
        assert [item["difficulty"] for item in examples] == [1, 2, 3]
        assert [item["id"] for item in examples] == [easy.id, medium.id, hard.id]

        for item in examples:
            assert item["correct_option"] in {1, 2, 3, 4}
            assert item["explanation"]
            assert item["fast_method"]
            assert len(item["options"]) == 4
            assert [option["position"] for option in item["options"]] == [1, 2, 3, 4]
    finally:
        db.close()


def test_topic_package_deduplicates_repeated_teacher_example_content():
    db, topic, easy, _, _, duplicate = _db()
    try:
        payload = topic_package(topic.id, db=db)
        examples = payload["solved_examples"]

        matching = [item for item in examples if item["question_text"] == "What is 25% of 80?"]
        assert len(matching) == 1
        assert matching[0]["id"] == easy.id
        assert all(item["id"] != duplicate.id for item in examples)
    finally:
        db.close()
