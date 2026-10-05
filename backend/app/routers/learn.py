from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Lesson, Topic
from app.schemas import LessonOut

router = APIRouter(prefix="/learn", tags=["learn"])


@router.get("/topics/{topic_id}/lessons", response_model=list[LessonOut])
def topic_lessons(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    stmt = (
        select(Lesson)
        .where(Lesson.topic_id == topic_id, Lesson.is_published.is_(True))
        .order_by(Lesson.sort_order)
    )
    return list(db.scalars(stmt))


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: int, db: Session = Depends(get_db)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson.is_published:
        raise HTTPException(status_code=404, detail="Lesson not found")
    return lesson
