from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, Question, QuestionOption, Subject, Topic
from app.services.content_audit import collect_content_audit


def test_content_audit_detects_integrity_and_quality_gaps():
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

    topic = Topic(
        subject_id=subject.id,
        slug="analogy",
        name="Analogy",
        priority=5,
    )
    db.add(topic)
    db.flush()

    valid = Question(
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=topic.id,
        question_text="Valid audit question",
        correct_option=1,
        explanation="Valid explanation",
        fast_method="Valid shortcut",
        expected_time_seconds=30,
        pattern_type="valid-pattern",
        difficulty=1,
        source_type="original",
        verification_status="verified",
    )
    invalid = Question(
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=topic.id,
        question_text="Invalid audit question",
        correct_option=5,
        explanation=None,
        fast_method=None,
        expected_time_seconds=None,
        pattern_type=None,
        difficulty=2,
        source_type="generated",
        verification_status="verified",
    )
    duplicate = Question(
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=topic.id,
        question_text="Duplicate option audit question",
        correct_option=2,
        explanation="Explanation",
        fast_method="Shortcut",
        expected_time_seconds=45,
        pattern_type="duplicate-pattern",
        difficulty=3,
        source_type="original",
        verification_status="verified",
    )
    visual = Question(
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=topic.id,
        question_text="Visual options can share labels",
        correct_option=1,
        explanation="Explanation",
        fast_method="Shortcut",
        expected_time_seconds=40,
        pattern_type="visual-pattern",
        difficulty=1,
        source_type="original",
        verification_status="verified",
    )
    db.add_all([valid, invalid, duplicate, visual])
    db.flush()

    for question, values in [
        (valid, ["A", "B", "C", "D"]),
        (invalid, ["A", "B", "C"]),
        (duplicate, ["Same", "Same", "C", "D"]),
    ]:
        for position, value in enumerate(values, start=1):
            db.add(
                QuestionOption(
                    question_id=question.id,
                    position=position,
                    text=value,
                )
            )


    for position, image_url in enumerate(
        ["private://a.svg", "private://b.svg", "private://c.svg", "private://d.svg"],
        start=1,
    ):
        db.add(
            QuestionOption(
                question_id=visual.id,
                position=position,
                text="Figure",
                image_url=image_url,
            )
        )

    db.commit()

    report = collect_content_audit(db, current_year=2026)

    assert report["verified_questions"] == 4
    assert report["topics"] == 1
    assert report["question_integrity"] == {
        "invalid_option_sets": 1,
        "invalid_correct_options": 1,
        "duplicate_option_sets": 1,
        "empty_option_content_sets": 0,
        "missing_explanations": 1,
        "missing_fast_methods": 1,
        "missing_expected_time": 1,
        "missing_pattern_type": 1,
    }
    assert report["critical_issues"] == 3
    assert report["diagnostics"]["duplicate_option_sets_by_topic"] == {
        "reasoning/analogy": 1,
    }
    assert report["diagnostics"]["duplicate_option_sets_by_source"] == {
        "original": 1,
    }
    assert report["diagnostics"]["duplicate_shape"] == {"3-unique": 1}
    assert report["diagnostics"]["duplicate_correct_answer_payload"] == 1
    assert report["diagnostics"]["duplicate_distractor_only"] == 0
    assert report["diagnostics"]["duplicate_with_image"] == 0
    assert report["diagnostics"]["duplicate_text_only"] == 1
    assert report["diagnostics"]["missing_pattern_type_by_topic"] == {
        "reasoning/analogy": 1,
    }
    assert report["diagnostics"]["missing_pattern_with_subtopic"] == 0
    assert report["diagnostics"]["missing_pattern_without_subtopic"] == 1
    assert report["difficulty"] == {"1": 2, "2": 1, "3": 1}
    assert report["source_types"] == {"generated": 1, "original": 3}
    assert report["pending_topic_count"] == 1
    assert report["subjects"][0]["slug"] == "reasoning"
    assert report["subjects"][0]["verified_questions"] == 4
    assert report["status"] == "attention"

    db.close()
