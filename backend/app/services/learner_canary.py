import json
import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.study_time import current_study_date
from app.models import Exam, ExamTarget, RevisionItem, User
from app.routers.analytics import analytics_summary
from app.routers.learn import topic_package
from app.routers.mocks import (
    active_mock,
    get_mock_state,
    review_mock,
    save_mock_response,
    start_mock,
    submit_mock,
)
from app.routers.practice import classify_mistake, submit_practice
from app.routers.revision import (
    due_flashcards,
    get_revision_queue,
    list_bookmarks,
    review_flashcard,
    review_revision_item,
    toggle_bookmark,
)
from app.schemas import MistakeUpdate, MockResponseUpdate, MockStartRequest, PracticeSubmit
from app.services.mock_engine import load_mock_attempt
from app.services.planner import generate_today_plan, rebuild_today_plan
from app.services.practice_selector import select_practice_questions


logger = logging.getLogger("uvicorn.error")


def _wrong_option(correct_option: int) -> int:
    return (correct_option % 4) + 1


def run_production_learner_canary(engine) -> dict:
    """
    Exercise the production learner loop inside an outer transaction.

    Router/service functions may call Session.commit(), but the Session is joined
    to an externally-owned transaction. The outer transaction is always rolled
    back, so no synthetic learner history persists.
    """
    connection = engine.connect()
    outer = connection.begin()
    db = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="rollback_only",
    )
    canary_email = f"phase4d-canary-{uuid4().hex}@example.invalid"

    report: dict[str, object] = {
        "status": "running",
        "practice_attempts": 0,
        "practice_correct": 0,
        "practice_incorrect": 0,
        "revision_items_created": 0,
        "mock_questions": 0,
        "mock_score": 0.0,
        "analytics_readiness": 0.0,
        "analytics_weak_topics": 0,
        "planner_tasks_initial": 0,
        "planner_tasks_rebalanced": 0,
        "rollback_verified": False,
    }

    try:
        exam = db.scalar(select(Exam).where(Exam.slug == "ssc-cgl-tier-1"))
        if not exam:
            raise RuntimeError("SSC CGL exam is not seeded")

        user = User(
            email=canary_email,
            password_hash="phase4d-canary-not-for-login",
            display_name="Phase 4D Canary",
            is_active=True,
        )
        db.add(user)
        db.flush()

        today = current_study_date()
        db.add(
            ExamTarget(
                user_id=user.id,
                exam_id=exam.id,
                exam_date=today + timedelta(days=45),
                daily_minutes=180,
                is_active=True,
            )
        )
        db.commit()

        _, initial_tasks = generate_today_plan(db, user_id=user.id, today=today)
        report["planner_tasks_initial"] = len(initial_tasks)
        if not initial_tasks:
            raise RuntimeError("Planner produced no learner tasks")

        topic_task = next((task for task in initial_tasks if task.topic_id is not None), None)
        if not topic_task or topic_task.topic_id is None:
            raise RuntimeError("Planner produced no topic-based task")

        package = topic_package(topic_task.topic_id, db=db)
        if not package["lessons"]:
            raise RuntimeError("Planner topic has no published lesson")
        report["lesson_count"] = len(package["lessons"])
        report["archetype_count"] = len(package["archetypes"])

        topic_task.status = "completed"
        db.commit()

        _, rebalanced = rebuild_today_plan(db, user_id=user.id, today=today)
        report["planner_tasks_rebalanced"] = len(rebalanced)
        if not any(task.id == topic_task.id and task.status == "completed" for task in rebalanced):
            raise RuntimeError("Planner rebalance did not preserve completed work")
        if not any(task.status == "pending" for task in rebalanced):
            raise RuntimeError("Planner rebalance produced no pending work")

        questions = select_practice_questions(
            db,
            user_id=user.id,
            topic_id=topic_task.topic_id,
            limit=10,
            mode="adaptive",
        )
        if len(questions) != 10:
            raise RuntimeError(f"Expected 10 practice questions, got {len(questions)}")

        wrong_types = ["concept", "calculation", "misread", "guess"]
        wrong_index = 0
        practice_correct = 0
        practice_incorrect = 0
        first_wrong_attempt_id = None

        for index, question in enumerate(questions):
            if question.correct_option is None:
                raise RuntimeError(f"Question {question.id} has no answer key")

            should_be_correct = index not in {2, 5, 8, 9}
            expected = float(question.expected_time_seconds or 45)
            is_slow = index in {5, 7}
            time_seconds = expected * (1.6 if is_slow else 0.75)
            confidence = 1 if index in {5, 9} else 2 if index in {2, 8} else 3

            if should_be_correct:
                selected = question.correct_option
                mistake_type = None
            else:
                selected = _wrong_option(question.correct_option)
                mistake_type = wrong_types[wrong_index]
                wrong_index += 1

            result = submit_practice(
                PracticeSubmit(
                    question_id=question.id,
                    selected_option=selected,
                    time_seconds=time_seconds,
                    confidence=confidence,
                    used_hint=index == 4,
                    mistake_type=mistake_type,
                ),
                db=db,
                user=user,
            )

            if result.correct:
                practice_correct += 1
            else:
                practice_incorrect += 1
                if first_wrong_attempt_id is None:
                    first_wrong_attempt_id = result.attempt_id

        report["practice_attempts"] = len(questions)
        report["practice_correct"] = practice_correct
        report["practice_incorrect"] = practice_incorrect
        if practice_correct != 6 or practice_incorrect != 4:
            raise RuntimeError("Practice result mix is not 6 correct / 4 incorrect")

        if first_wrong_attempt_id is not None:
            classify_mistake(
                first_wrong_attempt_id,
                MistakeUpdate(mistake_type="time_pressure"),
                db=db,
                user=user,
            )

        revision_items = list(
            db.scalars(
                select(RevisionItem)
                .where(
                    RevisionItem.user_id == user.id,
                    RevisionItem.is_active.is_(True),
                )
                .order_by(RevisionItem.id)
            )
        )
        report["revision_items_created"] = len(revision_items)
        if not revision_items:
            raise RuntimeError("Practice did not create revision items")

        revision_items[0].next_review_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        queue = get_revision_queue(limit=30, reason=None, db=db, user=user)
        if not queue:
            raise RuntimeError("Due revision queue did not surface a due item")
        revision_result = review_revision_item(
            queue[0]["id"],
            success=True,
            db=db,
            user=user,
        )
        report["revision_successful_reviews"] = revision_result["successful_reviews"]

        bookmark_result = toggle_bookmark(questions[0].id, db=db, user=user)
        if not bookmark_result["bookmarked"] or not list_bookmarks(db=db, user=user):
            raise RuntimeError("Bookmark round-trip failed")
        report["bookmark_round_trip"] = True

        cards = due_flashcards(limit=1, db=db, user=user)
        if cards:
            flashcard_result = review_flashcard(cards[0]["id"], success=True, db=db, user=user)
            report["flashcard_reviewed"] = True
            report["flashcard_successful_reviews"] = flashcard_result["successful_reviews"]
        else:
            report["flashcard_reviewed"] = False

        started = start_mock(
            MockStartRequest(mode="mini", subject_slug=None, topic_id=None),
            db=db,
            user=user,
        )
        attempt_id = started.attempt_id
        attempt, rows = load_mock_attempt(db, attempt_id=attempt_id, user_id=user.id)
        report["mock_questions"] = len(rows)
        if len(rows) != 4:
            raise RuntimeError(f"Mini mock expected 4 questions, got {len(rows)}")

        active = active_mock(db=db, user=user)
        if active["attempt_id"] != attempt_id:
            raise RuntimeError("Active mock resume state did not match canary attempt")

        for index, (row, question) in enumerate(rows):
            if question.correct_option is None:
                raise RuntimeError(f"Mock question {question.id} has no answer key")
            selected = question.correct_option if index < 3 else _wrong_option(question.correct_option)
            save_mock_response(
                attempt_id,
                MockResponseUpdate(
                    question_id=question.id,
                    selected_option=selected,
                    marked_for_review=index == 1,
                    time_seconds=float(question.expected_time_seconds or 30),
                ),
                db=db,
                user=user,
            )

        state = get_mock_state(attempt_id, db=db, user=user)
        if len(state["responses"]) != 4:
            raise RuntimeError("Mock autosave/state did not retain all responses")

        submitted = submit_mock(attempt_id, db=db, user=user)
        report["mock_score"] = float(submitted.score)
        report["mock_correct"] = submitted.correct
        report["mock_incorrect"] = submitted.incorrect
        review = review_mock(attempt_id, db=db, user=user)
        report["mock_sections"] = len(review["sections"])
        if submitted.correct != 3 or submitted.incorrect != 1:
            raise RuntimeError("Mini mock result mix is not 3 correct / 1 incorrect")

        analytics = analytics_summary(db=db, user=user)
        overview = analytics["overview"]
        report["analytics_readiness"] = overview["readiness"]
        report["analytics_accuracy"] = overview["accuracy"]
        report["analytics_mock_accuracy"] = overview["mock_accuracy"]
        report["analytics_weak_topics"] = len(analytics["weak_topics"])
        report["analytics_next_actions"] = len(analytics["next_actions"])
        if overview["practice_attempts"] != 10:
            raise RuntimeError("Analytics did not record all 10 practice attempts")
        if not analytics["recent_mocks"]:
            raise RuntimeError("Analytics did not include the submitted mini mock")
        if not analytics["weak_topics"]:
            raise RuntimeError("Analytics did not produce a weakness map")

        _, adapted_plan = rebuild_today_plan(db, user_id=user.id, today=today)
        topic_ids = {task.topic_id for task in adapted_plan if task.topic_id is not None}
        report["planner_adapted_to_practice_topic"] = topic_task.topic_id in topic_ids
        if topic_task.topic_id not in topic_ids:
            raise RuntimeError("Planner did not keep the practised weak topic in the adaptive plan")

        report["status"] = "passed"
        return report
    finally:
        db.close()
        if outer.is_active:
            outer.rollback()
        connection.close()

        verify = Session(bind=engine)
        try:
            persisted = verify.scalar(select(User).where(User.email == canary_email))
            report["rollback_verified"] = persisted is None
            if persisted is not None:
                logger.error(
                    "PHASE4D_LEARNER_CANARY_ROLLBACK_FAILED %s",
                    json.dumps({"email_present": True}, separators=(",", ":"), sort_keys=True),
                )
        finally:
            verify.close()
