"""Replace transcription attempt generation with run ID

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-06 16:45:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("transcription", "attempt_generation")
    op.add_column(
        "transcription",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transcription", "run_id")
    op.add_column(
        "transcription",
        sa.Column("attempt_generation", sa.Integer(), server_default="0", nullable=False),
    )
