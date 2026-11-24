"""Add meeting_datetime to transcription

Revision ID: c2d9e4f6a8b1
Revises: d7e2f9a4c1b3
Create Date: 2026-11-18 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d9e4f6a8b1"
down_revision: str | None = "d7e2f9a4c1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "transcription",
        sa.Column("meeting_datetime", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    # Existing meetings have no better start time than when they were uploaded.
    op.execute("UPDATE transcription SET meeting_datetime = created_datetime")
    op.alter_column("transcription", "meeting_datetime", nullable=False)


def downgrade() -> None:
    op.drop_column("transcription", "meeting_datetime")
