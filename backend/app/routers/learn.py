from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Lesson, LessonBlock, Question, QuestionArchetype, Subject, Topic
from app.schemas import LessonBlockOut, LessonOut, QuestionArchetypeOut, WorkedQuestionOut
from app.services.question_quality import unique_questions

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

    candidate_ids = list(
        db.scalars(
            select(Question.id)
            .where(
                Question.topic_id == topic_id,
                Question.verification_status == "verified",
                Question.correct_option.is_not(None),
                Question.explanation.is_not(None),
            )
            .order_by(
                Question.difficulty,
                Question.year.desc().nullslast(),
                Question.id,
            )
            .limit(60)
        )
    )
    candidate_questions = []
    if candidate_ids:
        loaded = list(
            db.scalars(
                select(Question)
                .options(selectinload(Question.options))
                .where(Question.id.in_(candidate_ids))
            ).unique()
        )
        by_id = {question.id: question for question in loaded}
        candidate_questions = unique_questions(
            [by_id[qid] for qid in candidate_ids if qid in by_id]
        )

    worked_questions = []
    used_ids: set[int] = set()
    for difficulty in (1, 2, 3):
        match = next(
            (
                question
                for question in candidate_questions
                if question.difficulty == difficulty and question.id not in used_ids
            ),
            None,
        )
        if match:
            worked_questions.append(match)
            used_ids.add(match.id)

    for question in candidate_questions:
        if len(worked_questions) >= 3:
            break
        if question.id not in used_ids:
            worked_questions.append(question)
            used_ids.add(question.id)

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
        "worked_questions": [
            WorkedQuestionOut.model_validate(question).model_dump()
            for question in worked_questions
        ],
    }
