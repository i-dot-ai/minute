"""add roles permissions and org tenancy tables

Revision ID: 8b229444d54b
Revises: c2d9e4f6a8b1
Create Date: 2026-11-15 08:43:25.254817

Adds Organisations and static authorization layer).
Permissions and roles are both defined in code since they're tightly coupled to
the codebase; role grants are stored as a JSON array of role names directly on
the row they apply to - org-scoped grants on ``membership.roles`` and
service-wide grants on ``user.roles`` (the role's permission set lives in
common/authz/roles.py).
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "8b229444d54b"
down_revision: str | None = "c2d9e4f6a8b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_names() -> set[str]:
    return set(sa.inspect(op.get_bind()).get_table_names())


def _columns(table: str) -> set[str]:
    return {col["name"] for col in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    existing_tables = _table_names()

    if "organisation" not in existing_tables:
        op.create_table(
            "organisation",
            sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_datetime", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_datetime", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "membership" not in existing_tables:
        op.create_table(
            "membership",
            sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_datetime", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_datetime", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("org_id", sa.Uuid(), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column(
                "roles",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["org_id"], ["organisation.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
        )
        op.create_index(op.f("ix_membership_org_id"), "membership", ["org_id"], unique=False)
        op.create_index(op.f("ix_membership_user_id"), "membership", ["user_id"], unique=False)

    if "roles" not in _columns("user"):
        op.add_column(
            "user",
            sa.Column(
                "roles",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
        )

    if "org_id" not in _columns("recording"):
        op.add_column("recording", sa.Column("org_id", sa.Uuid(), nullable=True))
        op.create_foreign_key("fk_recording_org", "recording", "organisation", ["org_id"], ["id"], ondelete="SET NULL")

    if "org_id" not in _columns("transcription"):
        op.add_column("transcription", sa.Column("org_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(
            "fk_transcription_org", "transcription", "organisation", ["org_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    existing_tables = _table_names()

    if "org_id" in _columns("transcription"):
        op.drop_constraint("fk_transcription_org", "transcription", type_="foreignkey")
        op.drop_column("transcription", "org_id")

    if "org_id" in _columns("recording"):
        op.drop_constraint("fk_recording_org", "recording", type_="foreignkey")
        op.drop_column("recording", "org_id")

    if "roles" in _columns("user"):
        op.drop_column("user", "roles")

    if "membership" in existing_tables:
        op.drop_index(op.f("ix_membership_user_id"), table_name="membership")
        op.drop_index(op.f("ix_membership_org_id"), table_name="membership")
        op.drop_table("membership")

    if "organisation" in existing_tables:
        op.drop_table("organisation")
