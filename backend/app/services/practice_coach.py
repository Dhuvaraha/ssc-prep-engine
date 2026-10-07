from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Lesson, LessonBlock, Question, QuestionArchetype


COACH_BLOCK_TYPES = {
    "recognition",
    "formula",
    "method",
    "shortcut",
    "trap",
    "example_easy",
    "example_exam",
    "example_hard",
}


def _first(blocks: list[LessonBlock], *types: str) -> str | None:
    for block in blocks:
        if block.block_type in types and block.body:
            return block.body
    return None


def build_question_coaching(db: Session, question: Question) -> dict | None:
    if question.topic_id is None:
        return None

    archetype = None
    if question.pattern_type:
        archetype = db.scalar(
            select(QuestionArchetype)
            .where(
                QuestionArchetype.topic_id == question.topic_id,
                QuestionArchetype.slug == question.pattern_type,
                QuestionArchetype.is_published.is_(True),
            )
            .limit(1)
        )

    lesson_ids = select(Lesson.id).where(
        Lesson.topic_id == question.topic_id,
        Lesson.is_published.is_(True),
    )
    blocks = list(
        db.scalars(
            select(LessonBlock)
            .where(
                LessonBlock.lesson_id.in_(lesson_ids),
                LessonBlock.is_published.is_(True),
                LessonBlock.block_type.in_(COACH_BLOCK_TYPES),
            )
            .order_by(LessonBlock.sort_order, LessonBlock.id)
        )
    )

    if archetype:
        difficulty_rule = {
            1: archetype.easy_rule,
            2: archetype.medium_rule,
            3: archetype.hard_rule,
        }.get(max(1, min(3, question.difficulty)))
        pattern_name = archetype.name
        skill = archetype.skill
        recognition = archetype.recognition_cues
        standard_method = archetype.canonical_method
        fast_method = question.fast_method or archetype.shortcut_method or _first(blocks, "shortcut")
        common_trap = archetype.common_trap or _first(blocks, "trap")
    else:
        difficulty_rule = None
        pattern_name = (question.pattern_type or question.subtopic or "Topic application").replace("-", " ").title()
        skill = question.subtopic or question.pattern_type
        recognition = _first(blocks, "recognition")
        standard_method = _first(blocks, "method", "formula")
        fast_method = question.fast_method or _first(blocks, "shortcut")
        common_trap = _first(blocks, "trap")

    worked_example = (
        _first(blocks, "example_exam")
        or _first(blocks, "example_easy")
        or _first(blocks, "example_hard")
    )

    hint_steps: list[str] = []
    for value in (recognition, standard_method, fast_method):
        if value and value not in hint_steps:
            hint_steps.append(value)

    return {
        "pattern_name": pattern_name,
        "skill": skill,
        "recognition_cues": recognition,
        "standard_method": standard_method,
        "fast_method": fast_method,
        "common_trap": common_trap,
        "difficulty_rule": difficulty_rule,
        "worked_example": worked_example,
        "hint_steps": hint_steps,
        "archetype_exact": archetype is not None,
    }
