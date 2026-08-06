"""merge uninstall feedback and compress scripts heads

Revision ID: b7e4a29f1c83
Revises: 21fe8cc61865, compress_generated_scripts
Create Date: 2026-07-29 06:00:00.000000

"""
from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = 'b7e4a29f1c83'
down_revision: str | None = ('21fe8cc61865', 'compress_generated_scripts')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass