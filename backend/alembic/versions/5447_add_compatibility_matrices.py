"""add compatibility matrices

Revision ID: 5447a123bcde
Revises: 21e6b6b21ff3
Create Date: 2026-06-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5447a123bcde"
down_revision: str | None = "21e6b6b21ff3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── cuda_compatibility_matrix ─────────────────────────────────────────────
    op.create_table(
        "cuda_compatibility_matrix",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cuda_version", sa.String(16), nullable=False, unique=True),
        sa.Column("min_driver_linux", sa.String(32), nullable=False),
        sa.Column("min_driver_windows", sa.String(32), nullable=False),
        sa.Column("cudnn_versions", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("supported_archs", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
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

    # ── rocm_compatibility_matrix ─────────────────────────────────────────────
    op.create_table(
        "rocm_compatibility_matrix",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("rocm_version", sa.String(16), nullable=False, unique=True),
        sa.Column("min_driver_linux", sa.String(32), nullable=False),
        sa.Column("supported_gpus", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("source_url", sa.Text, nullable=True),
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

    # ── python_compatibility_matrix ───────────────────────────────────────────
    op.create_table(
        "python_compatibility_matrix",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("framework", sa.String(64), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("min_python", sa.String(16), nullable=False),
        sa.Column("max_python", sa.String(16), nullable=False),
        sa.Column("supported_cuda", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("supported_rocm", postgresql.ARRAY(sa.String), nullable=False),
        sa.Column("supported_python", postgresql.ARRAY(sa.String), nullable=False),
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
        sa.UniqueConstraint("framework", "version", name="uq_framework_version"),
    )


def downgrade() -> None:
    op.drop_table("python_compatibility_matrix")
    op.drop_table("rocm_compatibility_matrix")
    op.drop_table("cuda_compatibility_matrix")
