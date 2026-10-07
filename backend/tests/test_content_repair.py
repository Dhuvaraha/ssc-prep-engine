from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, Question, QuestionOption, Subject, Topic
from app.services.content_audit import collect_content_audit
from app.services.content_repair import repair_content_integrity


def _add_question(db, *, exam_id, subject_id, topic_id, text, options, correct_option):
    question = Question(
        exam_id=exam_id,
        subject_id=subject_id,
        topic_id=topic_id,
        question_text=text,
        correct_option=correct_option,
        explanation="Verified explanation",
        fast_method="Verified shortcut",
        expected_time_seconds=30,
        difficulty=2,
        source_type="original",
        verification_status="verified",
    )
    db.add(question)
    db.flush()
    for position, value in enumerate(options, start=1):
        db.add(
            QuestionOption(
                question_id=question.id,
                position=position,
                text=value,
            )
        )
    return question


def _repair_db():
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
        slug="reasoning",
        name="Reasoning",
        sort_order=1,
    )
    db.add(subject)
    db.flush()

    number_topic = Topic(
        subject_id=subject.id,
        slug="number-system",
        name="Number System",
        priority=5,
    )
    spelling_topic = Topic(
        subject_id=subject.id,
        slug="spelling",
        name="Spelling",
        priority=5,
    )
    text_topic = Topic(
        subject_id=subject.id,
        slug="classification-and-odd-one-out",
        name="Classification",
        priority=5,
    )
    db.add_all([number_topic, spelling_topic, text_topic])
    db.flush()

    q1 = _add_question(
        db,
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=number_topic.id,
        text="Numeric duplicate distractor",
        options=["10", "20", "20", "30"],
        correct_option=1,
    )
    q2 = _add_question(
        db,
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=number_topic.id,
        text="Correct answer payload duplicated",
        options=["5", "5", "7", "8"],
        correct_option=1,
    )
    q3 = _add_question(
        db,
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=spelling_topic.id,
        text="Word duplicate",
        options=["milennium", "millennium", "millennium", "millenium"],
        correct_option=2,
    )
    q4 = _add_question(
        db,
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=text_topic.id,
        text="General text duplicate distractor",
        options=["Red", "Blue", "Blue", "Green"],
        correct_option=1,
    )
    db.commit()
    return db, (q1.id, q2.id, q3.id, q4.id)


def test_repair_plan_is_safe_dry_run_and_apply_is_idempotent():
    db, question_ids = _repair_db()
    try:
        before = collect_content_audit(db)
        assert before["question_integrity"]["duplicate_option_sets"] == 4
        assert before["question_integrity"]["missing_pattern_type"] == 4

        plan = repair_content_integrity(db, apply=False)
        assert plan == {
            "exam_slug": "ssc-cgl-tier-1",
            "duplicate_questions": 4,
            "replacement_count": 4,
            "correct_payload_duplicates": 2,
            "unsupported_image_duplicates": 0,
            "missing_pattern_count": 4,
            "strategies": {
                "numeric": 2,
                "word-mutation": 1,
                "none-of-these": 1,
            },
        }

        # Dry run must not change production-like content.
        still_before = collect_content_audit(db)
        assert still_before["question_integrity"]["duplicate_option_sets"] == 4

        q2 = db.get(Question, question_ids[1])
        q3 = db.get(Question, question_ids[2])
        q2_correct_before = next(
            option.text for option in q2.options if option.position == q2.correct_option
        )
        q3_correct_before = next(
            option.text for option in q3.options if option.position == q3.correct_option
        )

        applied = repair_content_integrity(db, apply=True)
        assert applied == plan

        after = collect_content_audit(db)
        assert after["question_integrity"]["duplicate_option_sets"] == 0
        assert after["question_integrity"]["missing_pattern_type"] == 0

        db.expire_all()
        q2 = db.get(Question, question_ids[1])
        q3 = db.get(Question, question_ids[2])
        assert next(
            option.text for option in q2.options if option.position == q2.correct_option
        ) == q2_correct_before
        assert next(
            option.text for option in q3.options if option.position == q3.correct_option
        ) == q3_correct_before

        assert repair_content_integrity(db, apply=True)["replacement_count"] == 0
        assert repair_content_integrity(db, apply=True)["missing_pattern_count"] == 0
    finally:
        db.close()
