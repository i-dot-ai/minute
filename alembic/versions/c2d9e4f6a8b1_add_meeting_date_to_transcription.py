"""Add user-provided meeting_date to transcription

Revision ID: c2d9e4f6a8b1
Revises: b8c4d2e7f1a9
Create Date: 2026-11-18 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d9e4f6a8b1"
down_revision: str | None = "b8c4d2e7f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("transcription", sa.Column("meeting_date", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("transcription", "meeting_date")
