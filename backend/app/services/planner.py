from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.study_time import current_study_date
from app.models import DailyPlanTask, Exam, ExamTarget, RevisionItem, Subject, Topic, TopicMastery


def _days_until(target: date, today: date) -> int:
    return max(0, (target - today).days)


def _find_subject_slug(db: Session, topic: Topic) -> str | None:
    subject = db.get(Subject, topic.subject_id)
    return subject.slug if subject else None


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
    limit: int = 3,
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
            .order_by(DailyPlanTask.priority.desc(), DailyPlanTask.id.asc())
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

    topics = _pick_topics(db, user_id=user_id, exam_id=target.exam_id, limit=3)

    if days_left <= 3:
        for topic in topics[:2]:
            add_task(
                "practice",
                f"Final sprint: {topic.name}",
                25,
                topic=topic,
                target_questions=15,
                priority=5,
            )
        add_task("mock", "Timed mini/full mock + error review", 45, priority=5)
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
                f"Second weak area: {topics[1].name}",
                25,
                topic=topics[1],
                target_questions=15,
                priority=4,
            )
        if target.daily_minutes >= 120:
            add_task("mock", "Mini mock and mistake review", 30, priority=4)

    if minutes_left >= 15:
        add_task(
            "flashcards",
            "Formula, vocabulary & GK flashcard recall",
            min(20, minutes_left),
            priority=3,
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
