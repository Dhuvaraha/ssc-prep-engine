from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Exam, Subject, Topic
from app.schemas import SubjectOut, TopicOut

router = APIRouter(prefix="/content", tags=["content"])


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(exam_id: int, db: Session = Depends(get_db)):
    stmt = select(Subject).where(Subject.exam_id == exam_id).order_by(Subject.sort_order)
    return list(db.scalars(stmt))


@router.get("/topics", response_model=list[TopicOut])
def list_topics(subject_id: int, db: Session = Depends(get_db)):
    stmt = select(Topic).where(Topic.subject_id == subject_id).order_by(Topic.priority.desc(), Topic.name)
    return list(db.scalars(stmt))


@router.get("/tree")
def content_tree(exam_slug: str = "ssc-cgl-tier-1", db: Session = Depends(get_db)):
    exam = db.scalar(select(Exam).where(Exam.slug == exam_slug))
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    subjects = list(
        db.scalars(
            select(Subject)
            .where(Subject.exam_id == exam.id)
            .order_by(Subject.sort_order)
        )
    )

    result = []
    for subject in subjects:
        topics = list(
            db.scalars(
                select(Topic)
                .where(Topic.subject_id == subject.id)
                .order_by(Topic.priority.desc(), Topic.name)
            )
        )
        result.append(
            {
                "id": subject.id,
                "slug": subject.slug,
                "name": subject.name,
                "topics": [
                    {
                        "id": topic.id,
                        "slug": topic.slug,
                        "name": topic.name,
                        "priority": topic.priority,
                    }
                    for topic in topics
                ],
            }
        )

    return {
        "exam": {"id": exam.id, "slug": exam.slug, "name": exam.name},
        "subjects": result,
    }
