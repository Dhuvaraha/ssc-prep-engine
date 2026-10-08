from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SourceType(StrEnum):
    OFFICIAL = "official"
    LICENSED = "licensed"
    USER_PRIVATE = "user_private"
    ORIGINAL = "original"
    GENERATED = "generated"


class VerificationStatus(StrEnum):
    RAW = "raw"
    PARSED = "parsed"
    REVIEW_REQUIRED = "review_required"
    VERIFIED = "verified"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    duration_minutes: Mapped[int] = mapped_column(Integer)
    positive_marks: Mapped[float] = mapped_column(Float, default=2.0)
    negative_marks: Mapped[float] = mapped_column(Float, default=0.5)


class UserExamFocus(Base):
    """Per-user currently selected published exam stage.

    Deliberately additive: existing exam targets, attempts, lessons and
    progress remain untouched. A later PR will scope their queries.
    """
    __tablename__ = "user_exam_focus"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    exam_slug: Mapped[str] = mapped_column(String(120), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)




class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(180))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Topic(Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(String(150), index=True)
    name: Mapped[str] = mapped_column(String(180))
    priority: Mapped[int] = mapped_column(Integer, default=3)
    parent_topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"))
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True)
    subtopic: Mapped[str | None] = mapped_column(String(160), nullable=True)
    pattern_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    question_text: Mapped[str] = mapped_column(Text)
    question_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    correct_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    fast_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[int] = mapped_column(Integer, default=2)
    expected_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shift: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_type: Mapped[str] = mapped_column(String(40), default=SourceType.USER_PRIVATE.value)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    requires_visual_review: Mapped[bool] = mapped_column(Boolean, default=False)
    source_chosen_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_question_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    source_status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="private")
    verification_status: Mapped[str] = mapped_column(String(40), default=VerificationStatus.RAW.value)
    fingerprint: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    options: Mapped[list["QuestionOption"]] = relationship(
        back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.position"
    )


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    question: Mapped[Question] = relationship(back_populates="options")


class QuestionOptionInsight(Base):
    """Reviewed knowledge about a *wrong* MCQ option.

    Content stays invisible until human-reviewed and explicitly published.
    Published insights are returned only after a learner submits an answer.
    """
    __tablename__ = "question_option_insights"

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    option_position: Mapped[int] = mapped_column(Integer, primary_key=True)
    insight_type: Mapped[str] = mapped_column(String(30), default="fact")
    knowledge_text: Mapped[str] = mapped_column(Text)
    related_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str] = mapped_column(Text)
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="draft")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class QuestionAttempt(Base):
    __tablename__ = "question_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    selected_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    time_seconds: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_hint: Mapped[bool] = mapped_column(Boolean, default=False)
    mistake_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TopicMastery(Base):
    __tablename__ = "topic_mastery"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"))
    mastery_score: Mapped[float] = mapped_column(Float, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    correct: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RevisionItem(Base):
    __tablename__ = "revision_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    reason: Mapped[str] = mapped_column(String(40))
    successful_reviews: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    intro: Mapped[str] = mapped_column(Text)
    concept: Mapped[str] = mapped_column(Text)
    shortcut: Mapped[str | None] = mapped_column(Text, nullable=True)
    worked_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_traps: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=10)
    sort_order: Mapped[int] = mapped_column(Integer, default=1)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)


class LessonBlock(Base):
    __tablename__ = "lesson_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id", ondelete="CASCADE"), index=True)
    block_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=1)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)


class QuestionArchetype(Base):
    __tablename__ = "question_archetypes"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(220))
    skill: Mapped[str] = mapped_column(Text)
    recognition_cues: Mapped[str] = mapped_column(Text)
    canonical_method: Mapped[str] = mapped_column(Text)
    shortcut_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_trap: Mapped[str | None] = mapped_column(Text, nullable=True)
    easy_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    medium_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    hard_rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_time_seconds: Mapped[int] = mapped_column(Integer, default=60)
    source_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)


class MockAttempt(Base):
    __tablename__ = "mock_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    mode: Mapped[str] = mapped_column(String(30))
    subject_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), default="in_progress")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    correct_count: Mapped[int] = mapped_column(Integer, default=0)
    incorrect_count: Mapped[int] = mapped_column(Integer, default=0)
    unattempted_count: Mapped[int] = mapped_column(Integer, default=0)


class MockAttemptQuestion(Base):
    __tablename__ = "mock_attempt_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("mock_attempts.id", ondelete="CASCADE"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    section_slug: Mapped[str] = mapped_column(String(120))
    position: Mapped[int] = mapped_column(Integer)
    selected_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    marked_for_review: Mapped[bool] = mapped_column(Boolean, default=False)
    time_seconds: Mapped[float] = mapped_column(Float, default=0)


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True, index=True)
    front: Mapped[str] = mapped_column(Text)
    back: Mapped[str] = mapped_column(Text)
    related_fact: Mapped[str | None] = mapped_column(Text, nullable=True)
    card_type: Mapped[str] = mapped_column(String(40), default="fact")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)


class FlashcardProgress(Base):
    __tablename__ = "flashcard_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    flashcard_id: Mapped[int] = mapped_column(ForeignKey("flashcards.id"), index=True)
    successful_reviews: Mapped[int] = mapped_column(Integer, default=0)
    next_review_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ExamTarget(Base):
    __tablename__ = "exam_targets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    exam_date: Mapped[date] = mapped_column(Date)
    daily_minutes: Mapped[int] = mapped_column(Integer, default=180)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class DailyPlanTask(Base):
    __tablename__ = "daily_plan_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan_date: Mapped[date] = mapped_column(Date, index=True)
    activity_type: Mapped[str] = mapped_column(String(40))
    subject_slug: Mapped[str | None] = mapped_column(String(120), nullable=True)
    topic_id: Mapped[int | None] = mapped_column(ForeignKey("topics.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    target_minutes: Mapped[int] = mapped_column(Integer, default=15)
    target_questions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=3)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
