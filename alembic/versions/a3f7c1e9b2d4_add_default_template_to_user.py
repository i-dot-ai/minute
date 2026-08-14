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


def _user_columns() -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns("user")}


def _user_foreign_keys() -> set[str]:
    return {fk["name"] for fk in sa.inspect(op.get_bind()).get_foreign_keys("user")}


def upgrade() -> None:
    # Guarded so this replays cleanly on environments where an earlier deploy of
    # this revision already created the columns but the stamp was later rolled back.
    existing_columns = _user_columns()

    if "default_template_id" not in existing_columns:
        op.add_column("user", sa.Column("default_template_id", sa.Uuid(), nullable=True))
    if "default_template_name" not in existing_columns:
        op.add_column("user", sa.Column("default_template_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True))

    if "fk_user_default_template" not in _user_foreign_keys():
        op.create_foreign_key(
            "fk_user_default_template",
            "user",
            "user_template",
            ["default_template_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    if "fk_user_default_template" in _user_foreign_keys():
        op.drop_constraint("fk_user_default_template", "user", type_="foreignkey")

    existing_columns = _user_columns()

    if "default_template_name" in existing_columns:
        op.drop_column("user", "default_template_name")
    if "default_template_id" in existing_columns:
        op.drop_column("user", "default_template_id")
