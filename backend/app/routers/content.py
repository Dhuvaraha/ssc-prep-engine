from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Exam, Lesson, Subject, Topic
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
    """
    Return the lightweight syllabus/lesson tree used by the Learn landing page.

    Do not scan the question bank here. The old implementation loaded every
    verified question and all four option rows just to render counts, which made
    opening Learn proportional to the full 10k-question corpus. Exact content
    integrity is audited separately; the learner navigation only needs topic and
    lesson metadata.
    """
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

    topics = list(
        db.scalars(
            select(Topic)
            .join(Subject, Subject.id == Topic.subject_id)
            .where(Subject.exam_id == exam.id)
            .order_by(Subject.sort_order, Topic.priority.desc(), Topic.name)
        )
    )
    topic_ids = [topic.id for topic in topics]

    lesson_counts: dict[int, int] = {}
    if topic_ids:
        lesson_counts = {
            topic_id: int(count)
            for topic_id, count in db.execute(
                select(Lesson.topic_id, func.count(Lesson.id))
                .where(
                    Lesson.topic_id.in_(topic_ids),
                    Lesson.is_published.is_(True),
                )
                .group_by(Lesson.topic_id)
            )
        }

    topics_by_subject: dict[int, list[Topic]] = {}
    for topic in topics:
        topics_by_subject.setdefault(topic.subject_id, []).append(topic)

    result = []
    for subject in subjects:
        topic_rows = [
            {
                "id": topic.id,
                "slug": topic.slug,
                "name": topic.name,
                "priority": topic.priority,
                "lesson_count": lesson_counts.get(topic.id, 0),
            }
            for topic in topics_by_subject.get(subject.id, [])
        ]
        result.append(
            {
                "id": subject.id,
                "slug": subject.slug,
                "name": subject.name,
                "lesson_count": sum(item["lesson_count"] for item in topic_rows),
                "topic_count": len(topic_rows),
                "topics": topic_rows,
            }
        )

    return {
        "exam": {"id": exam.id, "slug": exam.slug, "name": exam.name},
        "totals": {
            "lessons": sum(item["lesson_count"] for item in result),
            "topics": sum(item["topic_count"] for item in result),
        },
        "subjects": result,
    }
