from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Bookmark,
    Exam,
    Flashcard,
    FlashcardProgress,
    Question,
    QuestionOption,
    RevisionItem,
    Subject,
    Topic,
    User,
)
from app.routers.revision import due_flashcards, get_revision_queue, list_bookmarks


def _fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="phase7p@example.com", password_hash="x")
    exam = Exam(slug="ssc-cgl-tier-1", name="CGL", duration_minutes=60)
    db.add_all([user, exam])
    db.flush()
    subject = Subject(exam_id=exam.id, slug="quant", name="Quant", sort_order=1)
    db.add(subject)
    db.flush()
    topic = Topic(subject_id=subject.id, slug="percentage", name="Percentage", priority=5)
    db.add(topic)
    db.flush()
    due = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)

    for idx in range(30):
        question = Question(
            exam_id=exam.id,
            subject_id=subject.id,
            topic_id=topic.id,
            question_text=f"question {idx}",
            correct_option=1,
            verification_status="verified",
        )
        db.add(question)
        db.flush()
        db.add(QuestionOption(question_id=question.id, position=1, text="Correct"))
        db.add(RevisionItem(
            user_id=user.id, question_id=question.id,
            reason="wrong", successful_reviews=0,
            next_review_at=due, is_active=True,
        ))
        db.add(Bookmark(user_id=user.id, question_id=question.id))

    for idx in range(60):
        card = Flashcard(topic_id=topic.id, front=f"front {idx}", back=f"back {idx}", is_published=True)
        db.add(card)
        db.flush()
        if idx % 2:
            db.add(FlashcardProgress(
                user_id=user.id, flashcard_id=card.id,
                next_review_at=due + timedelta(days=15),
                successful_reviews=2,
            ))
        elif idx % 4 == 0:
            db.add(FlashcardProgress(
                user_id=user.id, flashcard_id=card.id,
                next_review_at=due,
                successful_reviews=1,
            ))
    db.commit()
    # Keep the fixture user loaded; refreshing an expired identity is a separate
    # test-fixture query and should not count toward the endpoint's SQL budget.
    db.refresh(user)
    return engine, db, user


def _count_selects(engine, fn):
    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().lower().startswith("select"):
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", observe)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    return result, len(statements)


def test_revision_queue_30_questions_hydrates_in_constant_queries():
    engine, db, user = _fixture()
    try:
        items, queries = _count_selects(engine, lambda: get_revision_queue(
            reason=None, limit=30, db=db, user=user,
        ))
        assert len(items) == 30
        assert items[0]["question"]["question_text"] == "question 0"
        assert len(items[0]["question"]["options"]) == 1
        assert queries <= 4, f"Revision queue issued {queries} SELECT statements"
    finally:
        db.close()


def test_bookmarks_30_questions_hydrate_in_constant_queries():
    engine, db, user = _fixture()
    try:
        items, queries = _count_selects(engine, lambda: list_bookmarks(db=db, user=user))
        assert len(items) == 30
        assert len(items[-1]["question"]["options"]) == 1
        assert queries <= 4, f"Bookmarks issued {queries} SELECT statements"
    finally:
        db.close()


def test_flashcard_due_filter_is_applied_in_sql_not_python_loop():
    engine, db, user = _fixture()
    try:
        cards, queries = _count_selects(engine, lambda: due_flashcards(
            limit=20, db=db, user=user,
        ))
        assert len(cards) == 20
        assert all(not int(card["front"].split()[-1]) % 2 for card in cards)
        assert queries <= 2, f"Flashcards issued {queries} SELECT statements"
        assert any(card["successful_reviews"] == 1 for card in cards)
    finally:
        db.close()
