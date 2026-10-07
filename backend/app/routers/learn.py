from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Lesson, LessonBlock, QuestionArchetype, Subject, Topic
from app.schemas import LessonBlockOut, LessonOut, QuestionArchetypeOut

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



@router.get("/topics/{topic_id}/package")
def topic_package(topic_id: int, db: Session = Depends(get_db)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    subject = db.get(Subject, topic.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")

    lessons = list(
        db.scalars(
            select(Lesson)
            .where(Lesson.topic_id == topic_id, Lesson.is_published.is_(True))
            .order_by(Lesson.sort_order)
        )
    )
    lesson_ids = [lesson.id for lesson in lessons]

    blocks = []
    if lesson_ids:
        blocks = list(
            db.scalars(
                select(LessonBlock)
                .where(
                    LessonBlock.lesson_id.in_(lesson_ids),
                    LessonBlock.is_published.is_(True),
                )
                .order_by(LessonBlock.lesson_id, LessonBlock.sort_order)
            )
        )

    archetypes = list(
        db.scalars(
            select(QuestionArchetype)
            .where(
                QuestionArchetype.topic_id == topic_id,
                QuestionArchetype.is_published.is_(True),
            )
            .order_by(QuestionArchetype.id)
        )
    )

    blocks_by_lesson: dict[int, list[LessonBlockOut]] = {}
    for block in blocks:
        blocks_by_lesson.setdefault(block.lesson_id, []).append(LessonBlockOut.model_validate(block))

    return {
        "subject": {
            "id": subject.id,
            "slug": subject.slug,
            "name": subject.name,
        },
        "topic": {
            "id": topic.id,
            "slug": topic.slug,
            "name": topic.name,
            "priority": topic.priority,
        },
        "lessons": [
            {
                **LessonOut.model_validate(lesson).model_dump(),
                "blocks": [
                    item.model_dump()
                    for item in blocks_by_lesson.get(lesson.id, [])
                ],
            }
            for lesson in lessons
        ],
        "archetypes": [
            QuestionArchetypeOut.model_validate(item).model_dump()
            for item in archetypes
        ],
    }
