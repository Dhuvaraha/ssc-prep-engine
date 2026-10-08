"""Verified option insights must never leak before an actual submission."""
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Exam, Question, QuestionOption, QuestionOptionInsight,
    Subject, Topic, User,
)
from app.routers.practice import get_practice_questions, submit_practice
from app.schemas import PracticeSubmit
from app.services.option_insights import published_option_insights


def _fixture():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    user = User(email="option-review@example.com", password_hash="x")
    cgl = Exam(slug="ssc-cgl-tier-1", name="SSC CGL", duration_minutes=60)
    other = Exam(slug="ssc-je-telecom-paper-1", name="JE Telecom", duration_minutes=120)
    db.add_all([user, cgl, other])
    db.flush()
    s1 = Subject(exam_id=cgl.id, slug="general-awareness", name="GA")
    s2 = Subject(exam_id=other.id, slug="telecom-technical", name="JE Technical")
    db.add_all([s1, s2])
    db.flush()
    t1 = Topic(subject_id=s1.id, slug="history", name="History")
    t2 = Topic(subject_id=s2.id, slug="circuits", name="Circuits")
    db.add_all([t1, t2])
    db.flush()
    question = Question(exam_id=cgl.id, subject_id=s1.id, topic_id=t1.id,
                        question_text="A sample verified question?",
                        correct_option=1, explanation="Use the verified answer.",
                        verification_status="verified")
    je_question = Question(exam_id=other.id, subject_id=s2.id, topic_id=t2.id,
                           question_text="A JE technical question?",
                           correct_option=1, verification_status="verified")
    db.add_all([question, je_question])
    db.flush()
    for position in (1, 2, 3, 4):
        db.add(QuestionOption(question_id=question.id, position=position, text=f"Choice {position}"))
    db.add(QuestionOption(question_id=je_question.id, position=1, text="Technical answer"))
    db.flush()
    return db, user, question, je_question


def test_only_published_reviewed_wrong_option_insight_is_returned_after_answer():
    db, user, question, _ = _fixture()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        db.add_all([
            QuestionOptionInsight(
                question_id=question.id, option_position=2,
                insight_type="fact", knowledge_text="A reviewed historical fact.",
                related_question="What was Choice 2 historically associated with?",
                related_answer="An independently checked context.",
                source_reference="Official reference 1", source_year=2026,
                review_status="published", reviewed_at=now,
            ),
            QuestionOptionInsight(
                question_id=question.id, option_position=3,
                insight_type="fact", knowledge_text="An unpublished claim.",
                source_reference="Draft reviewer", review_status="draft", reviewed_at=now,
            ),
            QuestionOptionInsight(
                question_id=question.id, option_position=4,
                insight_type="fact", knowledge_text="Not reviewed yet.",
                source_reference="Reference", review_status="published", reviewed_at=None,
            ),
            QuestionOptionInsight(
                question_id=question.id, option_position=1,
                insight_type="fact", knowledge_text="Correct-option duplicate.",
                source_reference="Reference", review_status="published", reviewed_at=now,
            ),
        ])
        db.commit()

        # Practice list is an unaudited question attempt, NOT post-answer review.
        questions = get_practice_questions(topic_id=question.topic_id, limit=10,
            mode="guided", similar_to=None, db=db, user=user)
        assert any(q.id == question.id for q in questions)
        assert "option_insights" not in questions[0].__dict__

        answer = submit_practice(PracticeSubmit(
            question_id=question.id, selected_option=2,
            confidence=3, used_hint=False, time_seconds=30,
        ), db=db, user=user)
        assert answer.correct is False
        assert len(answer.option_insights) == 1
        insight = answer.option_insights[0]
        assert insight["position"] == 2
        assert insight["source_reference"] == "Official reference 1"
        assert "historical fact" in insight["knowledge_text"]
        assert insight["related_question"] is not None
    finally:
        db.close()


def test_unreviewed_or_unsourced_records_do_not_publish_even_with_wrong_flag():
    db, user, question, _ = _fixture()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    try:
        db.add(QuestionOptionInsight(
            question_id=question.id, option_position=2, insight_type="fact",
            knowledge_text="Unverified content", source_reference=" ",
            review_status="published", reviewed_at=now,
        ))
        db.commit()
        assert published_option_insights(db, question=question) == []
        response = submit_practice(PracticeSubmit(
            question_id=question.id, selected_option=1,
            confidence=3, used_hint=False, time_seconds=20,
        ), db=db, user=user)
        assert response.option_insights == []
    finally:
        db.close()


def test_je_options_cannot_be_retrieved_with_cgl_focus():
    db, user, _, je_question = _fixture()
    try:
        with pytest.raises(HTTPException) as error:
            submit_practice(PracticeSubmit(
                question_id=je_question.id, selected_option=1,
                confidence=2, used_hint=False, time_seconds=20,
            ), db=db, user=user)
        assert error.value.status_code == 404
    finally:
        db.close()
