from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Exam, Question, Subject
from app.services.mock_engine import SECTION_ORDER, _difficulty_targets
from app.services.question_quality import unique_questions


HIGH_FIDELITY_SOURCES = {"official", "licensed", "user_private"}


def collect_mock_readiness(db: Session, *, exam_slug: str = "ssc-cgl-tier-1") -> dict:
    exam = db.scalar(select(Exam).where(Exam.slug == exam_slug))
    if not exam:
        raise ValueError("Exam not found")

    targets = _difficulty_targets(25)
    sections = []
    for slug in SECTION_ORDER:
        subject = db.scalar(
            select(Subject).where(
                Subject.exam_id == exam.id,
                Subject.slug == slug,
            )
        )
        if not subject:
            sections.append(
                {
                    "subject": slug,
                    "ready": False,
                    "failures": ["missing_subject"],
                    "verified_unique": 0,
                    "high_fidelity": 0,
                    "difficulty": {"1": 0, "2": 0, "3": 0},
                }
            )
            continue

        questions = list(
            db.scalars(
                select(Question)
                .options(selectinload(Question.options))
                .where(
                    Question.exam_id == exam.id,
                    Question.subject_id == subject.id,
                    Question.verification_status == "verified",
                    Question.correct_option.is_not(None),
                )
                .order_by(Question.id)
            ).unique()
        )
        unique = unique_questions(questions)
        difficulty = {
            level: sum(max(1, min(3, question.difficulty)) == level for question in unique)
            for level in (1, 2, 3)
        }
        high_fidelity = sum(
            question.source_type in HIGH_FIDELITY_SOURCES or question.year is not None
            for question in unique
        )

        failures: list[str] = []
        if len(unique) < 25:
            failures.append("unique_verified<25")
        for level, required in targets.items():
            if difficulty[level] < required:
                failures.append(f"difficulty_{level}<{required}")
        if high_fidelity < 25:
            failures.append("high_fidelity<25")

        sections.append(
            {
                "subject": slug,
                "ready": not failures,
                "failures": failures,
                "verified_unique": len(unique),
                "high_fidelity": high_fidelity,
                "difficulty": {str(level): difficulty[level] for level in (1, 2, 3)},
            }
        )

    pending = [section for section in sections if not section["ready"]]
    return {
        "exam_slug": exam_slug,
        "status": "ready" if not pending else "attention",
        "difficulty_target": {str(k): v for k, v in targets.items()},
        "sections": sections,
        "pending_sections": len(pending),
    }
