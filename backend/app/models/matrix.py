"""SQLAlchemy ORM models for compatibility matrices."""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CUDAMatrixEntry(Base):
    __tablename__ = "cuda_compatibility_matrix"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuda_version: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    min_driver_linux: Mapped[str] = mapped_column(String(32), nullable=False)
    min_driver_windows: Mapped[str] = mapped_column(String(32), nullable=False)
    cudnn_versions: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    supported_archs: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class RocmMatrixEntry(Base):
    __tablename__ = "rocm_compatibility_matrix"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    rocm_version: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    min_driver_linux: Mapped[str] = mapped_column(String(32), nullable=False)
    supported_gpus: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class PythonMatrixEntry(Base):
    __tablename__ = "python_compatibility_matrix"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    framework: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    min_python: Mapped[str] = mapped_column(String(16), nullable=False)
    max_python: Mapped[str] = mapped_column(String(16), nullable=False)
    supported_cuda: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    supported_rocm: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    supported_python: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("framework", "version", name="uq_framework_version"),
    )
