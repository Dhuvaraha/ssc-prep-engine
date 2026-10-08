"""First diagnostic is an immutable sampled starting profile, not exam readiness."""
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import MockAttempt, MockAttemptQuestion, Question, Subject, Topic, User
from app.services.exam_scope import current_exam

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def _profile(db: Session, attempt: MockAttempt) -> dict:
    rows = list(db.execute(
        select(MockAttemptQuestion, Question)
        .join(Question, Question.id == MockAttemptQuestion.question_id)
        .where(MockAttemptQuestion.attempt_id == attempt.id)
        .order_by(MockAttemptQuestion.position)
    ))
    subjects: dict[str, dict] = {
        slug: {"correct": 0, "incorrect": 0, "unattempted": 0,
               "easy_attempted": 0, "medium_attempted": 0, "hard_attempted": 0}
        for slug in ("reasoning", "general-awareness", "quant", "english")
    }
    selected_topics = set()
    attempted_topics = set()
    for row, question in rows:
        subject = subjects[row.section_slug]
        if question.topic_id is not None:
            selected_topics.add(question.topic_id)
        if row.selected_option is None:
            subject["unattempted"] += 1
            continue
        if question.topic_id is not None:
            attempted_topics.add(question.topic_id)
        difficulty_key = {1: "easy_attempted", 2: "medium_attempted", 3: "hard_attempted"}.get(question.difficulty)
        if difficulty_key:
            subject[difficulty_key] += 1
        if row.selected_option == question.correct_option:
            subject["correct"] += 1
        else:
            subject["incorrect"] += 1

    total_topics = db.scalar(
        select(func.count(Topic.id))
        .join(Subject, Subject.id == Topic.subject_id)
        .where(Subject.exam_id == attempt.exam_id)
    ) or 0
    attempted = sum(s["correct"] + s["incorrect"] for s in subjects.values())
    correct = sum(s["correct"] for s in subjects.values())
    confidence = (
        "limited_sample"
        if attempted < 30 or any(
            s["correct"] + s["incorrect"] < 5 for s in subjects.values()
        ) else "initial_sample"
    )
    for row in subjects.values():
        answered = row["correct"] + row["incorrect"]
        row["accuracy"] = round(100 * row["correct"] / answered, 1) if answered else None
        row["attempted"] = answered

    return {
        "attempt_id": attempt.id,
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "evidence_label": confidence,
        "readiness": None,
        "readiness_label": "Not assessed",
        "caution": (
            "A 40-question diagnostic samples only part of the syllabus. "
            "Unseen topics are unknown, not weak; easy-only correctness is not exam readiness."
        ),
        "sampled_questions": len(rows),
        "attempted_questions": attempted,
        "correct": correct,
        "accuracy": round(100 * correct / attempted, 1) if attempted else None,
        "sampled_topics": len(selected_topics),
        "attempted_topics": len(attempted_topics),
        "total_topics": total_topics,
        "subjects": subjects,
    }


@router.get("/baseline")
def diagnostic_baseline(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    exam = current_exam(db, user_id=user.id)
    submitted = list(db.scalars(
        select(MockAttempt).where(
            MockAttempt.user_id == user.id,
            MockAttempt.exam_id == exam.id,
            MockAttempt.mode == "diagnostic",
            MockAttempt.status == "submitted",
        ).order_by(MockAttempt.submitted_at, MockAttempt.id)
    ))
    if not submitted:
        return {
            "status": "not_assessed",
            "readiness": None,
            "baseline": None,
            "latest": None,
            "completed_diagnostics": 0,
        }
    first = submitted[0]
    last = submitted[-1]
    return {
        "status": "sampled",
        "readiness": None,
        "baseline": _profile(db, first),
        "latest": _profile(db, last) if last.id != first.id else _profile(db, first),
        "completed_diagnostics": len(submitted),
    }
