"""Set 30-day retention for businessandtrade.gov.uk users

Revision ID: 2f6c1b8a9d04
Revises: b8c4d2e7f1a9
Create Date: 2026-10-23 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "2f6c1b8a9d04"
down_revision: str | None = "b8c4d2e7f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Exact domain only: the '@' immediately before the domain excludes
    # subdomains (x@sub.businessandtrade.gov.uk) and lookalikes
    # (x@notbusinessandtrade.gov.uk). ILIKE covers any un-lowercased rows.
    op.execute("""
        UPDATE "user"
        SET data_retention_days = 30
        WHERE email ILIKE '%@businessandtrade.gov.uk'
    """)


def downgrade() -> None:
    # One-off backfill: the previous per-user values are not recorded anywhere,
    # so there is nothing to restore. 30 is also the column default.
    pass
