"""merge

Revision ID: ac38511aa175
Revises: 0002, 01e26e1d6a52, 5447a123bcde
Create Date: 2026-06-07 22:41:38.832874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac38511aa175'
down_revision: Union[str, None] = ('0002', '01e26e1d6a52', '5447a123bcde')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
