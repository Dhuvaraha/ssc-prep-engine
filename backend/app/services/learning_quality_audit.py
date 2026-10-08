"""Read-only pre-publication learning content quality report.

This is a candidate/reviewer audit, NOT an automatic claim that factual
answers are correct. Source checks, mathematics proofs, diagrams and current
affairs require human verification even when the metadata passes.
"""

from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Exam, Lesson, Question, Subject, Topic


MIN_DISTINCT_PER_LEVEL = 5
SHORT_SOLUTION_CHARS = 60


def _choice_key(option) -> str:
    text = (option.text or "").strip().lower()
    image = (option.image_url or "").strip()
    return text if text else ("image:" + image if image else "")


def collect_learning_quality(db: Session, *, exam_slug: str) -> dict:
    exam = db.scalar(select(Exam).where(Exam.slug == exam_slug))
    if exam is None:
        raise ValueError("Exam not found")

    topics = list(db.scalars(
        select(Topic).join(Subject, Subject.id == Topic.subject_id)
        .where(Subject.exam_id == exam.id)
        .order_by(Subject.sort_order, Topic.name)
    ))
    subject_by_id = {
        subject.id: subject.slug for subject in db.scalars(
            select(Subject).where(Subject.exam_id == exam.id)
        )
    }
    lesson_topics = set(db.scalars(
        select(Lesson.topic_id).where(
            Lesson.topic_id.in_([topic.id for topic in topics]),
            Lesson.is_published.is_(True),
        )
    )) if topics else set()

    # Two bounded-in-count queries, one for all verified questions and one for
    # their options, avoiding the per-question SQL N+1 problem.
    verified = list(db.scalars(
        select(Question)
        .options(selectinload(Question.options))
        .where(Question.exam_id == exam.id, Question.verification_status == "verified")
        .order_by(Question.id)
    ).unique())

    questions_by_topic: dict[int, list[Question]] = defaultdict(list)
    for question in verified:
        if question.topic_id is not None:
            questions_by_topic[question.topic_id].append(question)

    reports = []
    incomplete_levels = []
    solution_review_total = 0
    answer_audit_total = 0

    for topic in topics:
        questions = questions_by_topic.get(topic.id, [])
        levels = Counter(q.difficulty for q in questions)
        short_solutions = 0
        invalid_options = 0
        distinct_patterns = set()
        source_review = 0

        for q in questions:
            if q.pattern_type:
                distinct_patterns.add(q.pattern_type)
            solution = (q.explanation or "").strip() + " " + (q.fast_method or "").strip()
            if len(solution.strip()) < SHORT_SOLUTION_CHARS:
                short_solutions += 1
            choice_keys = [_choice_key(option) for option in q.options]
            if (
                q.correct_option not in (1, 2, 3, 4)
                or len(q.options) != 4
                or len({option.position for option in q.options}) != 4
                or "" in choice_keys
                or len(set(choice_keys)) != 4
            ):
                invalid_options += 1
            if not (q.source_reference or "").strip():
                source_review += 1

        shortage = {
            difficulty: max(0, MIN_DISTINCT_PER_LEVEL - levels.get(difficulty, 0))
            for difficulty in (1, 2, 3)
            if levels.get(difficulty, 0) < MIN_DISTINCT_PER_LEVEL
        }
        if shortage:
            incomplete_levels.append(topic.name)
        solution_review_total += short_solutions
        answer_audit_total += invalid_options
        reports.append({
            "topic_id": topic.id,
            "topic": topic.name,
            "subject": subject_by_id.get(topic.subject_id, "unknown"),
            "lesson_published": topic.id in lesson_topics,
            "verified_questions": len(questions),
            "difficulty_counts": {
                "easy": levels.get(1, 0), "medium": levels.get(2, 0), "hard": levels.get(3, 0)
            },
            "level_shortage": shortage,
            "distinct_pattern_types": len(distinct_patterns),
            "brief_solution_review": short_solutions,
            "invalid_options_review": invalid_options,
            "source_reference_review": source_review,
            "content_status": (
                "missing_lesson" if topic.id not in lesson_topics else
                "insufficient_level_questions" if shortage else
                "answer_options_need_review" if invalid_options else
                "solution_review_needed" if short_solutions else
                "automated_checks_passed"
            ),
        })

    return {
        "exam_slug": exam_slug,
        "topics_audited": len(topics),
        "verified_questions_audited": len(verified),
        "topics_missing_level_floor": len(incomplete_levels),
        "missing_level_topics": incomplete_levels,
        "brief_solution_review_count": solution_review_total,
        "answer_options_review_count": answer_audit_total,
        "human_fact_check_required": True,
        "topic_reports": reports,
    }
