"""SQLAlchemy ORM models for AI sessions, suggestions, and audit log."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AISession(Base):
    __tablename__ = "ai_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    diagnostic_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("diagnostic_reports.id", ondelete="SET NULL"), index=True
    )
    verification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("verification_results.id", ondelete="SET NULL"), index=True
    )
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("environment_profiles.id", ondelete="SET NULL"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, index=True)

    # Relationships
    suggestions: Mapped[list["AISuggestion"]] = relationship(
        "AISuggestion", back_populates="session", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AIAuditLog"]] = relationship(
        "AIAuditLog", back_populates="session"
    )


class AISuggestion(Base):
    __tablename__ = "ai_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    safe_commands: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    template_id: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(nullable=False, index=True)

    # Relationships
    session: Mapped["AISession"] = relationship(
        "AISession", back_populates="suggestions"
    )


class AIAuditLog(Base):
    __tablename__ = "ai_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_sessions.id", ondelete="SET NULL"), index=True
    )
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    safety_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    safety_violation: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str | None] = mapped_column(String(32))
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(nullable=False, index=True)

    # Relationships
    session: Mapped["AISession | None"] = relationship(
        "AISession", back_populates="audit_logs"
    )
