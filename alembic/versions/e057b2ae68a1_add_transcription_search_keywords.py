"""Add search keywords to transcriptions.

Revision ID: e057b2ae68a1
Revises: c2d9e4f6a8b1
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from alembic import op

revision: str = "e057b2ae68a1"
down_revision: str | None = "c2d9e4f6a8b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transcription", sa.Column("search_keywords", ARRAY(sa.Text()), nullable=True))
    op.add_column(
        "transcription",
        sa.Column("search_keywords_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("transcription", "search_keywords_generated")
    op.drop_column("transcription", "search_keywords")
