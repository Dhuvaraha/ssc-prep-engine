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
        normalize_text(option.text or "")
        + "\u0000"
        + (option.image_url or "").strip()
        for option in sorted(item.options, key=lambda row: row.position)
    )
    payload = "::".join(
        [
            item.exam_slug,
            item.subject_slug,
            normalize_text(item.question_text),
            (item.question_image_url or "").strip(),
            option_text,
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def validate_question(item: ImportedQuestion) -> None:
    positions = [option.position for option in item.options]
    if len(positions) < 2:
        raise ValueError("A question needs at least two options")
    if len(set(positions)) != len(positions):
        raise ValueError("Option positions must be unique")
    if item.correct_option is not None and item.correct_option not in positions:
        raise ValueError("correct_option must point to an existing option")

    if item.verification_status != "verified":
        return

    if positions != [1, 2, 3, 4]:
        raise ValueError("Verified SSC questions require exactly four ordered options")
    if item.correct_option is None:
        raise ValueError("Verified questions require a correct option")
    if not item.pattern_type or not item.pattern_type.strip():
        raise ValueError("Verified questions require a pattern_type")

    identities: list[tuple[str, str]] = []
    for option in item.options:
        text_key = normalize_text(option.text or "")
        image_key = (option.image_url or "").strip()
        if not text_key and not image_key:
            raise ValueError("Verified options require text or an image")
        identities.append((text_key, image_key))

    if len(identities) != len(set(identities)):
        raise ValueError("Verified option payloads must be unique")


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
        subtopic=item.subtopic,
        pattern_type=item.pattern_type,
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
        source_chosen_option=item.source_chosen_option,
        source_question_id=item.source_question_id,
        source_status=item.source_status,
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
