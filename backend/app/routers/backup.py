from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.content_access import teaching_user as get_current_user
from app.models import (
    Bookmark,
    DailyPlanTask,
    ExamTarget,
    FlashcardProgress,
    MockAttempt,
    MockAttemptQuestion,
    QuestionAttempt,
    RevisionItem,
    TopicMastery,
    User,
)

router = APIRouter(prefix="/backup", tags=["backup"])


def _serialize(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _row_dict(row, fields):
    return {field: _serialize(getattr(row, field)) for field in fields}


@router.get("/export")
def export_user_data(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempts = list(db.scalars(select(QuestionAttempt).where(QuestionAttempt.user_id == user.id)))
    mastery = list(db.scalars(select(TopicMastery).where(TopicMastery.user_id == user.id)))
    revisions = list(db.scalars(select(RevisionItem).where(RevisionItem.user_id == user.id)))
    bookmarks = list(db.scalars(select(Bookmark).where(Bookmark.user_id == user.id)))
    mocks = list(db.scalars(select(MockAttempt).where(MockAttempt.user_id == user.id)))
    targets = list(db.scalars(select(ExamTarget).where(ExamTarget.user_id == user.id)))
    plan_tasks = list(db.scalars(select(DailyPlanTask).where(DailyPlanTask.user_id == user.id)))
    card_progress = list(db.scalars(select(FlashcardProgress).where(FlashcardProgress.user_id == user.id)))

    mock_ids = [item.id for item in mocks]
    mock_questions = list(
        db.scalars(
            select(MockAttemptQuestion).where(MockAttemptQuestion.attempt_id.in_(mock_ids))
        )
    ) if mock_ids else []

    # Export revision identifiers only, never private source or question payloads.
    from app.core.config import get_settings
    import json
    from app.revision_models import DeliveryRevision, QuestionRevision
    evidence = list(db.scalars(select(DeliveryRevision).where(
        DeliveryRevision.user_id == user.id))) if get_settings().phase_b_capture_enabled else []
    captures = {r.id: json.loads(r.payload) for r in db.scalars(select(QuestionRevision).where(
        QuestionRevision.id.in_({p.revision_id for p in evidence})))} if evidence else {}

    return {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "revision_references": [
            {"kind": p.kind, "delivery_id": p.delivery_id, "question_id": p.question_id,
             "question_revision_id": p.revision_id,
             "capture_basis": captures[p.revision_id]['capture_kind'],
             "original_version_unknown": captures[p.revision_id]['original_version_unknown']} for p in evidence],
        "history_caution": "Absent references and migration-time captures have unknown original versions; saved results are unchanged.",
        "user": {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "created_at": _serialize(user.created_at),
        },
        "question_attempts": [
            _row_dict(item, [
                "id", "question_id", "selected_option", "is_correct", "time_seconds",
                "confidence", "used_hint", "mistake_type", "attempted_at"
            ])
            for item in attempts
        ],
        "topic_mastery": [
            _row_dict(item, ["topic_id", "mastery_score", "attempts", "correct", "updated_at"])
            for item in mastery
        ],
        "revision_items": [
            _row_dict(item, [
                "id", "question_id", "reason", "successful_reviews", "next_review_at", "is_active"
            ])
            for item in revisions
        ],
        "bookmarks": [
            _row_dict(item, ["id", "question_id", "created_at"])
            for item in bookmarks
        ],
        "mock_attempts": [
            _row_dict(item, [
                "id", "exam_id", "mode", "subject_slug", "duration_minutes", "status",
                "started_at", "submitted_at", "score", "correct_count", "incorrect_count",
                "unattempted_count"
            ])
            for item in mocks
        ],
        "mock_responses": [
            _row_dict(item, [
                "attempt_id", "question_id", "section_slug", "position", "selected_option",
                "marked_for_review", "time_seconds"
            ])
            for item in mock_questions
        ],
        "exam_targets": [
            _row_dict(item, ["exam_id", "exam_date", "daily_minutes", "is_active"])
            for item in targets
        ],
        "daily_plan_tasks": [
            _row_dict(item, [
                "id", "plan_date", "activity_type", "subject_slug", "topic_id", "title",
                "target_minutes", "target_questions", "priority", "status", "created_at"
            ])
            for item in plan_tasks
        ],
        "flashcard_progress": [
            _row_dict(item, [
                "flashcard_id", "successful_reviews", "next_review_at", "last_reviewed_at"
            ])
            for item in card_progress
        ],
    }
