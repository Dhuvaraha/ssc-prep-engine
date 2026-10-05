import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.content.import_schema import ImportedQuestion
from app.db import SessionLocal
from app.models import Exam, Question, QuestionOption, Subject, Topic


def load_questions(path: Path) -> list[ImportedQuestion]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Import file must contain a JSON array")
    return [ImportedQuestion.model_validate(item) for item in raw]


def import_questions(path: Path) -> None:
    rows = load_questions(path)

    with SessionLocal() as db:
        inserted = 0
        for item in rows:
            exam = db.scalar(select(Exam).where(Exam.slug == item.exam_slug))
            if not exam:
                raise ValueError(f"Unknown exam: {item.exam_slug}")

            subject = db.scalar(
                select(Subject).where(
                    Subject.exam_id == exam.id,
                    Subject.slug == item.subject_slug,
                )
            )
            if not subject:
                raise ValueError(f"Unknown subject: {item.subject_slug}")

            topic = None
            if item.topic_slug:
                topic = db.scalar(
                    select(Topic).where(
                        Topic.subject_id == subject.id,
                        Topic.slug == item.topic_slug,
                    )
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
                visibility=item.visibility,
                verification_status=item.verification_status,
            )
            question.options = [
                QuestionOption(
                    position=option.position,
                    text=option.text,
                    image_url=option.image_url,
                )
                for option in item.options
            ]
            db.add(question)
            inserted += 1

        db.commit()
        print(f"Imported {inserted} questions")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.scripts.import_questions questions.json")
    import_questions(Path(sys.argv[1]))
