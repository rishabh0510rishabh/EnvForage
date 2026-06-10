"""add_deleted_at_to_profile_packages

Revision ID: 85bfc532a74c
Revises: ac38511aa175
Create Date: 2026-06-07 22:41:47.489625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85bfc532a74c'
down_revision: Union[str, None] = 'ac38511aa175'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('profile_packages',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('profile_packages', 'deleted_at')
