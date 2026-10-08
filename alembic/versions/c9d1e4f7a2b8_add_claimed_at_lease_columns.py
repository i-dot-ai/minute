"""Add claimed_at lease columns for worker job claims

Revision ID: c9d1e4f7a2b8
Revises: b8c4d2e7f1a9
Create Date: 2026-10-08 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d1e4f7a2b8"
down_revision: str | None = "b8c4d2e7f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table in ["transcription", "minute_version"]:
        op.add_column(table, sa.Column("claimed_at", sa.TIMESTAMP(timezone=True), nullable=True))
        # Seed in-flight rows so a lease written before this column existed is not
        # treated as immediately stealable by the worker's staleness check.
        op.execute(
            f"UPDATE {table} SET claimed_at = updated_datetime WHERE status = 'IN_PROGRESS'"  # noqa: S608
        )


def downgrade() -> None:
    for table in ["minute_version", "transcription"]:
        op.drop_column(table, "claimed_at")
