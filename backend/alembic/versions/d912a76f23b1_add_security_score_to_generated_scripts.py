"""add security_score to generated_scripts

Revision ID: d912a76f23b1
Revises: f113b99acf31
Create Date: 2026-06-27 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd912a76f23b1'
down_revision: Union[str, None] = 'f113b99acf31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'generated_scripts',
        sa.Column('security_score', sa.String(length=16), server_default='Low', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('generated_scripts', 'security_score')
