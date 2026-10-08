"""Publish only independently reviewed alternative-option learning context.

All insights are selected AFTER answer submission. No hint is given that
would identify the correct option while an assessment is in progress.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Question, QuestionOptionInsight


def published_option_insights(db: Session, *, question: Question) -> list[dict]:
    # Correct-choice explanation already comes from the question itself.
    # Alternative insights may be published only for existing wrong options.
    valid_positions = {option.position for option in question.options}
    insights = db.scalars(
        select(QuestionOptionInsight)
        .where(
            QuestionOptionInsight.question_id == question.id,
            QuestionOptionInsight.review_status == "published",
            QuestionOptionInsight.reviewed_at.is_not(None),
        )
        .order_by(QuestionOptionInsight.option_position)
    )
    return [
        {
            "position": item.option_position,
            "insight_type": item.insight_type,
            "knowledge_text": item.knowledge_text,
            "related_question": item.related_question if item.related_answer else None,
            "related_answer": item.related_answer if item.related_question else None,
            "source_reference": item.source_reference,
            "source_year": item.source_year,
        }
        for item in insights
        if (
            item.option_position in valid_positions
            and item.option_position != question.correct_option
            and item.insight_type in {"fact", "rule", "misconception", "comparison"}
            and bool(item.knowledge_text and item.knowledge_text.strip())
            and bool(item.source_reference and item.source_reference.strip())
        )
    ]
