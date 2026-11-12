"""Add roles to user

Revision ID: e6f0c3d8a2b4
Revises: d7e2f9a4c1b3
Create Date: 2026-11-16 10:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f0c3d8a2b4"
down_revision: str | None = "d7e2f9a4c1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user", sa.Column("roles", sa.ARRAY(sqlmodel.sql.sqltypes.AutoString()), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "roles")
