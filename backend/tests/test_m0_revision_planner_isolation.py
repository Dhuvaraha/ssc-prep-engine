"""M0 stage isolation: revision, cards and study plans cannot mix CGL/JE."""
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Bookmark, Exam, ExamTarget, Flashcard, Question, RevisionItem,
    Subject, Topic, User,
)
from app.routers.revision import (
    add_question_to_revision, due_flashcards, get_revision_queue,
    list_bookmarks, review_flashcard, review_revision_item, toggle_bookmark,
)
from app.services.planner import generate_today_plan, rebuild_today_plan


def _two_exam_fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="rev-multi@example.com", password_hash="x")
    cgl = Exam(slug="ssc-cgl-tier-1", name="CGL", duration_minutes=60)
    je = Exam(slug="ssc-je-telecom-paper-1", name="JE", duration_minutes=120)
    db.add_all([user, cgl, je])
    db.flush()
    a = Subject(exam_id=cgl.id, slug="quant", name="Quant")
    b = Subject(exam_id=je.id, slug="telecom-technical", name="Telecom")
    db.add_all([a,b])
    db.flush()
    ta = Topic(subject_id=a.id, slug="percentage", name="Percentage")
    tb = Topic(subject_id=b.id, slug="circuits", name="Circuits")
    db.add_all([ta,tb])
    db.flush()
    qa = Question(exam_id=cgl.id, subject_id=a.id, topic_id=ta.id,
                  question_text="CGL Question", correct_option=1,
                  verification_status="verified")
    qb = Question(exam_id=je.id, subject_id=b.id, topic_id=tb.id,
                  question_text="JE Question", correct_option=1,
                  verification_status="verified")
    db.add_all([qa,qb])
    db.flush()
    due = datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=1)
    ra = RevisionItem(user_id=user.id, question_id=qa.id, reason="wrong", next_review_at=due)
    rb = RevisionItem(user_id=user.id, question_id=qb.id, reason="wrong", next_review_at=due)
    fa = Flashcard(topic_id=ta.id, front="CGL fact", back="CGL answer", is_published=True)
    fb = Flashcard(topic_id=tb.id, front="JE fact", back="JE answer", is_published=True)
    db.add_all([ra,rb,fa,fb,Bookmark(user_id=user.id, question_id=qa.id),
                Bookmark(user_id=user.id, question_id=qb.id)])
    db.commit()
    return db, user, cgl, je, qa, qb, ra, rb, fa, fb


def test_revision_and_flashcards_are_scoped_to_cgl():
    db,user,cgl,je,qa,qb,ra,rb,fa,fb=_two_exam_fixture()
    try:
        due = get_revision_queue(reason=None, limit=30, db=db, user=user)
        assert len(due)==1 and due[0]["question"]["id"]==qa.id
        bookmarks=list_bookmarks(db=db,user=user)
        assert len(bookmarks)==1 and bookmarks[0]["question"]["id"]==qa.id
        cards=due_flashcards(limit=20,db=db,user=user)
        assert len(cards)==1 and cards[0]["id"]==fa.id
        for operation in (
            lambda: add_question_to_revision(question_id=qb.id,db=db,user=user),
            lambda: toggle_bookmark(question_id=qb.id,db=db,user=user),
            lambda: review_revision_item(item_id=rb.id,success=True,db=db,user=user),
            lambda: review_flashcard(flashcard_id=fb.id,success=True,db=db,user=user),
        ):
            with pytest.raises(HTTPException) as error:
                operation()
            assert error.value.status_code==404
        db.refresh(rb)
        assert rb.successful_reviews==0
    finally:
        db.close()


def test_planner_does_not_count_other_exam_revision_or_erase_old_tasks():
    db,user,cgl,je,qa,qb,ra,rb,fa,fb=_two_exam_fixture()
    try:
        target=ExamTarget(
            user_id=user.id, exam_id=cgl.id,
            exam_date=date.today()+timedelta(days=20),
            daily_minutes=120,is_active=True,
        )
        db.add(target)
        db.commit()
        _,tasks=generate_today_plan(db,user_id=user.id)
        assert any("Clear 1 due revision" in task.title for task in tasks)
        ids={task.id for task in tasks}
        assert ids
        target.exam_id=je.id
        db.commit()
        with pytest.raises(ValueError,match="selected stage"):
            rebuild_today_plan(db,user_id=user.id)
        from app.models import DailyPlanTask
        assert {t.id for t in db.query(DailyPlanTask).filter(DailyPlanTask.user_id==user.id)}==ids
    finally:
        db.close()
