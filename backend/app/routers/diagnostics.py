"""First diagnostic is an immutable sampled starting profile, not exam readiness."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.content_access import teaching_user as get_current_user
from app.models import MockAttempt, Subject, Topic, User
from app.services.exam_scope import current_exam

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def _profile(db: Session, attempt: MockAttempt) -> dict:
    from app.services.mock_engine import load_mock_attempt
    _,rows=load_mock_attempt(db,attempt_id=attempt.id,user_id=attempt.user_id)
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

    counts=[getattr(q,'delivery_blueprint',{}).get('curriculum_topic_count') for _,q in rows]
    curriculum_unknown=not counts or all(value is None for value in counts)
    if curriculum_unknown:
        total_topics = db.scalar(select(func.count(Topic.id)).join(Subject,Subject.id==Topic.subject_id)
            .where(Subject.exam_id==attempt.exam_id)) or 0
    elif all(type(value) is int and value>=0 for value in counts) and len(set(counts))==1:
        total_topics=counts[0]
    else:
        raise HTTPException(409,'INCONSISTENT_CURRICULUM_BLUEPRINT')
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

    original_unknown=any(getattr(q,'original_version_unknown',True) for _,q in rows)

    return {
        "attempt_id": attempt.id,
        "original_version_unknown": original_unknown,
        "original_curriculum_unknown": curriculum_unknown,
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "evidence_label": confidence,
        "readiness": None,
        "readiness_label": "Not assessed",
        "caution": (
            "A 40-question diagnostic samples only part of the syllabus. "
            "Unseen topics are unknown, not weak; easy-only correctness is not exam readiness."
            + (" Original question versions were not recorded; these details use current content. Saved scores are unchanged." if original_unknown else "")
            + (" The original syllabus count was not recorded; topic coverage uses the current curriculum." if curriculum_unknown else "")
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
    baseline=_profile(db,first)
    return {
        "status": "sampled",
        "readiness": None,
        "baseline": baseline,
        "latest": _profile(db, last) if last.id != first.id else baseline,
        "completed_diagnostics": len(submitted),
    }
