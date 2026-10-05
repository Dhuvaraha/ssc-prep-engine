import hashlib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.import_schema import ImportedQuestion
from app.models import Exam, Question, QuestionOption, Subject, Topic


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def question_fingerprint(item: ImportedQuestion) -> str:
    option_text = "|".join(
        normalize_text(option.text or option.image_url or "")
        for option in sorted(item.options, key=lambda row: row.position)
    )
    payload = "::".join(
        [item.exam_slug, item.subject_slug, normalize_text(item.question_text), option_text]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_question(item: ImportedQuestion) -> None:
    positions = [option.position for option in item.options]
    if len(positions) < 2:
        raise ValueError("A question needs at least two options")
    if len(set(positions)) != len(positions):
        raise ValueError("Option positions must be unique")
    if item.correct_option not in positions:
        raise ValueError("correct_option must point to an existing option")


def import_question(db: Session, item: ImportedQuestion) -> tuple[Question, bool]:
    validate_question(item)
    fingerprint = question_fingerprint(item)

    existing = db.scalar(select(Question).where(Question.fingerprint == fingerprint))
    if existing:
        return existing, False

    exam = db.scalar(select(Exam).where(Exam.slug == item.exam_slug))
    if not exam:
        raise ValueError(f"Unknown exam: {item.exam_slug}")

    subject = db.scalar(
        select(Subject).where(Subject.exam_id == exam.id, Subject.slug == item.subject_slug)
    )
    if not subject:
        raise ValueError(f"Unknown subject: {item.subject_slug}")

    topic = None
    if item.topic_slug:
        topic = db.scalar(
            select(Topic).where(Topic.subject_id == subject.id, Topic.slug == item.topic_slug)
        )
        if not topic:
            raise ValueError(f"Unknown topic: {item.topic_slug}")

    question = Question(
        exam_id=exam.id,
        subject_id=subject.id,
        topic_id=topic.id if topic else None,
        question_text=item.question_text,
        question_image_url=item.question_image_url,
        correct_option=item.correct_option,
        explanation=item.explanation,
        fast_method=item.fast_method,
        difficulty=item.difficulty,
        expected_time_seconds=item.expected_time_seconds,
        year=item.year,
        shift=item.shift,
        source_type=item.source_type,
        source_reference=item.source_reference,
        source_page=item.source_page,
        requires_visual_review=item.requires_visual_review,
        visibility=item.visibility,
        verification_status=item.verification_status,
        fingerprint=fingerprint,
    )
    question.options = [
        QuestionOption(position=o.position, text=o.text, image_url=o.image_url)
        for o in item.options
    ]
    db.add(question)
    db.flush()
    return question, True
