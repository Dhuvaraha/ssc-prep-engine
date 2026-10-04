from sqlalchemy import select

from app.content.cgl_topics import CGL_TOPICS
from app.db import Base, SessionLocal, engine
from app.models import Exam, Subject, Topic


SUBJECT_NAMES = {
    "reasoning": "General Intelligence & Reasoning",
    "general-awareness": "General Awareness",
    "quant": "Quantitative Aptitude",
    "english": "English Comprehension",
}


def slugify(value: str) -> str:
    return (
        value.lower()
        .replace("&", "and")
        .replace(",", "")
        .replace("/", "-")
        .replace(" ", "-")
    )


def seed() -> None:
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        exam = db.scalar(select(Exam).where(Exam.slug == "ssc-cgl-tier-1"))
        if not exam:
            exam = Exam(
                slug="ssc-cgl-tier-1",
                name="SSC CGL Tier I",
                duration_minutes=60,
                positive_marks=2.0,
                negative_marks=0.5,
            )
            db.add(exam)
            db.flush()

        for order, (subject_slug, topics) in enumerate(CGL_TOPICS.items(), start=1):
            subject = db.scalar(
                select(Subject).where(
                    Subject.exam_id == exam.id,
                    Subject.slug == subject_slug,
                )
            )
            if not subject:
                subject = Subject(
                    exam_id=exam.id,
                    slug=subject_slug,
                    name=SUBJECT_NAMES[subject_slug],
                    sort_order=order,
                )
                db.add(subject)
                db.flush()

            for topic_name in topics:
                topic_slug = slugify(topic_name)
                exists = db.scalar(
                    select(Topic).where(
                        Topic.subject_id == subject.id,
                        Topic.slug == topic_slug,
                    )
                )
                if not exists:
                    db.add(
                        Topic(
                            subject_id=subject.id,
                            slug=topic_slug,
                            name=topic_name,
                            priority=3,
                        )
                    )

        db.commit()


if __name__ == "__main__":
    seed()
