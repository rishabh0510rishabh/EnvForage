"""add min_macos_version to python_compatibility_matrix

Revision ID: d4f8b21e6a97
Revises: b7e4a29f1c83
Create Date: 2026-07-29 06:15:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4f8b21e6a97'
down_revision: str | None = 'b7e4a29f1c83'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "python_compatibility_matrix",
        sa.Column("min_macos_version", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("python_compatibility_matrix", "min_macos_version")
