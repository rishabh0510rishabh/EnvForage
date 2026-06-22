"""SQLAlchemy ORM models for script generation jobs."""

import uuid
import zlib
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CompressedText(sa.TypeDecorator):
    """
    Automatically compress text before storing in DB
    and decompress when reading.
    """

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None

        return zlib.compress(value.encode("utf-8"))

    def process_result_value(self, value, dialect):
        if value is None:
            return None

        return zlib.decompress(value).decode("utf-8")

class ScriptGenerationJob(Base):
    __tablename__ = "script_generation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("environment_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_os: Mapped[str] = mapped_column(String(16), nullable=False)
    python_version: Mapped[str] = mapped_column(String(8), nullable=False)
    cuda_version: Mapped[str | None] = mapped_column(String(16))
    overrides: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    error: Mapped[str | None] = mapped_column(Text)
    resolved_env: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    profile: Mapped["EnvironmentProfile"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "EnvironmentProfile", back_populates="generation_jobs"
    )
    scripts: Mapped[list["GeneratedScript"]] = relationship(
        "GeneratedScript", back_populates="job", cascade="all, delete-orphan"
    )


class GeneratedScript(Base):
    __tablename__ = "generated_scripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("script_generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(
    CompressedText,
    nullable=False,
)
    size_bytes: Mapped[int | None] = mapped_column()

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    job: Mapped["ScriptGenerationJob"] = relationship(
        "ScriptGenerationJob", back_populates="scripts"
    )
