"""Resolve the published exam stage owned by a learner.

Only ready, DB-backed courses can be used for actual learning queries.
The existing CGL Tier I course remains the read-only fallback for
accounts created before multi-exam selection existed.
"""
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Exam, UserExamFocus
from app.services.exam_catalog import is_published_exam

DEFAULT_EXAM = "ssc-cgl-tier-1"


def current_exam(db: Session, *, user_id: int) -> Exam:
    focus_slug = select(UserExamFocus.exam_slug).where(
        UserExamFocus.user_id == user_id,
    ).scalar_subquery()
    # One DB round-trip instead of loading focus then resolving the exam.
    exam = db.scalar(select(Exam).where(
        Exam.slug == func.coalesce(focus_slug, DEFAULT_EXAM),
    ))
    if exam is None:
        raise HTTPException(status_code=409, detail="Selected exam content is not available")
    if not is_published_exam(exam.slug):
        raise HTTPException(status_code=409, detail="Selected exam stage is not published")
    return exam
