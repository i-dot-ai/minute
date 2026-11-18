"""Add display_name to user

Revision ID: d7e2f9a4c1b3
Revises: b8c4d2e7f1a9
Create Date: 2026-11-13 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e2f9a4c1b3"
down_revision: str | None = "b8c4d2e7f1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user", sa.Column("display_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "display_name")
