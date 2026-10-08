"""Resolve the published exam stage owned by a learner.

Only ready, DB-backed courses can be used for actual learning queries.
The existing CGL Tier I course remains the read-only fallback for
accounts created before multi-exam selection existed.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Exam, UserExamFocus
from app.services.exam_catalog import is_published_exam

DEFAULT_EXAM = "ssc-cgl-tier-1"


def current_exam(db: Session, *, user_id: int) -> Exam:
    focus = db.get(UserExamFocus, user_id)
    slug = focus.exam_slug if focus else DEFAULT_EXAM
    if not is_published_exam(slug):
        raise HTTPException(status_code=409, detail="Selected exam stage is not published")
    exam = db.scalar(select(Exam).where(Exam.slug == slug))
    if exam is None:
        raise HTTPException(status_code=409, detail="Selected exam content is not available")
    return exam
