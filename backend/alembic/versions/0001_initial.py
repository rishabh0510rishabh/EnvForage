"""Initial schema — all EnvForage tables.

Revision ID: 0001
Revises:Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── environment_profiles ──────────────────────────────────────────────────
    op.create_table(
        "environment_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("tags", postgresql.ARRAY(sa.String)),
        sa.Column("os_support", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("cuda_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("python_versions", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("cuda_versions", postgresql.ARRAY(sa.String)),
        sa.Column("status", sa.String(16), nullable=False, server_default="ACTIVE"),
        sa.Column("last_validated", sa.Date),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("idx_profiles_slug", "environment_profiles", ["slug"])
    op.create_index(
        "idx_profiles_tags", "environment_profiles", ["tags"], postgresql_using="gin"
    )
    op.create_index(
        "idx_profiles_os",
        "environment_profiles",
        ["os_support"],
        postgresql_using="gin",
    )

    # ── profile_packages ──────────────────────────────────────────────────────
    op.create_table(
        "profile_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_name", sa.String(128), nullable=False),
        sa.Column("version_spec", sa.String(64), nullable=False),
        sa.Column("cuda_variant", sa.String(32)),
        sa.Column("is_optional", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("install_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["environment_profiles.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "idx_profile_packages_profile_id", "profile_packages", ["profile_id"]
    )

    # ── cuda_compatibility_matrix ─────────────────────────────────────────────
    op.create_table(
        "cuda_compatibility_matrix",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cuda_version", sa.String(16), nullable=False, unique=True),
        sa.Column("min_driver_linux", sa.String(32)),
        sa.Column("min_driver_windows", sa.String(32)),
        sa.Column("cudnn_versions", postgresql.ARRAY(sa.String)),
        sa.Column("supported_archs", postgresql.ARRAY(sa.String)),
        sa.Column("notes", sa.Text),
        sa.Column("source_url", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── script_generation_jobs ────────────────────────────────────────────────
    op.create_table(
        "script_generation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_os", sa.String(16), nullable=False),
        sa.Column("python_version", sa.String(8), nullable=False),
        sa.Column("cuda_version", sa.String(16)),
        sa.Column("overrides", postgresql.JSONB),
        sa.Column("status", sa.String(16), nullable=False, server_default="PENDING"),
        sa.Column("error", sa.Text),
        sa.Column("resolved_env", postgresql.JSONB),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["profile_id"], ["environment_profiles.id"]),
    )
    op.create_index("idx_jobs_profile_id", "script_generation_jobs", ["profile_id"])
    op.create_index("idx_jobs_status", "script_generation_jobs", ["status"])

    # ── generated_scripts ─────────────────────────────────────────────────────
    op.create_table(
        "generated_scripts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(128), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("size_bytes", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["script_generation_jobs.id"], ondelete="CASCADE"
        ),
    )
    op.create_index("idx_generated_scripts_job_id", "generated_scripts", ["job_id"])

    # ── diagnostic_reports ────────────────────────────────────────────────────
    op.create_table(
        "diagnostic_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_data", postgresql.JSONB, nullable=False),
        sa.Column("os_type", sa.String(16)),
        sa.Column("gpu_name", sa.String(128)),
        sa.Column("cuda_version", sa.String(16)),
        sa.Column("python_version", sa.String(8)),
        sa.Column("driver_version", sa.String(32)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_diag_os", "diagnostic_reports", ["os_type"])
    op.create_index("idx_diag_cuda", "diagnostic_reports", ["cuda_version"])

    # ── verification_results ──────────────────────────────────────────────────
    op.create_table(
        "verification_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True)),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_status", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["report_id"], ["diagnostic_reports.id"]),
        sa.ForeignKeyConstraint(["profile_id"], ["environment_profiles.id"]),
    )

    # ── verification_checks ───────────────────────────────────────────────────
    op.create_table(
        "verification_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_name", sa.String(128), nullable=False),
        sa.Column("passed", sa.Boolean, nullable=False),
        sa.Column("detail", sa.Text),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["result_id"], ["verification_results.id"], ondelete="CASCADE"
        ),
    )

    # ── ai_sessions ───────────────────────────────────────────────────────────
    op.create_table(
        "ai_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("diagnostic_id", postgresql.UUID(as_uuid=True)),
        sa.Column("verification_id", postgresql.UUID(as_uuid=True)),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True)),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # ── ai_suggestions ────────────────────────────────────────────────────────
    op.create_table(
        "ai_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_number", sa.Integer, nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("safe_commands", postgresql.ARRAY(sa.String)),
        sa.Column("template_id", sa.String(128)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["ai_sessions.id"], ondelete="CASCADE"),
    )

    # ── ai_audit_log ──────────────────────────────────────────────────────────
    op.create_table(
        "ai_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True)),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("safety_passed", sa.Boolean, nullable=False),
        sa.Column("safety_violation", sa.Text),
        sa.Column("provider", sa.String(32)),
        sa.Column("tokens_used", sa.Integer),
        sa.Column("latency_ms", sa.Integer),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["ai_sessions.id"]),
    )
    op.create_index("idx_audit_session", "ai_audit_log", ["session_id"])
    op.create_index("idx_audit_safety", "ai_audit_log", ["safety_passed"])


def downgrade() -> None:
    op.drop_table("ai_audit_log")
    op.drop_table("ai_suggestions")
    op.drop_table("ai_sessions")
    op.drop_table("verification_checks")
    op.drop_table("verification_results")
    op.drop_table("diagnostic_reports")
    op.drop_table("generated_scripts")
    op.drop_table("script_generation_jobs")
    op.drop_table("cuda_compatibility_matrix")
    op.drop_table("profile_packages")
    op.drop_table("environment_profiles")
