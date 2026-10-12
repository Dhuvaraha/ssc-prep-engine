"""Additive Phase A records. No implicit grants or changes to legacy IDs."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ContentSource(Base):
    __tablename__ = "content_sources"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"))
    # Licensing approval is independent of an individual learner's grant.
    private_use_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    public_use_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_reference: Mapped[str] = mapped_column(Text)


class CourseGrant(Base):
    __tablename__ = "course_grants"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class SourceGrant(Base):
    __tablename__ = "source_grants"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("content_sources.id"), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class ContentBinding(Base):
    """Reviewed complete dependency set; multiple sources require ALL grants.

    resource_kind is question, lesson, archetype or flashcard. Lesson bindings
    cover all its blocks. Operators must bind every contributing source.
    """
    __tablename__ = "content_bindings"
    resource_kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    resource_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("content_sources.id"), primary_key=True)


class EntitlementAudit(Base):
    __tablename__ = "entitlement_audit"
    id: Mapped[int] = mapped_column(primary_key=True)
    operator: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str] = mapped_column(Text)
    manifest_digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PracticeDelivery(Base):
    __tablename__ = "practice_deliveries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"))
    content_digest: Mapped[str] = mapped_column(String(64))
    assisted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    request_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class ContentExposure(Base):
    __tablename__ = "content_exposures"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    # Normalized stem/options digest covers exact-content duplicate IDs.
    content_digest: Mapped[str] = mapped_column(String(64), primary_key=True)
    reason: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AssessmentAsset(Base):
    """Explicitly reviewed, answer-free crop; never a whole answer-key page."""
    __tablename__ = "assessment_assets"
    asset_key: Mapped[str] = mapped_column(String(500), primary_key=True)
    content_sha256: Mapped[str] = mapped_column(String(64))
    review_reference: Mapped[str] = mapped_column(Text)


class AssessmentDelivery(Base):
    __tablename__ = "assessment_deliveries"
    attempt_id: Mapped[int] = mapped_column(ForeignKey("mock_attempts.id"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), primary_key=True)
    content_digest: Mapped[str] = mapped_column(String(64))
    correct_option: Mapped[int] = mapped_column(Integer)
