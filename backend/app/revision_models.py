"""Additive backend-only Phase B evidence; legacy records stay unchanged."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class QuestionRevision(Base):
    __tablename__ = 'question_revisions'
    __table_args__ = {'sqlite_with_rowid': False}
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'), index=True)
    payload: Mapped[str] = mapped_column(Text)
    answer_version: Mapped[str] = mapped_column(String(64))
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DeliveryRevision(Base):
    __tablename__ = 'delivery_revisions'
    __table_args__ = {'sqlite_with_rowid': False}
    kind: Mapped[str] = mapped_column(String(20), primary_key=True)
    delivery_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    revision_id: Mapped[str] = mapped_column(ForeignKey('question_revisions.id'))
    source_ids: Mapped[str] = mapped_column(Text)
    blueprint: Mapped[str] = mapped_column(Text)


class EditorialCandidate(Base):
    __tablename__ = 'editorial_candidates'
    __table_args__ = {'sqlite_with_rowid': False}
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey('questions.id'), index=True)
    parent_revision_id: Mapped[str] = mapped_column(ForeignKey('question_revisions.id'))
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    payload: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class EditorialDecision(Base):
    __tablename__ = 'editorial_decisions'
    __table_args__ = {'sqlite_with_rowid': False}
    candidate_id: Mapped[str] = mapped_column(ForeignKey('editorial_candidates.id'), primary_key=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    evidence: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
