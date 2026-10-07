from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Exam, Lesson, LessonBlock, Question, QuestionArchetype, Subject, Topic


CORE_BLOCKS = {"concept", "recognition", "method", "trap"}
SUBJECT_EXTRA_BLOCKS = {
    "reasoning": {"shortcut"},
    "quant": {"shortcut"},
    "english": set(),
    "general-awareness": {"recall"},
}


def collect_teacher_readiness(db: Session, *, exam_slug: str = "ssc-cgl-tier-1") -> dict:
    exam = db.scalar(select(Exam).where(Exam.slug == exam_slug))
    if not exam:
        raise ValueError("Exam not found")

    subjects = list(
        db.scalars(
            select(Subject)
            .where(Subject.exam_id == exam.id)
            .order_by(Subject.sort_order, Subject.id)
        )
    )
    subject_by_id = {subject.id: subject for subject in subjects}
    topics = list(
        db.scalars(
            select(Topic)
            .join(Subject, Subject.id == Topic.subject_id)
            .where(Subject.exam_id == exam.id)
            .order_by(Subject.sort_order, Topic.priority.desc(), Topic.id)
        )
    )

    topic_ids = [topic.id for topic in topics]
    lesson_rows = db.execute(
        select(Lesson.id, Lesson.topic_id)
        .where(Lesson.topic_id.in_(topic_ids), Lesson.is_published.is_(True))
    ).all() if topic_ids else []
    lesson_ids = [int(row[0]) for row in lesson_rows]
    lesson_topic = {int(lesson_id): int(topic_id) for lesson_id, topic_id in lesson_rows}

    blocks_by_topic: dict[int, set[str]] = {topic.id: set() for topic in topics}
    if lesson_ids:
        for lesson_id, block_type in db.execute(
            select(LessonBlock.lesson_id, LessonBlock.block_type)
            .where(
                LessonBlock.lesson_id.in_(lesson_ids),
                LessonBlock.is_published.is_(True),
            )
        ).all():
            topic_id = lesson_topic.get(int(lesson_id))
            if topic_id is not None:
                blocks_by_topic[topic_id].add(str(block_type))

    archetypes = Counter(
        {
            int(topic_id): int(count)
            for topic_id, count in db.execute(
                select(QuestionArchetype.topic_id, func.count(QuestionArchetype.id))
                .where(
                    QuestionArchetype.topic_id.in_(topic_ids),
                    QuestionArchetype.is_published.is_(True),
                )
                .group_by(QuestionArchetype.topic_id)
            ).all()
        }
    ) if topic_ids else Counter()

    explained_by_difficulty: dict[int, set[int]] = {topic.id: set() for topic in topics}
    if topic_ids:
        for topic_id, difficulty in db.execute(
            select(Question.topic_id, Question.difficulty)
            .where(
                Question.exam_id == exam.id,
                Question.topic_id.in_(topic_ids),
                Question.verification_status == "verified",
                Question.correct_option.is_not(None),
                Question.explanation.is_not(None),
                func.length(func.trim(Question.explanation)) > 0,
            )
            .group_by(Question.topic_id, Question.difficulty)
        ).all():
            if topic_id is not None:
                explained_by_difficulty[int(topic_id)].add(int(difficulty))

    rows = []
    for topic in topics:
        subject = subject_by_id[topic.subject_id]
        required = set(CORE_BLOCKS) | SUBJECT_EXTRA_BLOCKS.get(subject.slug, set())
        block_types = blocks_by_topic.get(topic.id, set())
        failures: list[str] = []
        missing_blocks = sorted(required - block_types)
        if missing_blocks:
            failures.append("missing_blocks:" + ",".join(missing_blocks))
        if archetypes[topic.id] < 1:
            failures.append("no_published_archetype")
        difficulty_set = explained_by_difficulty.get(topic.id, set())
        for level in (1, 2, 3):
            if level not in difficulty_set:
                failures.append(f"missing_verified_example:d{level}")

        rows.append(
            {
                "subject": subject.slug,
                "topic_id": topic.id,
                "topic": topic.slug,
                "ready": not failures,
                "failures": failures,
                "published_block_types": sorted(block_types),
                "published_archetypes": archetypes[topic.id],
                "verified_example_difficulties": sorted(difficulty_set),
            }
        )

    pending = [row for row in rows if not row["ready"]]
    return {
        "exam_slug": exam_slug,
        "topics": len(rows),
        "ready_topics": len(rows) - len(pending),
        "pending_topics": len(pending),
        "status": "ready" if not pending else "attention",
        "items": rows,
    }
