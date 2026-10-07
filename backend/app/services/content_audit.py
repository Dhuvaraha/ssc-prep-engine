from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

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
from app.services.question_quality import unique_questions


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

    verified_questions = list(
        db.scalars(
            select(Question)
            .options(selectinload(Question.options))
            .where(*verified_filter, Question.correct_option.is_not(None))
            .order_by(Question.id)
        ).unique()
    )
    verified_questions_by_topic: dict[int, list[Question]] = defaultdict(list)
    for question in verified_questions:
        if question.topic_id is not None:
            verified_questions_by_topic[int(question.topic_id)].append(question)
    unique_verified_by_topic = {
        topic_id: len(unique_questions(rows))
        for topic_id, rows in verified_questions_by_topic.items()
    }
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
            verified_questions=unique_verified_by_topic.get(topic.id, 0),
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

    verified_question_rows = db.execute(
        select(
            Question.id,
            Question.topic_id,
            Question.source_type,
            Question.correct_option,
            Question.subtopic,
        ).where(*verified_filter)
    ).all()
    verified_question_ids = [int(row[0]) for row in verified_question_rows]
    question_topic = {
        int(question_id): int(topic_id) if topic_id is not None else None
        for question_id, topic_id, _, _, _ in verified_question_rows
    }
    question_source = {
        int(question_id): str(source_type)
        for question_id, _, source_type, _, _ in verified_question_rows
    }
    question_correct = {
        int(question_id): int(correct_option) if correct_option is not None else None
        for question_id, _, _, correct_option, _ in verified_question_rows
    }
    topic_labels = {
        topic.id: (
            next(
                (subject.slug for subject in subjects if subject.id == topic.subject_id),
                "unknown",
            )
            + "/"
            + topic.slug
        )
        for topic in topics
    }

    invalid_option_count = 0
    duplicate_option_count = 0
    duplicate_by_topic: Counter[str] = Counter()
    duplicate_by_source: Counter[str] = Counter()
    duplicate_shape: Counter[str] = Counter()
    duplicate_correct_payload = 0
    duplicate_distractor_only = 0
    duplicate_with_image = 0
    duplicate_text_only = 0
    empty_option_content_sets = 0
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
        if len(non_empty) != len(identities):
            empty_option_content_sets += 1

        groups: dict[str, list[int]] = defaultdict(list)
        for (position, _, _), identity in zip(options, identities):
            if identity != "\u0000":
                groups[identity].append(position)
        repeated_groups = [positions for positions in groups.values() if len(positions) > 1]

        if repeated_groups:
            duplicate_option_count += 1
            topic_id = question_topic.get(int(question_id))
            duplicate_by_topic[topic_labels.get(topic_id, "unassigned")] += 1
            duplicate_by_source[question_source.get(int(question_id), "unknown")] += 1
            duplicate_shape[f"{len(set(non_empty))}-unique"] += 1

            correct_position = question_correct.get(int(question_id))
            if correct_position is not None and any(
                correct_position in positions for positions in repeated_groups
            ):
                duplicate_correct_payload += 1
            else:
                duplicate_distractor_only += 1

            duplicate_identities = {
                identity for identity, positions in groups.items() if len(positions) > 1
            }
            duplicate_rows = [
                row
                for row, identity in zip(options, identities)
                if identity in duplicate_identities
            ]
            if any((image_url or "").strip() for _, _, image_url in duplicate_rows):
                duplicate_with_image += 1
            else:
                duplicate_text_only += 1

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
    missing_pattern_clause = (
        Question.pattern_type.is_(None)
        | (func.length(func.trim(Question.pattern_type)) == 0)
    )
    missing_pattern = int(
        db.scalar(
            select(func.count(Question.id)).where(
                *verified_filter,
                missing_pattern_clause,
            )
        )
        or 0
    )
    missing_pattern_by_topic = Counter()
    missing_pattern_with_subtopic = 0
    missing_pattern_without_subtopic = 0
    for topic_id, count in db.execute(
        select(Question.topic_id, func.count(Question.id))
        .where(
            *verified_filter,
            missing_pattern_clause,
        )
        .group_by(Question.topic_id)
    ).all():
        label = topic_labels.get(int(topic_id), "unassigned") if topic_id is not None else "unassigned"
        missing_pattern_by_topic[label] = int(count)

    for subtopic, count in db.execute(
        select(Question.subtopic, func.count(Question.id))
        .where(*verified_filter, missing_pattern_clause)
        .group_by(Question.subtopic)
    ).all():
        if subtopic and str(subtopic).strip():
            missing_pattern_with_subtopic += int(count)
        else:
            missing_pattern_without_subtopic += int(count)

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
                "unique_verified_questions": sum(
                    unique_verified_by_topic.get(topic.id, 0)
                    for topic in subject_topics
                ),
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
        "unique_verified_questions": sum(unique_verified_by_topic.values()),
        "topics": len(topics),
        "subjects": subject_summary,
        "pending_topic_count": len(pending_topics),
        "pending_topics": pending_topics,
        "question_integrity": {
            "invalid_option_sets": invalid_option_count,
            "invalid_correct_options": invalid_correct_option,
            "duplicate_option_sets": duplicate_option_count,
            "empty_option_content_sets": empty_option_content_sets,
            "missing_explanations": missing_explanation,
            "missing_fast_methods": missing_fast_method,
            "missing_expected_time": missing_expected_time,
            "missing_pattern_type": missing_pattern,
        },
        "diagnostics": {
            "duplicate_option_sets_by_topic": dict(duplicate_by_topic.most_common()),
            "duplicate_option_sets_by_source": dict(duplicate_by_source.most_common()),
            "duplicate_shape": dict(duplicate_shape.most_common()),
            "duplicate_correct_answer_payload": duplicate_correct_payload,
            "duplicate_distractor_only": duplicate_distractor_only,
            "duplicate_with_image": duplicate_with_image,
            "duplicate_text_only": duplicate_text_only,
            "missing_pattern_type_by_topic": dict(missing_pattern_by_topic.most_common()),
            "missing_pattern_with_subtopic": missing_pattern_with_subtopic,
            "missing_pattern_without_subtopic": missing_pattern_without_subtopic,
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
