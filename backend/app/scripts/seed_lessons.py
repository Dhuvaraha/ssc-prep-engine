from sqlalchemy import select

from app.content.lesson_seed import LESSONS
from app.db import Base, SessionLocal, engine
from app.models import Lesson, Subject, Topic


def seed_lessons() -> None:
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        for row in LESSONS:
            subject = db.scalar(select(Subject).where(Subject.slug == row["subject"]))
            if not subject:
                continue

            topic = db.scalar(
                select(Topic).where(
                    Topic.subject_id == subject.id,
                    Topic.slug == row["topic"],
                )
            )
            if not topic:
                continue

            existing = db.scalar(
                select(Lesson).where(
                    Lesson.topic_id == topic.id,
                    Lesson.title == row["title"],
                )
            )
            if existing:
                continue

            db.add(
                Lesson(
                    topic_id=topic.id,
                    title=row["title"],
                    intro=row["intro"],
                    concept=row["concept"],
                    shortcut=row.get("shortcut"),
                    worked_example=row.get("worked_example"),
                    memory_rule=row.get("memory_rule"),
                    common_traps=row.get("common_traps"),
                    estimated_minutes=row.get("estimated_minutes", 10),
                )
            )

        db.commit()


if __name__ == "__main__":
    seed_lessons()
