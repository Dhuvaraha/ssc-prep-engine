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
    if days_left <= 7:
        return "coverage"
    return "normal"


def _submitted_full_mock_count(db: Session, *, user_id: int, exam_id: int) -> int:
    return int(
        db.scalar(
            select(func.count(MockAttempt.id)).where(
                MockAttempt.user_id == user_id,
                MockAttempt.exam_id == exam_id,
                MockAttempt.mode == "full",
                MockAttempt.status == "submitted",
            )
        )
        or 0
    )


def ensure_exam_target(
    db: Session,
    *,
    user_id: int,
    exam_slug: str,
    exam_date: date,
    daily_minutes: int,
) -> ExamTarget:
    exam = db.scalar(select(Exam).where(Exam.slug == exam_slug))
    if not exam:
        raise ValueError("Exam not found")

    target = db.scalar(
        select(ExamTarget).where(
            ExamTarget.user_id == user_id,
            ExamTarget.exam_id == exam.id,
            ExamTarget.is_active.is_(True),
        )
    )
    if not target:
        target = ExamTarget(
            user_id=user_id,
            exam_id=exam.id,
            exam_date=exam_date,
            daily_minutes=daily_minutes,
            is_active=True,
        )
        db.add(target)
    else:
        target.exam_date = exam_date
        target.daily_minutes = daily_minutes
    db.commit()
    db.refresh(target)
    return target


def get_active_target(db: Session, *, user_id: int) -> ExamTarget | None:
    return db.scalar(
        select(ExamTarget)
        .where(
            ExamTarget.user_id == user_id,
            ExamTarget.is_active.is_(True),
        )
        .order_by(ExamTarget.id.desc())
    )


def days_until_active_exam(
    db: Session,
    *,
    user_id: int,
    today: date | None = None,
) -> int | None:
    target = get_active_target(db, user_id=user_id)
    if not target:
        return None
    return _days_until(target.exam_date, today or current_study_date())


def _pick_topics(
    db: Session,
    *,
    user_id: int,
    exam_id: int,
    limit: int = 4,
) -> list[Topic]:
    exam_topic_ids = select(Topic.id).join(Subject, Subject.id == Topic.subject_id).where(
        Subject.exam_id == exam_id
    )
    mastery_rows = list(
        db.scalars(
            select(TopicMastery)
            .where(
                TopicMastery.user_id == user_id,
                TopicMastery.topic_id.in_(exam_topic_ids),
                TopicMastery.attempts > 0,
            )
            .order_by(TopicMastery.mastery_score.asc(), TopicMastery.updated_at.asc())
            .limit(limit)
        )
    )
    topics: list[Topic] = []
    for row in mastery_rows:
        topic = db.get(Topic, row.topic_id)
        if topic:
            topics.append(topic)

    if len(topics) < limit:
        existing = {topic.id for topic in topics}
        extras_stmt = (
            select(Topic)
            .join(Subject, Subject.id == Topic.subject_id)
            .where(Subject.exam_id == exam_id)
        )
        if existing:
            extras_stmt = extras_stmt.where(Topic.id.not_in(existing))
        extras = list(
            db.scalars(
                extras_stmt
                .order_by(Topic.priority.desc(), Topic.id.asc())
                .limit(limit - len(topics))
            )
        )
        topics.extend(extras)

    return topics[:limit]


def generate_today_plan(
    db: Session,
    *,
    user_id: int,
    today: date | None = None,
    rebalance: bool = False,
) -> tuple[ExamTarget, list[DailyPlanTask]]:
    today = today or current_study_date()
    target = get_active_target(db, user_id=user_id)
    if not target:
        raise ValueError("Set an exam target first")

    existing = list(
        db.scalars(
            select(DailyPlanTask)
            .where(
                DailyPlanTask.user_id == user_id,
                DailyPlanTask.plan_date == today,
            )
            .order_by(DailyPlanTask.id.asc())
        )
    )
    if existing and not rebalance:
        return target, existing

    completed_tasks = [task for task in existing if task.status == "completed"]
    tasks: list[DailyPlanTask] = list(completed_tasks)
    completed_minutes = sum(task.target_minutes for task in completed_tasks)
    minutes_left = max(0, target.daily_minutes - completed_minutes) if rebalance else max(45, target.daily_minutes)
    days_left = _days_until(target.exam_date, today)

    due_revision = db.scalar(
        select(func.count(RevisionItem.id)).where(
            RevisionItem.user_id == user_id,
            RevisionItem.is_active.is_(True),
            RevisionItem.next_review_at <= datetime.combine(today, datetime.max.time()),
        )
    ) or 0

    evidence_topic_ids = set(
        db.scalars(
            select(TopicMastery.topic_id).where(
                TopicMastery.user_id == user_id,
                TopicMastery.attempts > 0,
            )
        )
    )

    def add_task(
        activity_type: str,
        title: str,
        minutes: int,
        *,
        topic: Topic | None = None,
        target_questions: int | None = None,
        priority: int = 3,
    ) -> None:
        nonlocal minutes_left
        if minutes_left <= 0:
            return
        minutes = min(minutes, minutes_left)
        if minutes < 10:
            return
        task = DailyPlanTask(
            user_id=user_id,
            plan_date=today,
            activity_type=activity_type,
            subject_slug=_find_subject_slug(db, topic) if topic else None,
            topic_id=topic.id if topic else None,
            title=title,
            target_minutes=minutes,
            target_questions=target_questions,
            priority=priority,
        )
        db.add(task)
        tasks.append(task)
        minutes_left -= minutes

    if due_revision:
        add_task(
            "revision",
            f"Clear {min(due_revision, 20)} due revision items",
            25 if days_left > 3 else 35,
            target_questions=min(due_revision, 20),
            priority=5,
        )

    topics = _pick_topics(db, user_id=user_id, exam_id=target.exam_id, limit=4)

    def practice_label(topic: Topic) -> str:
        return "Weak-topic practice" if topic.id in evidence_topic_ids else "Priority practice"

    sprint_stage = _sprint_stage(days_left)
    submitted_full_mocks = _submitted_full_mock_count(db, user_id=user_id, exam_id=target.exam_id)

    if sprint_stage == "exam_day":
        if due_revision:
            add_task("revision", "Exam-day recall: due mistakes and marked questions", 25, target_questions=min(due_revision, 15), priority=5)
        add_task("flashcards", "Formula, vocabulary & GK rapid recall", 25, priority=5)
        if topics:
            add_task("practice", f"Confidence warm-up: {topics[0].name}", 20, topic=topics[0], target_questions=10, priority=4)
    elif sprint_stage == "final_day":
        if topics:
            add_task("practice", f"Final weak-area repair: {topics[0].name}", 30, topic=topics[0], target_questions=15, priority=5)
        add_task("revision", "Final error-log revision", 40, target_questions=20, priority=5)
        add_task("mock", "15-minute confidence sectional + review", 30, priority=4)
        add_task("flashcards", "Formula, vocabulary & GK rapid recall", 30, priority=5)
    elif sprint_stage == "test_and_repair":
        add_task("mock", "Full Tier-I simulation + immediate error review" if target.daily_minutes >= 180 else "15-minute sectional test + error review", 80 if target.daily_minutes >= 180 else 30, priority=5)
        if topics:
            add_task("practice", f"Repair weakest evidence: {topics[0].name}", 35, topic=topics[0], target_questions=20, priority=5)
        if len(topics) > 1:
            add_task("practice", f"Timed accuracy drill: {topics[1].name}", 25, topic=topics[1], target_questions=15, priority=4)
        add_task("revision", "Wrong, slow and guessed-question revision", 35, target_questions=20, priority=5)
        add_task("flashcards", "Formula, vocabulary & GK active recall", 20, priority=4)
    elif sprint_stage == "consolidate":
        if topics:
            first_label = "Targeted concept repair" if topics[0].id in evidence_topic_ids else "Finish priority concept"
            add_task("learn", f"{first_label}: {topics[0].name}", 20, topic=topics[0], priority=5)
            add_task("practice", f"Guided-to-timed practice: {topics[0].name}", 30, topic=topics[0], target_questions=20, priority=5)
        if target.daily_minutes >= 180 and (submitted_full_mocks == 0 or days_left == 4):
            add_task("mock", "Full Tier-I simulation + error review", 80, priority=5)
        else:
            add_task("mock", "25Q sectional test + error review", 35, priority=5)
        if len(topics) > 1:
            add_task("practice", f"{practice_label(topics[1])}: {topics[1].name}", 25, topic=topics[1], target_questions=15, priority=4)
        add_task("flashcards", "Formula, vocabulary & GK active recall", 20, priority=4)
    elif sprint_stage == "coverage":
        if topics:
            add_task("learn", f"Learn & revise {topics[0].name}", 30, topic=topics[0], priority=5)
            add_task("practice", f"Guided practice: {topics[0].name}", 30, topic=topics[0], target_questions=20, priority=5)
        if len(topics) > 1:
            add_task("practice", f"{practice_label(topics[1])}: {topics[1].name}", 25, topic=topics[1], target_questions=15, priority=5)
        add_task("mock", "25Q sectional test + error review", 35, priority=4)
        if len(topics) > 2:
            add_task("practice", f"Reinforce {topics[2].name}", 25, topic=topics[2], target_questions=15, priority=4)
        add_task("flashcards", "Formula, vocabulary & GK active recall", 20, priority=4)
    else:
        if topics:
            add_task("learn", f"Learn & revise {topics[0].name}", 25, topic=topics[0], priority=4)
            add_task("practice", f"Targeted practice: {topics[0].name}", 30, topic=topics[0], target_questions=20, priority=5)
        if len(topics) > 1:
            add_task("practice", f"{practice_label(topics[1])}: {topics[1].name}", 25, topic=topics[1], target_questions=15, priority=4)
        if target.daily_minutes >= 120:
            add_task("mock", "Quick timed test + mistake review", 30, priority=4)
        if len(topics) > 2:
            add_task("practice", f"Reinforce {topics[2].name}", 25, topic=topics[2], target_questions=15, priority=3)
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
