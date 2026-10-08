"""Read-only catalog of official exam blueprints and course availability."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import User, UserExamFocus

from app.services.exam_catalog import get_exam_blueprint, is_published_exam, list_exam_catalog

router = APIRouter(prefix="/exams", tags=["exams"])


@router.get("")
def list_exams() -> list[dict]:
    return list_exam_catalog()


@router.get("/{slug}")
def get_exam(slug: str) -> dict:
    blueprint = get_exam_blueprint(slug)
    if blueprint is None:
        raise HTTPException(status_code=404, detail="Exam not found")
    return blueprint


DEFAULT_EXAM_SLUG = "ssc-cgl-tier-1"


class ExamFocusUpdate(BaseModel):
    exam_slug: str


@router.get("/focus/current")
def current_exam_focus(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    focus = db.get(UserExamFocus, user.id)
    slug = focus.exam_slug if focus and is_published_exam(focus.exam_slug) else DEFAULT_EXAM_SLUG
    return {"exam_slug": slug, "exam": get_exam_blueprint(slug)}


@router.put("/focus/current")
def set_exam_focus(
    payload: ExamFocusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    exam = get_exam_blueprint(payload.exam_slug)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    if not is_published_exam(payload.exam_slug):
        raise HTTPException(status_code=409, detail="This exam stage is not published yet")

    focus = db.get(UserExamFocus, user.id)
    if focus is None:
        focus = UserExamFocus(user_id=user.id, exam_slug=payload.exam_slug)
        db.add(focus)
    else:
        focus.exam_slug = payload.exam_slug
    db.commit()
    return {"exam_slug": payload.exam_slug, "exam": exam}
