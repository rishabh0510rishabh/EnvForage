"""compress generated script content

Revision ID: compress_generated_scripts
Revises: f113b99acf31
Create Date: 2026-06-21

"""

import zlib

from alembic import op
import sqlalchemy as sa


revision = "compress_generated_scripts"
down_revision = "f113b99acf31"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    rows = conn.execute(
        sa.text(
            "SELECT id, content FROM generated_scripts"
        )
    ).fetchall()

    for row in rows:
        compressed_content = zlib.compress(
            row.content.encode("utf-8")
        )

        conn.execute(
            sa.text(
                """
                UPDATE generated_scripts
                SET content = :content
                WHERE id = :id
                """
            ),
            {
                "id": row.id,
                "content": compressed_content,
            },
        )

    op.alter_column(
        "generated_scripts",
        "content",
        existing_type=sa.Text(),
        type_=sa.LargeBinary(),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "generated_scripts",
        "content",
        existing_type=sa.LargeBinary(),
        type_=sa.Text(),
        existing_nullable=False,
    )