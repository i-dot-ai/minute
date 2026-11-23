"""Fix businessandtrade.gov.uk users' retention at 30 days.

Revision ID: 3e91a7c2d6b4
Revises: d7e2f9a4c1b3
Create Date: 2026-11-23

"""

from collections.abc import Sequence

from alembic import op

revision: str = "3e91a7c2d6b4"
down_revision: str | None = "d7e2f9a4c1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""UPDATE "user" SET data_retention_days = 30 WHERE email ILIKE '%@businessandtrade.gov.uk'""")


def downgrade() -> None:
    # Previous per-user retention values cannot be recovered.
    pass
