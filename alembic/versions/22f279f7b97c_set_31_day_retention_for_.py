"""Set 31-day retention for businessandtrade.gov.uk and dsit.gov.uk users

Revision ID: 22f279f7b97c
Revises: 2f6c1b8a9d04
Create Date: 2026-10-23 16:41:49.636465

"""

from collections.abc import Sequence

from alembic import op

revision: str = "22f279f7b97c"
down_revision: str | None = "2f6c1b8a9d04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        UPDATE "user"
        SET data_retention_days = 31
        WHERE email ILIKE '%@businessandtrade.gov.uk'
           OR email ILIKE '%@dsit.gov.uk'
    """)


def downgrade() -> None:
    # One-off backfill: the previous per-user values are not recorded anywhere,
    # so there is nothing to restore. 30 is also the column default.
    pass
