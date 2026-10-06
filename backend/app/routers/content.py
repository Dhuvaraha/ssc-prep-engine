from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Exam, Lesson, Question, Subject, Topic
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

        topic_rows = []
        for topic in topics:
            lesson_count = db.scalar(
                select(func.count(Lesson.id)).where(
                    Lesson.topic_id == topic.id,
                    Lesson.is_published.is_(True),
                )
            ) or 0
            question_count = db.scalar(
                select(func.count(Question.id)).where(
                    Question.topic_id == topic.id,
                    Question.verification_status == "verified",
                    Question.correct_option.is_not(None),
                )
            ) or 0
            topic_rows.append(
                {
                    "id": topic.id,
                    "slug": topic.slug,
                    "name": topic.name,
                    "priority": topic.priority,
                    "lesson_count": lesson_count,
                    "question_count": question_count,
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
