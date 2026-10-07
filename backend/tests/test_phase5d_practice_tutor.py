from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Exam,
    Lesson,
    LessonBlock,
    Question,
    QuestionArchetype,
    Subject,
    Topic,
    User,
)
from app.routers.practice import submit_practice
from app.schemas import PracticeSubmit
from app.services.practice_coach import build_question_coaching


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    user = User(email="coach@example.com", password_hash="x")
    exam = Exam(
        slug="ssc-cgl-tier-1",
        name="SSC CGL Tier I",
        duration_minutes=60,
        positive_marks=2.0,
        negative_marks=0.5,
    )
    db.add_all([user, exam])
    db.flush()

    subject = Subject(exam_id=exam.id, slug="quant", name="Quantitative Aptitude", sort_order=1)
    db.add(subject)
    db.flush()
    topic = Topic(subject_id=subject.id, slug="percentage", name="Percentage", priority=5)
    db.add(topic)
    db.flush()

    lesson = Lesson(
        topic_id=topic.id,
        title="Percentage",
        intro="Intro",
        concept="A percentage is a ratio out of 100.",
        shortcut="Convert common percentages to fractions.",
        common_traps="Use the original value as the base for percentage change.",
        estimated_minutes=12,
        is_published=True,
    )
    db.add(lesson)
    db.flush()
    db.add_all(
        [
            LessonBlock(
                lesson_id=lesson.id,
                block_type="recognition",
                title="Recognise",
                body="Look for 'of', 'increase', 'decrease' and identify the base.",
                sort_order=1,
                is_published=True,
            ),
            LessonBlock(
                lesson_id=lesson.id,
                block_type="method",
                title="Method",
                body="Identify the base, convert the percentage and write one clean equation.",
                sort_order=2,
                is_published=True,
            ),
            LessonBlock(
                lesson_id=lesson.id,
                block_type="shortcut",
                title="Shortcut",
                body="25% = 1/4 and 12.5% = 1/8.",
                sort_order=3,
                is_published=True,
            ),
            LessonBlock(
                lesson_id=lesson.id,
                block_type="example_exam",
                title="Example",
                body="25% of 360 = 90 because 360 / 4 = 90.",
                sort_order=4,
                is_published=True,
            ),
            LessonBlock(
                lesson_id=lesson.id,
                block_type="trap",
                title="Trap",
                body="Do not use the new value as the base for ordinary percentage change.",
                sort_order=5,
                is_published=True,
            ),
        ]
    )

    exact = QuestionArchetype(
        topic_id=topic.id,
        slug="percentage-direct",
        name="Direct percentage",
        skill="Find a percentage of a quantity.",
        recognition_cues="The wording uses x% of N.",
        canonical_method="Convert x% to x/100, then multiply by N.",
        shortcut_method="Use a known fraction equivalent when possible.",
        common_trap="Do not divide by the percentage itself.",
        easy_rule="Use direct fraction conversion.",
        medium_rule="Choose the correct base before multiplying.",
        hard_rule="Reduce the fraction before large multiplication.",
        expected_time_seconds=25,
        is_published=True,
    )
    db.add(exact)
    db.flush()

    exact_question = Question(
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=topic.id,
        pattern_type="percentage-direct",
        question_text="What is 25% of 360?",
        correct_option=1,
        explanation="25% = 1/4, so 360 / 4 = 90.",
        fast_method="Quarter 360 directly.",
        difficulty=1,
        expected_time_seconds=25,
        verification_status="verified",
    )
    fallback_question = Question(
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=topic.id,
        pattern_type="generated-percentage-variant",
        question_text="A value rises from 80 to 100. Find the percentage increase.",
        correct_option=2,
        explanation="Increase = 20. Divide by original 80: 20/80 × 100 = 25%.",
        fast_method=None,
        difficulty=2,
        expected_time_seconds=40,
        verification_status="verified",
    )
    db.add_all([exact_question, fallback_question])
    db.commit()
    return db, user, exact_question, fallback_question


def test_exact_archetype_coaching_uses_matching_verified_pattern():
    db, _, exact_question, _ = _db()
    try:
        coaching = build_question_coaching(db, exact_question)

        assert coaching is not None
        assert coaching["archetype_exact"] is True
        assert coaching["pattern_name"] == "Direct percentage"
        assert coaching["recognition_cues"] == "The wording uses x% of N."
        assert coaching["standard_method"] == "Convert x% to x/100, then multiply by N."
        assert coaching["fast_method"] == "Quarter 360 directly."
        assert coaching["common_trap"] == "Do not divide by the percentage itself."
        assert coaching["difficulty_rule"] == "Use direct fraction conversion."
        assert len(coaching["hint_steps"]) == 3
    finally:
        db.close()


def test_unmatched_pattern_falls_back_to_topic_lesson_not_arbitrary_archetype():
    db, _, _, fallback_question = _db()
    try:
        coaching = build_question_coaching(db, fallback_question)

        assert coaching is not None
        assert coaching["archetype_exact"] is False
        assert coaching["pattern_name"] == "Generated Percentage Variant"
        assert coaching["recognition_cues"] == "Look for 'of', 'increase', 'decrease' and identify the base."
        assert coaching["standard_method"] == "Identify the base, convert the percentage and write one clean equation."
        assert coaching["fast_method"] == "25% = 1/4 and 12.5% = 1/8."
        assert coaching["common_trap"] == "Do not use the new value as the base for ordinary percentage change."
        assert coaching["worked_example"] == "25% of 360 = 90 because 360 / 4 = 90."
        assert coaching["difficulty_rule"] is None
        assert "Convert x% to x/100" not in coaching["standard_method"]
    finally:
        db.close()


def test_submit_practice_returns_structured_teacher_review():
    db, user, exact_question, _ = _db()
    try:
        result = submit_practice(
            PracticeSubmit(
                question_id=exact_question.id,
                selected_option=1,
                time_seconds=18,
                confidence=3,
                used_hint=False,
            ),
            db=db,
            user=user,
        )

        assert result.correct is True
        assert result.explanation == "25% = 1/4, so 360 / 4 = 90."
        assert result.coaching is not None
        assert result.coaching.pattern_name == "Direct percentage"
        assert result.coaching.archetype_exact is True
        assert result.coaching.standard_method == "Convert x% to x/100, then multiply by N."
        assert result.coaching.hint_steps[0] == "The wording uses x% of N."
    finally:
        db.close()
