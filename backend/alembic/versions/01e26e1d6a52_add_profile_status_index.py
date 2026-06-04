"""add_profile_status_index

Revision ID: 01e26e1d6a52
Revises: 21e6b6b21ff3
Create Date: 2026-06-03 01:54:32.845791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01e26e1d6a52'
down_revision: Union[str, None] = '21e6b6b21ff3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "idx_profiles_status_deleted",
        "environment_profiles",
        ["status", "deleted_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_profiles_status_deleted", table_name="environment_profiles")
