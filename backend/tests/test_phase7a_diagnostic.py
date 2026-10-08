"""Phase 7A diagnostic: strict exam sample, safe persistence, honest baseline."""
from collections import Counter
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    Exam, Question, QuestionOption, Subject, Topic, User,
)
from app.routers.analytics import analytics_summary
from app.routers.diagnostics import diagnostic_baseline
from app.routers.mocks import get_mock, get_mock_state, review_mock, save_mock_response, start_mock, submit_mock
from app.schemas import MockResponseUpdate, MockStartRequest
from app.services.mock_engine import create_mock_attempt, load_mock_attempt, submit_mock_attempt


SLUGS = ("reasoning", "general-awareness", "quant", "english")


def seeded(diagnostics_per_difficulty=2):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    learner = User(email="diagnostic-learner@example.com", password_hash="test")
    other = User(email="other-diagnostic@example.com", password_hash="test")
    exam = Exam(slug="ssc-cgl-tier-1", name="CGL Tier I",
                duration_minutes=60, positive_marks=2, negative_marks=.5)
    db.add_all([learner, other, exam])
    db.flush()
    for slug in SLUGS:
        subject = Subject(exam_id=exam.id, name=slug, slug=slug)
        db.add(subject)
        db.flush()
        topics = []
        for idx in range(15):
            topic = Topic(subject_id=subject.id, name=f"{slug} topic {idx}", slug=f"{slug}-{idx}")
            db.add(topic)
            topics.append(topic)
        db.flush()
        for difficulty, quota in ((1, 3), (2, 5), (3, 2)):
            for idx in range(quota * diagnostics_per_difficulty):
                topic = topics[idx % len(topics)]
                question = Question(
                    exam_id=exam.id, subject_id=subject.id, topic_id=topic.id,
                    pattern_type=f"pattern-{idx % 5}",
                    question_text=f"{slug} difficulty {difficulty} question {idx}",
                    correct_option=1, verification_status="verified",
                    difficulty=difficulty, requires_visual_review=False,
                    explanation="A fully verified explanation for the diagnostic.",
                )
                db.add(question)
                db.flush()
                for position in range(1, 5):
                    db.add(QuestionOption(
                        question_id=question.id, position=position,
                        text=f"{question.question_text} option {position}",
                    ))
    db.commit()
    return db, learner, other, exam


def test_exact_40_question_24_minute_blueprint_without_answer_leak():
    db, user, _, exam = seeded()
    try:
        response = start_mock(
            payload=MockStartRequest(mode="diagnostic"),
            db=db, user=user,
        )
        assert response.mode == "diagnostic"
        assert response.duration_minutes == 24
        assert response.resumed_existing is False
        assert len(response.questions) == 40
        assert len({q.question.id for q in response.questions}) == 40
        assert Counter(q.section_slug for q in response.questions) == {
            slug: 10 for slug in SLUGS
        }
        counts = Counter((q.section_slug, q.question.difficulty) for q in response.questions)
        for slug in SLUGS:
            assert [counts[(slug, level)] for level in (1, 2, 3)] == [3, 5, 2]
        assert all(len(q.question.options) == 4 for q in response.questions)
        payloads = [q.model_dump() for q in response.questions]
        assert all("correct_option" not in q["question"] for q in payloads)
        assert all("explanation" not in q["question"] for q in payloads)

        # Starting again in another tab resumes same immutable question set.
        repeated = start_mock(payload=MockStartRequest(mode="diagnostic"), db=db, user=user)
        assert repeated.resumed_existing is True
        assert repeated.attempt_id == response.attempt_id

        with pytest.raises(HTTPException) as error:
            review_mock(attempt_id=response.attempt_id, db=db, user=user)
        assert error.value.status_code == 409
    finally:
        db.close()


def test_resume_answer_idempotency_and_server_expiry():
    db, user, other, _ = seeded()
    try:
        initial = start_mock(payload=MockStartRequest(mode="diagnostic"), db=db, user=user)
        question_id = initial.questions[0].question.id

        with pytest.raises(HTTPException) as error:
            get_mock(attempt_id=initial.attempt_id, db=db, user=other)
        assert error.value.status_code == 404

        saved = save_mock_response(
            attempt_id=initial.attempt_id,
            payload=MockResponseUpdate(question_id=question_id, selected_option=2,
                                       marked_for_review=True, time_seconds=15),
            db=db, user=user,
        )
        assert saved["selected_option"] == 2
        assert any(q["question_id"] == question_id and q["selected_option"] == 2
                   for q in get_mock_state(attempt_id=initial.attempt_id, db=db, user=user)["responses"])

        attempt, _ = load_mock_attempt(db, attempt_id=initial.attempt_id, user_id=user.id)
        attempt.started_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=25)
        db.commit()
        with pytest.raises(HTTPException) as error:
            save_mock_response(
                attempt_id=initial.attempt_id,
                payload=MockResponseUpdate(question_id=question_id, selected_option=1),
                db=db, user=user,
            )
        assert error.value.status_code == 409

        first_submit = submit_mock(attempt_id=initial.attempt_id, db=db, user=user)
        second_submit = submit_mock(attempt_id=initial.attempt_id, db=db, user=user)
        assert first_submit == second_submit
        with pytest.raises(HTTPException) as error:
            save_mock_response(
                attempt_id=initial.attempt_id,
                payload=MockResponseUpdate(question_id=question_id, selected_option=1),
                db=db, user=user,
            )
        assert error.value.status_code == 409
    finally:
        db.close()


def test_first_baseline_immutable_repeat_has_no_overlap_and_never_unlocks_exam_readiness():
    db, user, _, exam = seeded()
    try:
        empty = diagnostic_baseline(db=db, user=user)
        assert empty["status"] == "not_assessed"
        assert empty["readiness"] is None

        attempt, rows = create_mock_attempt(
            db, user_id=user.id, mode="diagnostic", subject_slug=None,
        )
        for index, (row, question) in enumerate(rows):
            # 8 attempts/subject, 32 total; a diagnostic sample, not mastery.
            if index % 10 < 8:
                row.selected_option = 1 if index % 2 == 0 else 2
        db.commit()
        submit_mock_attempt(db, attempt=attempt, rows=rows)

        first = diagnostic_baseline(db=db, user=user)
        assert first["status"] == "sampled"
        assert first["baseline"]["readiness"] is None
        assert first["baseline"]["readiness_label"] == "Not assessed"
        assert first["baseline"]["attempted_questions"] == 32
        assert first["baseline"]["correct"] == 16
        assert first["baseline"]["accuracy"] == 50.0
        assert first["baseline"]["sampled_topics"] < first["baseline"]["total_topics"]
        assert first["baseline"]["attempted_topics"] <= first["baseline"]["sampled_topics"]
        assert first["baseline"]["evidence_label"] == "initial_sample"
        assert all(x["attempted"] == 8 for x in first["baseline"]["subjects"].values())

        # The diagnostic should never silently inflate full mock or practice statistics.
        summary = analytics_summary(db=db, user=user)
        assert summary["overview"]["readiness"] is None
        assert summary["overview"]["mock_attempt_rate"] == 0
        assert summary["recent_mocks"] == []

        second_attempt, second_rows = create_mock_attempt(
            db, user_id=user.id, mode="diagnostic", subject_slug=None,
        )
        assert len(second_rows) == 40
        assert not ({q.id for _, q in rows} & {q.id for _, q in second_rows})
        for row, _ in second_rows:
            row.selected_option = 1
        db.commit()
        submit_mock_attempt(db, attempt=second_attempt, rows=second_rows)

        after = diagnostic_baseline(db=db, user=user)
        assert after["completed_diagnostics"] == 2
        assert after["baseline"]["attempt_id"] == first["baseline"]["attempt_id"]
        assert after["baseline"]["accuracy"] == first["baseline"]["accuracy"]
        assert after["latest"]["attempt_id"] == second_attempt.id
        assert after["latest"]["accuracy"] == 100.0
    finally:
        db.close()


def test_do_not_downgrade_blueprint_or_write_partial_attempt_on_missing_hard_content():
    db, user, _, exam = seeded(diagnostics_per_difficulty=1)
    try:
        hardest = db.scalars(select(Question).where(
            Question.exam_id == exam.id, Question.difficulty == 3
        )).all()
        for question in hardest:
            if question.subject_id == hardest[0].subject_id:
                db.delete(question)
        db.commit()
        with pytest.raises(ValueError, match="Insufficient verified"):
            create_mock_attempt(db, user_id=user.id, mode="diagnostic", subject_slug=None)
        from app.models import MockAttempt
        assert db.query(MockAttempt).count() == 0
    finally:
        db.close()
