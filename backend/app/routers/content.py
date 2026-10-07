from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Exam, Lesson, Question, Subject, Topic
from app.schemas import SubjectOut, TopicOut
from app.services.question_quality import unique_questions

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

    topic_ids = [
        topic.id
        for subject in subjects
        for topic in db.scalars(
            select(Topic)
            .where(Topic.subject_id == subject.id)
            .order_by(Topic.priority.desc(), Topic.name)
        )
    ]
    lessons = list(
        db.scalars(
            select(Lesson).where(
                Lesson.topic_id.in_(topic_ids),
                Lesson.is_published.is_(True),
            )
        )
    ) if topic_ids else []
    questions = list(
        db.scalars(
            select(Question)
            .options(selectinload(Question.options))
            .where(
                Question.topic_id.in_(topic_ids),
                Question.verification_status == "verified",
                Question.correct_option.is_not(None),
            )
        ).unique()
    ) if topic_ids else []

    lessons_by_topic: dict[int, int] = {}
    for lesson in lessons:
        lessons_by_topic[lesson.topic_id] = lessons_by_topic.get(lesson.topic_id, 0) + 1

    questions_by_topic: dict[int, list[Question]] = {}
    for question in questions:
        if question.topic_id is not None:
            questions_by_topic.setdefault(question.topic_id, []).append(question)

    result = []
    for subject in subjects:
        topics = list(
            db.scalars(
                select(Topic)
                .where(Topic.subject_id == subject.id)
                .order_by(Topic.priority.desc(), Topic.name)
            )
        )

        topic_rows = []
        for topic in topics:
            unique_count = len(unique_questions(questions_by_topic.get(topic.id, [])))
            topic_rows.append(
                {
                    "id": topic.id,
                    "slug": topic.slug,
                    "name": topic.name,
                    "priority": topic.priority,
                    "lesson_count": lessons_by_topic.get(topic.id, 0),
                    "question_count": unique_count,
                }
            )

        result.append(
            {
                "id": subject.id,
                "slug": subject.slug,
                "name": subject.name,
                "lesson_count": sum(item["lesson_count"] for item in topic_rows),
                "question_count": sum(item["question_count"] for item in topic_rows),
                "topics": topic_rows,
            }
        )

    return {
        "exam": {"id": exam.id, "slug": exam.slug, "name": exam.name},
        "totals": {
            "lessons": sum(item["lesson_count"] for item in result),
            "questions": sum(item["question_count"] for item in result),
        },
        "subjects": result,
    }
