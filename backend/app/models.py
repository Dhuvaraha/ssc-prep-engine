from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
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
