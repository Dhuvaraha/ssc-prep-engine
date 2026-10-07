from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.readiness import TopicReadiness, readiness_failures
from app.models import (
    Exam,
    Flashcard,
    Lesson,
    LessonBlock,
    Question,
    QuestionArchetype,
    QuestionOption,
    Subject,
    Topic,
)


def _count_map(rows) -> dict[int, int]:
    return {int(key): int(value or 0) for key, value in rows}


def collect_content_audit(
    db: Session,
    *,
    exam_slug: str = "ssc-cgl-tier-1",
    current_year: int | None = None,
) -> dict:
    current_year = current_year or date.today().year
    exam = db.scalar(select(Exam).where(Exam.slug == exam_slug))
    if not exam:
        return {
            "exam_slug": exam_slug,
            "status": "exam_missing",
            "critical_issues": 1,
        }

    subjects = list(
        db.scalars(
            select(Subject)
            .where(Subject.exam_id == exam.id)
            .order_by(Subject.sort_order, Subject.id)
        )
    )
    topics = list(
        db.scalars(
            select(Topic)
            .join(Subject, Topic.subject_id == Subject.id)
            .where(Subject.exam_id == exam.id)
            .order_by(Subject.sort_order, Topic.id)
        )
    )

    verified_filter = (
        Question.exam_id == exam.id,
        Question.verification_status == "verified",
    )

    verified_by_subject = _count_map(
        db.execute(
            select(Question.subject_id, func.count(Question.id))
            .where(*verified_filter)
            .group_by(Question.subject_id)
        ).all()
    )
    verified_by_topic = _count_map(
        db.execute(
            select(Question.topic_id, func.count(Question.id))
            .where(*verified_filter, Question.topic_id.is_not(None))
            .group_by(Question.topic_id)
        ).all()
    )
    visual_by_topic = _count_map(
        db.execute(
            select(Question.topic_id, func.count(Question.id))
            .where(
                *verified_filter,
                Question.topic_id.is_not(None),
                Question.question_image_url.is_not(None),
            )
            .group_by(Question.topic_id)
        ).all()
    )
    official_by_topic = _count_map(
        db.execute(
            select(Question.topic_id, func.count(Question.id))
            .where(
                *verified_filter,
                Question.topic_id.is_not(None),
                Question.source_type == "official",
            )
            .group_by(Question.topic_id)
        ).all()
    )
    newest_year_by_topic = {
        int(topic_id): newest_year
        for topic_id, newest_year in db.execute(
            select(Question.topic_id, func.max(Question.year))
            .where(*verified_filter, Question.topic_id.is_not(None))
            .group_by(Question.topic_id)
        ).all()
    }

    lesson_blocks_by_topic = _count_map(
        db.execute(
            select(Lesson.topic_id, func.count(LessonBlock.id))
            .join(LessonBlock, LessonBlock.lesson_id == Lesson.id)
            .where(Lesson.is_published.is_(True), LessonBlock.is_published.is_(True))
            .group_by(Lesson.topic_id)
        ).all()
    )
    archetypes_by_topic = _count_map(
        db.execute(
            select(QuestionArchetype.topic_id, func.count(QuestionArchetype.id))
            .where(QuestionArchetype.is_published.is_(True))
            .group_by(QuestionArchetype.topic_id)
        ).all()
    )
    flashcards_by_topic = _count_map(
        db.execute(
            select(Flashcard.topic_id, func.count(Flashcard.id))
            .where(Flashcard.is_published.is_(True), Flashcard.topic_id.is_not(None))
            .group_by(Flashcard.topic_id)
        ).all()
    )

    pending_topics: list[dict] = []
    for topic in topics:
        subject = next((item for item in subjects if item.id == topic.subject_id), None)
        if not subject:
            continue
        item = TopicReadiness(
            subject_slug=subject.slug,
            topic_slug=topic.slug,
            verified_questions=verified_by_topic.get(topic.id, 0),
            lesson_blocks=lesson_blocks_by_topic.get(topic.id, 0),
            archetypes=archetypes_by_topic.get(topic.id, 0),
            flashcards=flashcards_by_topic.get(topic.id, 0),
            visual_questions=visual_by_topic.get(topic.id, 0),
            official_questions=official_by_topic.get(topic.id, 0),
            newest_year=newest_year_by_topic.get(topic.id),
        )
        failures = readiness_failures(item, current_year=current_year)
        if failures:
            pending_topics.append(
                {
                    "subject": subject.slug,
                    "topic": topic.slug,
                    "failures": failures,
                }
            )

    option_rows = db.execute(
        select(
            QuestionOption.question_id,
            QuestionOption.position,
            QuestionOption.text,
            QuestionOption.image_url,
        )
        .join(Question, Question.id == QuestionOption.question_id)
        .where(*verified_filter)
        .order_by(QuestionOption.question_id, QuestionOption.position)
    ).all()

    options_by_question: dict[int, list[tuple[int, str | None, str | None]]] = defaultdict(list)
    for question_id, position, text_value, image_url in option_rows:
        options_by_question[int(question_id)].append(
            (int(position), text_value, image_url)
        )

    verified_question_ids = list(
        db.scalars(select(Question.id).where(*verified_filter))
    )
    invalid_option_count = 0
    duplicate_option_count = 0
    for question_id in verified_question_ids:
        options = options_by_question.get(int(question_id), [])
        positions = [item[0] for item in options]
        if len(options) != 4 or positions != [1, 2, 3, 4]:
            invalid_option_count += 1

        identities: list[str] = []
        for _, text_value, image_url in options:
            text_key = " ".join((text_value or "").split()).casefold()
            image_key = (image_url or "").strip()
            identities.append(text_key + "\u0000" + image_key)
        non_empty = [
            value for value in identities
            if value != "\u0000"
        ]
        if len(non_empty) != len(set(non_empty)):
            duplicate_option_count += 1

    invalid_correct_option = int(
        db.scalar(
            select(func.count(Question.id)).where(
                *verified_filter,
                (
                    Question.correct_option.is_(None)
                    | (Question.correct_option < 1)
                    | (Question.correct_option > 4)
                ),
            )
        )
        or 0
    )
    missing_explanation = int(
        db.scalar(
            select(func.count(Question.id)).where(
                *verified_filter,
                (
                    Question.explanation.is_(None)
                    | (func.length(func.trim(Question.explanation)) == 0)
                ),
            )
        )
        or 0
    )
    missing_fast_method = int(
        db.scalar(
            select(func.count(Question.id)).where(
                *verified_filter,
                (
                    Question.fast_method.is_(None)
                    | (func.length(func.trim(Question.fast_method)) == 0)
                ),
            )
        )
        or 0
    )
    missing_expected_time = int(
        db.scalar(
            select(func.count(Question.id)).where(
                *verified_filter,
                Question.expected_time_seconds.is_(None),
            )
        )
        or 0
    )
    missing_pattern = int(
        db.scalar(
            select(func.count(Question.id)).where(
                *verified_filter,
                (
                    Question.pattern_type.is_(None)
                    | (func.length(func.trim(Question.pattern_type)) == 0)
                ),
            )
        )
        or 0
    )

    difficulty = Counter(
        {
            str(level): int(count)
            for level, count in db.execute(
                select(Question.difficulty, func.count(Question.id))
                .where(*verified_filter)
                .group_by(Question.difficulty)
            ).all()
        }
    )
    source_types = {
        str(source): int(count)
        for source, count in db.execute(
            select(Question.source_type, func.count(Question.id))
            .where(*verified_filter)
            .group_by(Question.source_type)
        ).all()
    }

    subject_summary = []
    for subject in subjects:
        subject_topics = [topic for topic in topics if topic.subject_id == subject.id]
        subject_summary.append(
            {
                "slug": subject.slug,
                "topics": len(subject_topics),
                "verified_questions": verified_by_subject.get(subject.id, 0),
                "ready_topics": len(subject_topics)
                - sum(1 for row in pending_topics if row["subject"] == subject.slug),
            }
        )

    total_verified = len(verified_question_ids)
    critical_issues = (
        invalid_option_count
        + invalid_correct_option
        + duplicate_option_count
    )

    return {
        "exam_slug": exam.slug,
        "status": "ready" if critical_issues == 0 and not pending_topics else "attention",
        "critical_issues": critical_issues,
        "verified_questions": total_verified,
        "topics": len(topics),
        "subjects": subject_summary,
        "pending_topic_count": len(pending_topics),
        "pending_topics": pending_topics,
        "question_integrity": {
            "invalid_option_sets": invalid_option_count,
            "invalid_correct_options": invalid_correct_option,
            "duplicate_option_sets": duplicate_option_count,
            "missing_explanations": missing_explanation,
            "missing_fast_methods": missing_fast_method,
            "missing_expected_time": missing_expected_time,
            "missing_pattern_type": missing_pattern,
        },
        "difficulty": dict(sorted(difficulty.items())),
        "source_types": dict(sorted(source_types.items())),
        "published": {
            "lesson_blocks": sum(lesson_blocks_by_topic.values()),
            "archetypes": sum(archetypes_by_topic.values()),
            "flashcards": int(
                db.scalar(
                    select(func.count(Flashcard.id)).where(
                        Flashcard.is_published.is_(True)
                    )
                )
                or 0
            ),
        },
    }
