from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.deps import get_current_user
from app.domain.revision import next_revision_date
from app.models import (
    Bookmark,
    Flashcard,
    FlashcardProgress,
    Question,
    RevisionItem,
    User,
)

router = APIRouter(prefix="/revision", tags=["revision"])


@router.get("/queue")
def get_revision_queue(
    reason: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    stmt = (
        select(RevisionItem)
        .where(
            RevisionItem.user_id == user.id,
            RevisionItem.is_active.is_(True),
            RevisionItem.next_review_at <= now,
        )
        .order_by(RevisionItem.next_review_at, RevisionItem.id)
        .limit(limit)
    )
    if reason:
        stmt = stmt.where(RevisionItem.reason == reason)

    items = list(db.scalars(stmt))
    result = []
    for item in items:
        question = db.scalar(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id == item.question_id)
        )
        if not question:
            continue
        result.append(
            {
                "id": item.id,
                "reason": item.reason,
                "successful_reviews": item.successful_reviews,
                "next_review_at": item.next_review_at.isoformat(),
                "question": {
                    "id": question.id,
                    "topic_id": question.topic_id,
                    "question_text": question.question_text,
                    "question_image_url": question.question_image_url,
                    "correct_option": question.correct_option,
                    "explanation": question.explanation,
                    "fast_method": question.fast_method,
                    "options": [
                        {
                            "position": option.position,
                            "text": option.text,
                            "image_url": option.image_url,
                        }
                        for option in question.options
                    ],
                },
            }
        )
    return result


@router.post("/questions/{question_id}/add")
def add_question_to_revision(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    question = db.get(Question, question_id)
    if not question or question.verification_status != "verified":
        raise HTTPException(status_code=404, detail="Verified question not found")

    existing = db.scalar(
        select(RevisionItem).where(
            RevisionItem.user_id == user.id,
            RevisionItem.question_id == question_id,
            RevisionItem.is_active.is_(True),
        )
    )
    if existing:
        return {"added": False, "item_id": existing.id, "reason": existing.reason}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    item = RevisionItem(
        user_id=user.id,
        question_id=question_id,
        reason="manual",
        next_review_at=now,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"added": True, "item_id": item.id, "reason": item.reason}


@router.post("/items/{item_id}/review")
def review_revision_item(
    item_id: int,
    success: bool,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    item = db.get(RevisionItem, item_id)
    if not item or item.user_id != user.id or not item.is_active:
        raise HTTPException(status_code=404, detail="Revision item not found")

    today = datetime.now(timezone.utc).date()
    if success:
        item.successful_reviews += 1
        if item.successful_reviews >= 5:
            item.is_active = False
        else:
            due = next_revision_date(
                today=today,
                successful_reviews=item.successful_reviews,
                days_until_exam=10,
            )
            item.next_review_at = datetime.combine(due, datetime.min.time())
    else:
        item.successful_reviews = 0
        item.next_review_at = datetime.combine(today + timedelta(days=1), datetime.min.time())

    db.commit()
    return {
        "id": item.id,
        "successful_reviews": item.successful_reviews,
        "is_active": item.is_active,
        "next_review_at": item.next_review_at.isoformat(),
    }


@router.post("/bookmarks/{question_id}")
def toggle_bookmark(
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    existing = db.scalar(
        select(Bookmark).where(
            Bookmark.user_id == user.id,
            Bookmark.question_id == question_id,
        )
    )
    if existing:
        db.delete(existing)
        db.commit()
        return {"bookmarked": False}

    db.add(Bookmark(user_id=user.id, question_id=question_id))
    db.commit()
    return {"bookmarked": True}


@router.get("/bookmarks")
def list_bookmarks(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = list(
        db.scalars(
            select(Bookmark)
            .where(Bookmark.user_id == user.id)
            .order_by(Bookmark.created_at.desc())
        )
    )
    result = []
    for row in rows:
        question = db.scalar(
            select(Question)
            .options(selectinload(Question.options))
            .where(Question.id == row.question_id)
        )
        if not question:
            continue
        result.append(
            {
                "bookmark_id": row.id,
                "question": {
                    "id": question.id,
                    "question_text": question.question_text,
                    "question_image_url": question.question_image_url,
                    "correct_option": question.correct_option,
                    "explanation": question.explanation,
                    "fast_method": question.fast_method,
                    "options": [
                        {
                            "position": option.position,
                            "text": option.text,
                            "image_url": option.image_url,
                        }
                        for option in question.options
                    ],
                },
            }
        )
    return result


@router.get("/flashcards/due")
def due_flashcards(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    cards = list(
        db.scalars(
            select(Flashcard)
            .where(Flashcard.is_published.is_(True))
            .order_by(Flashcard.id)
        )
    )

    due = []
    for card in cards:
        progress = db.scalar(
            select(FlashcardProgress).where(
                FlashcardProgress.user_id == user.id,
                FlashcardProgress.flashcard_id == card.id,
            )
        )
        if progress and progress.next_review_at > now:
            continue
        due.append(
            {
                "id": card.id,
                "topic_id": card.topic_id,
                "front": card.front,
                "back": card.back,
                "related_fact": card.related_fact,
                "card_type": card.card_type,
                "successful_reviews": progress.successful_reviews if progress else 0,
            }
        )
        if len(due) >= limit:
            break
    return due


@router.post("/flashcards/{flashcard_id}/review")
def review_flashcard(
    flashcard_id: int,
    success: bool,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    card = db.get(Flashcard, flashcard_id)
    if not card or not card.is_published:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    progress = db.scalar(
        select(FlashcardProgress).where(
            FlashcardProgress.user_id == user.id,
            FlashcardProgress.flashcard_id == flashcard_id,
        )
    )
    if not progress:
        progress = FlashcardProgress(user_id=user.id, flashcard_id=flashcard_id)
        db.add(progress)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    progress.last_reviewed_at = now
    if success:
        progress.successful_reviews += 1
        due = next_revision_date(
            today=now.date(),
            successful_reviews=progress.successful_reviews,
            days_until_exam=10,
        )
        progress.next_review_at = datetime.combine(due, datetime.min.time())
    else:
        progress.successful_reviews = 0
        progress.next_review_at = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())

    db.commit()
    return {
        "flashcard_id": flashcard_id,
        "successful_reviews": progress.successful_reviews,
        "next_review_at": progress.next_review_at.isoformat(),
    }
