from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import DailyPlanTask, User
from app.services.planner import ensure_exam_target, generate_today_plan, rebuild_today_plan

router = APIRouter(prefix="/planner", tags=["planner"])


def _task_outcome(task: DailyPlanTask) -> str:
    if task.activity_type == "learn":
        return "Understand the rule and recognition cues before attempting the drill."
    if task.activity_type == "practice":
        return f"Complete {task.target_questions or 10} focused questions and improve mastery."
    if task.activity_type == "revision":
        return "Recall the correct method without repeating the previous mistake."
    if task.activity_type == "flashcards":
        return "Finish due recall cards and push remembered facts to the next interval."
    if task.activity_type == "mock":
        return "Measure exam-speed accuracy and expose marks lost under time pressure."
    return "Move today's preparation target forward."


def _task_reason(task: DailyPlanTask) -> str:
    if task.activity_type == "revision":
        return "Due from a previous wrong, slow or low-confidence attempt."
    if task.activity_type == "flashcards":
        return "Spaced recall is due today, so this protects memory before it fades."
    if task.activity_type == "mock":
        return "Exam simulation is scheduled to measure speed, attempt rate and accuracy."
    if task.activity_type == "learn":
        return "Concept-first study was prioritised before more questions from this topic."
    if task.activity_type == "practice":
        if task.priority >= 5:
            return "High-priority or weak-topic practice was selected by the adaptive planner."
        return "Practice was selected to strengthen mastery and keep the topic active."
    return "This task fits today's available study time and preparation priority."


class PlannerConfig(BaseModel):
    exam_slug: str = "ssc-cgl-tier-1"
    exam_date: date
    daily_minutes: int = Field(default=180, ge=45, le=720)

    @field_validator("exam_date")
    @classmethod
    def validate_exam_date(cls, value: date) -> date:
        if value < date.today():
            raise ValueError("Exam date cannot be in the past")
        return value


def _serialize(target, tasks):
    today = date.today()
    days_left = max(0, (target.exam_date - today).days)
    completed_minutes = sum(task.target_minutes for task in tasks if task.status == "completed")
    total_minutes = sum(task.target_minutes for task in tasks)
    return {
        "target": {
            "exam_id": target.exam_id,
            "exam_date": target.exam_date.isoformat(),
            "daily_minutes": target.daily_minutes,
            "days_left": days_left,
        },
        "progress": {
            "completed_minutes": completed_minutes,
            "planned_minutes": total_minutes,
            "completed_tasks": sum(task.status == "completed" for task in tasks),
            "total_tasks": len(tasks),
        },
        "tasks": [
            {
                "id": task.id,
                "activity_type": task.activity_type,
                "subject_slug": task.subject_slug,
                "topic_id": task.topic_id,
                "title": task.title,
                "target_minutes": task.target_minutes,
                "target_questions": task.target_questions,
                "priority": task.priority,
                "status": task.status,
                "reason": _task_reason(task),
                "expected_outcome": _task_outcome(task),
            }
            for task in tasks
        ],
    }


@router.put("/config")
def set_planner_config(
    payload: PlannerConfig,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        target = ensure_exam_target(
            db,
            user_id=user.id,
            exam_slug=payload.exam_slug,
            exam_date=payload.exam_date,
            daily_minutes=payload.daily_minutes,
        )
        target, tasks = rebuild_today_plan(db, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _serialize(target, tasks)


@router.get("/today")
def today_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        target, tasks = generate_today_plan(db, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize(target, tasks)


@router.post("/today/rebuild")
def rebuild_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        target, tasks = rebuild_today_plan(db, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return _serialize(target, tasks)


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: int,
    completed: bool,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    task = db.get(DailyPlanTask, task_id)
    if not task or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Plan task not found")
    task.status = "completed" if completed else "pending"
    db.commit()
    return {"id": task.id, "status": task.status}
