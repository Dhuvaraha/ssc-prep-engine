"""Request-scoped authorization, applied in SQL before ranking and LIMIT.

Only learner request sessions are scoped. Offline import/review tools do not
silently acquire learner permissions. Never run raw SQL in scoped handlers.
"""
from fastapi import Depends, HTTPException, Request
from sqlalchemy import and_, event, exists, or_, select
from sqlalchemy.orm import Session, with_loader_criteria

from app.access_models import AssessmentAsset, ContentBinding, ContentSource, CourseGrant, SourceGrant
from app.db import get_db
from app.deps import get_current_user
from app.models import Flashcard, Lesson, LessonBlock, MockAttempt, Question, QuestionArchetype, QuestionOption, Subject, Topic, User
from app.services.exam_scope import current_exam


def permitted_resource(kind, resource_id, exam_id, user_id, public=False):
    binding = ContentBinding.__table__.alias()
    source = ContentSource.__table__.alias()
    grant = SourceGrant.__table__.alias()
    permitted_source = or_(
        and_(public, source.c.public_use_approved.is_(True)),
        and_(source.c.private_use_approved.is_(True), exists(
            select(1).select_from(grant).where(
                grant.c.user_id == user_id, grant.c.source_id == source.c.id,
                grant.c.active.is_(True),
            )
        )),
    )
    matching = and_(binding.c.resource_kind == kind, binding.c.resource_id == resource_id)
    present = exists(select(1).select_from(binding).where(matching))
    denied = exists(select(1).select_from(binding.outerjoin(source, source.c.id == binding.c.source_id)).where(
        matching, or_(source.c.id.is_(None), source.c.exam_id != exam_id, ~permitted_source),
    ))
    return and_(present, ~denied)


def question_policy(user_id, exam_id):
    q = Question
    subjects = Subject.__table__
    topics = Topic.__table__
    return and_(
        q.exam_id == exam_id,
        q.visibility.in_(["private", "public"]),
        exists(select(1).select_from(subjects).where(subjects.c.id == q.subject_id, subjects.c.exam_id == exam_id)),
        or_(q.topic_id.is_(None), exists(select(1).select_from(topics).where(
            topics.c.id == q.topic_id, topics.c.subject_id == q.subject_id,
        ))),
        permitted_resource("question", q.id, exam_id, user_id, q.visibility == "public"),
    )


def topic_in_exam(topic_id, exam_id):
    t, s = Topic.__table__, Subject.__table__
    return exists(select(1).select_from(t.join(s, t.c.subject_id == s.c.id)).where(t.c.id == topic_id, s.c.exam_id == exam_id))


@event.listens_for(Session, "do_orm_execute")
def apply_content_scope(state):
    scope = state.session.info.get("content_scope")
    if not scope or not state.is_select:
        return
    user_id, exam_id = scope
    policies = [(Question, question_policy(user_id, exam_id))]
    if state.session.info.get("assessment_selection"):
        safe_images = select("private://" + AssessmentAsset.asset_key)
        options = QuestionOption.__table__
        safe = and_(
            or_(Question.question_image_url.is_(None), Question.question_image_url.in_(safe_images)),
            ~exists(select(1).select_from(options).where(options.c.question_id == Question.id,
                options.c.image_url.is_not(None), options.c.image_url.not_in(safe_images))),
        )
        policies.append((Question, safe))
    for model, kind in ((Lesson, "lesson"), (QuestionArchetype, "archetype"), (Flashcard, "flashcard")):
        policies.append((model, and_(topic_in_exam(model.topic_id, exam_id), permitted_resource(kind, model.id, exam_id, user_id))))
    # Subqueries use Core tables to avoid recursively applying ORM criteria.
    q = Question.__table__
    allowed_q = select(q.c.id).where(question_policy(user_id, exam_id))
    policies.append((QuestionOption, QuestionOption.question_id.in_(allowed_q)))
    l = Lesson.__table__
    allowed_l = select(l.c.id).where(topic_in_exam(l.c.topic_id, exam_id), permitted_resource("lesson", l.c.id, exam_id, user_id))
    policies.append((LessonBlock, LessonBlock.lesson_id.in_(allowed_l)))
    for model, predicate in policies:
        state.statement = state.statement.options(with_loader_criteria(model, predicate, include_aliases=True))


def lock_learner(db: Session, user_id: int):
    # Common PostgreSQL row lock serializes start, submit, assistance and grants.
    db.execute(select(User.id).where(User.id == user_id).with_for_update()).one()


def require_no_assessment(db: Session, user_id: int):
    active = db.scalar(select(MockAttempt.id).where(MockAttempt.user_id == user_id, MockAttempt.status == "in_progress").limit(1))
    if active is not None:
        raise HTTPException(409, "ASSESSMENT_IN_PROGRESS")


def content_user(request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> User:
    lock_learner(db, user.id)
    exam = current_exam(db, user_id=user.id)
    grant = db.get(CourseGrant, (user.id, exam.id))
    if not grant or not grant.active:
        raise HTTPException(404, "Content not available")
    db.info["content_scope"] = (user.id, exam.id)
    db.info["assessment_selection"] = request.url.path.endswith("/mocks/start")
    return user


def teaching_user(db: Session = Depends(get_db), user: User = Depends(content_user)) -> User:
    require_no_assessment(db, user.id)
    return user
