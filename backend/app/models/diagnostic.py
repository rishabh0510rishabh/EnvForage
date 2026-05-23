"""SQLAlchemy ORM models for diagnostic reports and verification results."""
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DiagnosticReport(Base):
    __tablename__ = "diagnostic_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    os_type: Mapped[str | None] = mapped_column(String(16))
    gpu_name: Mapped[str | None] = mapped_column(String(128))
    cuda_version: Mapped[str | None] = mapped_column(String(16))
    rocm_version: Mapped[str | None] = mapped_column(String(16))
    python_version: Mapped[str | None] = mapped_column(String(8))
    driver_version: Mapped[str | None] = mapped_column(String(32))

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationships
    verification_results: Mapped[list["VerificationResult"]] = relationship(
        "VerificationResult", back_populates="report"
    )


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("diagnostic_reports.id", ondelete="SET NULL"))
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("environment_profiles.id", ondelete="CASCADE"), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(16), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationships
    report: Mapped["DiagnosticReport | None"] = relationship(
        "DiagnosticReport", back_populates="verification_results"
    )
    checks: Mapped[list["VerificationCheck"]] = relationship(
        "VerificationCheck", back_populates="result", cascade="all, delete-orphan"
    )


class VerificationCheck(Base):
    __tablename__ = "verification_checks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("verification_results.id", ondelete="CASCADE"), nullable=False)
    check_name: Mapped[str] = mapped_column(String(128), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )

    # Relationships
    result: Mapped["VerificationResult"] = relationship(
        "VerificationResult", back_populates="checks"
    )
