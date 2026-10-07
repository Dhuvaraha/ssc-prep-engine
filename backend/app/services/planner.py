from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.study_time import current_study_date
from app.models import DailyPlanTask, Exam, ExamTarget, MockAttempt, RevisionItem, Subject, Topic, TopicMastery


def _days_until(target: date, today: date) -> int:
    return max(0, (target - today).days)


def _find_subject_slug(db: Session, topic: Topic) -> str | None:
    subject = db.get(Subject, topic.subject_id)
    return subject.slug if subject else None


def _sprint_stage(days_left: int) -> str:
    if days_left <= 0:
        return "exam_day"
    if days_left == 1:
        return "final_day"
    if days_left <= 3:
        return "test_and_repair"
    if days_left <= 5:
        return "consolidate"
    sprint_stage = _sprint_stage(days_left)
    submitted_full_mocks = _submitted_full_mock_count(
        db,
        user_id=user_id,
        exam_id=target.exam_id,
    )

    if sprint_stage == "exam_day":
        if due_revision:
            add_task(
                "revision",
                "Exam-day recall: due mistakes and marked questions",
                25,
                target_questions=min(due_revision, 15),
                priority=5,
            )
        add_task("flashcards", "Formula, vocabulary & GK rapid recall", 25, priority=5)
        if topics:
            add_task(
                "practice",
                f"Confidence warm-up: {topics[0].name}",
                20,
                topic=topics[0],
                target_questions=10,
                priority=4,
            )
    elif sprint_stage == "final_day":
        if topics:
            add_task(
                "practice",
                f"Final weak-area repair: {topics[0].name}",
                30,
                topic=topics[0],
                target_questions=15,
                priority=5,
            )
        add_task("revision", "Final error-log revision", 40, target_questions=20, priority=5)
        add_task("mock", "15-minute confidence sectional + review", 30, priority=4)
        add_task("flashcards", "Formula, vocabulary & GK rapid recall", 30, priority=5)
    elif sprint_stage == "test_and_repair":
        if target.daily_minutes >= 180:
            add_task("mock", "Full Tier-I simulation + immediate error review", 80, priority=5)
        else:
            add_task("mock", "15-minute sectional test + error review", 30, priority=5)
        if topics:
            add_task(
                "practice",
                f"Repair weakest evidence: {topics[0].name}",
                35,
                topic=topics[0],
                target_questions=20,
                priority=5,
            )
        if len(topics) > 1:
            add_task(
                "practice",
                f"Timed accuracy drill: {topics[1].name}",
                25,
                topic=topics[1],
                target_questions=15,
                priority=4,
            )
        add_task("revision", "Wrong, slow and guessed-question revision", 35, target_questions=20, priority=5)
        add_task("flashcards", "Formula, vocabulary & GK active recall", 20, priority=4)
    elif sprint_stage == "consolidate":
        if topics:
            first_label = "Targeted concept repair" if topics[0].id in evidence_topic_ids else "Finish priority concept"
            add_task(
                "learn",
                f"{first_label}: {topics[0].name}",
                20,
                topic=topics[0],
                priority=5,
            )
            add_task(
                "practice",
                f"Guided-to-timed practice: {topics[0].name}",
                30,
                topic=topics[0],
                target_questions=20,
                priority=5,
            )
        if target.daily_minutes >= 180 and (submitted_full_mocks == 0 or days_left == 4):
            add_task("mock", "Full Tier-I simulation + error review", 80, priority=5)
        else:
            add_task("mock", "25Q sectional test + error review", 35, priority=5)
        if len(topics) > 1:
            add_task(
                "practice",
                f"{practice_label(topics[1])}: {topics[1].name}",
                25,
                topic=topics[1],
                target_questions=15,
                priority=4,
            )
        add_task("flashcards", "Formula, vocabulary & GK active recall", 20, priority=4)
    elif sprint_stage == "coverage":
        if topics:
            add_task(
                "learn",
                f"Learn & revise {topics[0].name}",
                30,
                topic=topics[0],
                priority=5,
            )
            add_task(
                "practice",
                f"Guided practice: {topics[0].name}",
                30,
                topic=topics[0],
                target_questions=20,
                priority=5,
            )
        if len(topics) > 1:
            add_task(
                "practice",
                f"{practice_label(topics[1])}: {topics[1].name}",
                25,
                topic=topics[1],
                target_questions=15,
                priority=5,
            )
        add_task("mock", "25Q sectional test + error review", 35, priority=4)
        if len(topics) > 2:
            add_task(
                "practice",
                f"Reinforce {topics[2].name}",
                25,
                topic=topics[2],
                target_questions=15,
                priority=4,
            )
        add_task("flashcards", "Formula, vocabulary & GK active recall", 20, priority=4)
    else:
        if topics:
            add_task(
                "learn",
                f"Learn & revise {topics[0].name}",
                25,
                topic=topics[0],
                priority=4,
            )
            add_task(
                "practice",
                f"Targeted practice: {topics[0].name}",
                30,
                topic=topics[0],
                target_questions=20,
                priority=5,
            )
        if len(topics) > 1:
            add_task(
                "practice",
                f"{practice_label(topics[1])}: {topics[1].name}",
                25,
                topic=topics[1],
                target_questions=15,
                priority=4,
            )
        if target.daily_minutes >= 120:
            add_task("mock", "Quick timed test + mistake review", 30, priority=4)
        if len(topics) > 2:
            add_task(
                "practice",
                f"Reinforce {topics[2].name}",
                25,
                topic=topics[2],
                target_questions=15,
                priority=3,
            )
        add_task("flashcards", "Formula, vocabulary & GK active recall", 20, priority=3)

    # Fill the learner's declared study budget instead of silently leaving large
    # unused gaps. Extra blocks stay actionable and rotate through priority topics.
    rotation = topics or []
    rotation_index = 0
    while minutes_left >= 20:
        topic = rotation[rotation_index % len(rotation)] if rotation else None
        if topic is not None:
            add_task(
                "practice",
                f"Mixed reinforcement: {topic.name}",
                min(25, minutes_left),
                topic=topic,
                target_questions=15,
                priority=3,
            )
            rotation_index += 1
        else:
            add_task(
                "practice",
                "Mixed syllabus reinforcement",
                min(25, minutes_left),
                target_questions=15,
                priority=3,
            )

    if minutes_left >= 10:
        add_task(
            "flashcards",
            "Rapid recall finish",
            minutes_left,
            priority=2,
        )

    db.commit()
    for task in tasks:
        db.refresh(task)
    return target, tasks


def rebuild_today_plan(db: Session, *, user_id: int, today: date | None = None):
    today = today or current_study_date()
    tasks = list(
        db.scalars(
            select(DailyPlanTask).where(
                DailyPlanTask.user_id == user_id,
                DailyPlanTask.plan_date == today,
                DailyPlanTask.status == "pending",
            )
        )
    )
    for task in tasks:
        db.delete(task)
    db.commit()
    return generate_today_plan(db, user_id=user_id, today=today, rebalance=True)
