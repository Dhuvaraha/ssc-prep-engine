"""Pre-publication audit flags thin difficulty and weak option metadata."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import Exam, Lesson, Question, QuestionOption, Subject, Topic
from app.services.learning_quality_audit import collect_learning_quality


def _fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    exam = Exam(slug="ssc-cgl-tier-1", name="CGL", duration_minutes=60)
    subject = Subject(slug="general-awareness", name="General Awareness", exam_id=1)
    db.add(exam)
    db.flush()
    subject.exam_id = exam.id
    db.add(subject)
    db.flush()
    topic = Topic(subject_id=subject.id, slug="current-affairs", name="Current Affairs")
    db.add(topic)
    db.flush()
    db.add(Lesson(topic_id=topic.id, title="Intro", concept="Foundational concepts",
                  is_published=True))
    db.commit()
    return db, exam, topic


def _add(db, exam, topic, difficulty, i, *, solution="Short.", invalid=False):
    question = Question(
        exam_id=exam.id, subject_id=topic.subject_id, topic_id=topic.id,
        question_text=f"Question difficulty={difficulty} index={i}",
        difficulty=difficulty, correct_option=1,
        explanation=solution, source_type="official", source_reference="ssc-source",
        verification_status="verified",
    )
    db.add(question)
    db.flush()
    for position in range(1, 5):
        text = "duplicate" if invalid and position == 2 else f"choice {position}"
        if invalid and position == 1:
            text = "duplicate"
        db.add(QuestionOption(question_id=question.id, position=position, text=text))
    db.commit()


def test_audit_flags_missing_advanced_questions_and_insufficient_solutions():
    db, exam, topic = _fixture()
    try:
        for level, count in ((1, 5), (2, 5), (3, 1)):
            for i in range(count):
                _add(db, exam, topic, level, i, invalid=level == 3)
        report = collect_learning_quality(db, exam_slug=exam.slug)
        assert report["topics_audited"] == 1
        assert report["verified_questions_audited"] == 11
        assert report["topics_missing_level_floor"] == 1
        assert report["brief_solution_review_count"] == 11
        assert report["answer_options_review_count"] == 1
        assert report["human_fact_check_required"] is True
        topic_report = report["topic_reports"][0]
        assert topic_report["level_shortage"][3] == 4
        assert topic_report["content_status"] == "insufficient_level_questions"
    finally:
        db.close()


def test_audit_marks_complete_metadata_only_as_automated_check_pass():
    db, exam, topic = _fixture()
    try:
        for difficulty in (1, 2, 3):
            for i in range(5):
                _add(
                    db, exam, topic, difficulty, i,
                    solution="The correct choice follows from the verified syllabus rule because the other options do not satisfy it.",
                )
        report = collect_learning_quality(db, exam_slug=exam.slug)
        row = report["topic_reports"][0]
        assert row["difficulty_counts"] == {"easy": 5, "medium": 5, "hard": 5}
        assert row["level_shortage"] == {}
        assert row["invalid_options_review"] == 0
        assert row["content_status"] == "automated_checks_passed"
        assert report["human_fact_check_required"] is True
    finally:
        db.close()
