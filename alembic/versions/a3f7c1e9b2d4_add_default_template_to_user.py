"""Add default template to user

Revision ID: a3f7c1e9b2d4
Revises: c4f9d2a1b8e3
Create Date: 2026-07-03 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f7c1e9b2d4"
down_revision: str | None = "c4f9d2a1b8e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("user", sa.Column("default_template_id", sa.Uuid(), nullable=True))
    op.add_column("user", sa.Column("default_template_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.create_foreign_key(
        "fk_user_default_template",
        "user",
        "user_template",
        ["default_template_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_user_default_template", "user", type_="foreignkey")
    op.drop_column("user", "default_template_name")
    op.drop_column("user", "default_template_id")
