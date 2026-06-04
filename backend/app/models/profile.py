"""SQLAlchemy ORM models for environment profiles."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.script_job import ScriptGenerationJob


class EnvironmentProfile(Base):
    __tablename__ = "environment_profiles"
    __table_args__ = (
        Index("idx_profiles_status_deleted", "status", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    os_support: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    cuda_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    python_versions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    cuda_versions: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    last_validated: Mapped[date | None] = mapped_column(Date)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    packages: Mapped[list["ProfilePackage"]] = relationship(
        "ProfilePackage", back_populates="profile", cascade="all, delete-orphan"
    )
    generation_jobs: Mapped[list["ScriptGenerationJob"]] = relationship(  # noqa: F821
        "ScriptGenerationJob", back_populates="profile"
    )


class ProfilePackage(Base):
    __tablename__ = "profile_packages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("environment_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    package_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version_spec: Mapped[str] = mapped_column(String(64), nullable=False)
    cuda_variant: Mapped[str | None] = mapped_column(String(32))
    is_optional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    install_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    profile: Mapped["EnvironmentProfile"] = relationship(
        "EnvironmentProfile", back_populates="packages"
    )
