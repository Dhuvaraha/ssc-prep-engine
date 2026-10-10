from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.services.content_access import teaching_user
from app.models import User
from app.models import Lesson, LessonBlock, Question, QuestionArchetype, Subject, Topic
from app.schemas import (
    LessonBlockOut,
    LessonOut,
    QuestionArchetypeOut,
    SolvedExampleOut,
)
from app.services.question_quality import unique_questions
from app.services.practice_integrity import expose

router = APIRouter(prefix="/learn", tags=["learn"])


def _representative_solved_examples(
    db: Session,
    *,
    topic_id: int,
    limit: int = 3,
) -> list[Question]:
    """
    Return a tiny verified teaching sample for the lesson page.

    The lesson package should never hydrate an entire topic bank. Fetch a
    bounded candidate window, prefer official/recent content, then keep one
    representative question per difficulty before filling any remaining slot.
    """
    source_rank = case(
        (Question.source_type == "official", 0),
        (Question.source_type == "licensed", 1),
        (Question.source_type == "user_private", 1),
        (Question.source_type == "original", 2),
        else_=3,
    )
    missing_year = case((Question.year.is_(None), 1), else_=0)

    candidate_ids: list[int] = []
    for difficulty in (1, 2, 3):
        candidate_ids.extend(
            db.scalars(
                select(Question.id)
                .where(
                    Question.topic_id == topic_id,
                    Question.verification_status == "verified",
                    Question.correct_option.is_not(None),
                    Question.explanation.is_not(None),
                    Question.difficulty == difficulty,
                )
                .order_by(
                    missing_year,
                    Question.year.desc(),
                    source_rank,
                    Question.id,
                )
                .limit(12)
            )
        )
    candidate_ids = list(dict.fromkeys(candidate_ids))
    if not candidate_ids:
        return []

    hydrated = list(
        db.scalars(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id.in_(candidate_ids))
        ).unique()
    )
    by_id = {question.id: question for question in hydrated}
    candidates = unique_questions(
        [by_id[question_id] for question_id in candidate_ids if question_id in by_id]
    )

    selected: list[Question] = []
    selected_ids: set[int] = set()
    for difficulty in (1, 2, 3):
        match = next(
            (
                question
                for question in candidates
                if question.difficulty == difficulty and question.id not in selected_ids
            ),
            None,
        )
        if match:
            selected.append(match)
            selected_ids.add(match.id)
        if len(selected) >= limit:
            return selected

    for question in candidates:
        if question.id in selected_ids:
            continue
        selected.append(question)
        selected_ids.add(question.id)
        if len(selected) >= limit:
            break

    return selected


@router.get("/topics/{topic_id}/lessons", response_model=list[LessonOut])
def topic_lessons(topic_id: int, db: Session = Depends(get_db), user: User = Depends(teaching_user)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Content not available")

    stmt = (
        select(Lesson)
        .where(Lesson.topic_id == topic_id, Lesson.is_published.is_(True))
        .order_by(Lesson.sort_order)
    )
    lessons = list(db.scalars(stmt))
    if not lessons:
        raise HTTPException(404, "Content not available")
    return lessons


@router.get("/lessons/{lesson_id}", response_model=LessonOut)
def get_lesson(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(teaching_user)):
    lesson = db.get(Lesson, lesson_id)
    if not lesson or not lesson.is_published:
        raise HTTPException(status_code=404, detail="Content not available")
    return lesson


@router.get("/topics/{topic_id}/package")
def topic_package(topic_id: int, db: Session = Depends(get_db), user: User = Depends(teaching_user)):
    topic = db.get(Topic, topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Content not available")

    subject = db.get(Subject, topic.subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Content not available")

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
    solved_examples = _representative_solved_examples(db, topic_id=topic_id)

    if db.info.get("content_scope"):
        for question in solved_examples:
            expose(db, user.id, question, "solved_example")
        db.commit()

    blocks_by_lesson: dict[int, list[LessonBlockOut]] = {}
    for block in blocks:
        blocks_by_lesson.setdefault(block.lesson_id, []).append(LessonBlockOut.model_validate(block))

    if not lessons and not archetypes and not solved_examples:
        raise HTTPException(404, "Content not available")
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
            QuestionArchetypeOut.model_validate(item).model_dump(exclude={"source_notes"})
            for item in archetypes
        ],
        "solved_examples": [
            SolvedExampleOut.model_validate(item).model_dump()
            for item in solved_examples
        ],
    }
