"""Read-only catalog of official exam blueprints and course availability."""

from fastapi import APIRouter, HTTPException

from app.services.exam_catalog import get_exam_blueprint, list_exam_catalog

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
