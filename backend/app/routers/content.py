from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Subject, Topic
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
