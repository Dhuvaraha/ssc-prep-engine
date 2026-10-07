import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.content.import_schema import ImportedQuestion
from app.db import Base
from app.models import Exam, Subject, Topic
from app.services.question_import import import_question, question_fingerprint, validate_question


def _verified_question(**overrides):
    payload = {
        "exam_slug": "ssc-cgl-tier-1",
        "subject_slug": "reasoning",
        "topic_slug": "analogy",
        "question_text": "Choose the matching figure.",
        "pattern_type": "figure-analogy",
        "options": [
            {"position": 1, "text": "Figure", "image_url": "private://a.svg"},
            {"position": 2, "text": "Figure", "image_url": "private://b.svg"},
            {"position": 3, "text": "Figure", "image_url": "private://c.svg"},
            {"position": 4, "text": "Figure", "image_url": "private://d.svg"},
        ],
        "correct_option": 2,
        "verification_status": "verified",
    }
    payload.update(overrides)
    return ImportedQuestion.model_validate(payload)


def test_verified_import_accepts_same_labels_when_images_differ():
    validate_question(_verified_question())


def test_verified_import_rejects_duplicate_option_payloads():
    item = _verified_question(
        options=[
            {"position": 1, "text": "10"},
            {"position": 2, "text": "10"},
            {"position": 3, "text": "12"},
            {"position": 4, "text": "14"},
        ]
    )
    with pytest.raises(ValueError, match="payloads must be unique"):
        validate_question(item)


def test_verified_import_rejects_missing_pattern_and_non_four_option_sets():
    with pytest.raises(ValueError, match="pattern_type"):
        validate_question(_verified_question(pattern_type=None))

    with pytest.raises(ValueError, match="exactly four"):
        validate_question(
            _verified_question(
                options=[
                    {"position": 1, "text": "A"},
                    {"position": 2, "text": "B"},
                    {"position": 3, "text": "C"},
                ],
                correct_option=1,
            )
        )


def test_visual_fingerprint_includes_image_identity():
    first = _verified_question()
    second = _verified_question(
        options=[
            {"position": 1, "text": "Figure", "image_url": "private://a2.svg"},
            {"position": 2, "text": "Figure", "image_url": "private://b.svg"},
            {"position": 3, "text": "Figure", "image_url": "private://c.svg"},
            {"position": 4, "text": "Figure", "image_url": "private://d.svg"},
        ]
    )
    assert question_fingerprint(first) != question_fingerprint(second)


def test_import_persists_subtopic_and_pattern_type():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
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
        db.commit()

        item = _verified_question(subtopic="Figure analogy")
        question, inserted = import_question(db, item)

        assert inserted is True
        assert question.subtopic == "Figure analogy"
        assert question.pattern_type == "figure-analogy"
        assert len(question.options) == 4
    finally:
        db.close()


def test_visual_fingerprint_includes_prompt_image_identity():
    first = _verified_question(question_image_url="private://prompt-a.svg")
    second = _verified_question(question_image_url="private://prompt-b.svg")
    assert question_fingerprint(first) != question_fingerprint(second)
