"""add roles permissions and org tenancy tables

Revision ID: 8b229444d54b
Revises: d7e2f9a4c1b3
Create Date: 2026-11-15 08:43:25.254817

Adds the authorization layer (organisations with an archive flag, per-org
membership, roles, and service-wide user role grants). The permission catalogue
is defined in code (common/authz/catalogue.py); each role carries the
permissions it grants as a JSON array on the ``role`` table, so roles and their
grants are data while permission identifiers are code. Also adds a nullable
org_id to recording and transcription.

Seed data (roles and their granted permissions) lives in the following revision
so the schema and the data are cleanly separable.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "8b229444d54b"
down_revision: str | None = "d7e2f9a4c1b3"
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
            # Soft-deletion flag: archiving an org sets this false rather than
            # deleting the row, so history and content ownership are preserved.
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if "role" not in existing_tables:
        op.create_table(
            "role",
            sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_datetime", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_datetime", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column("is_system", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            # Permissions this role grants, as a JSON array of Permission string
            # values. The permission catalogue is defined in code
            # (common/authz/catalogue.py); roles and their grants are data.
            sa.Column(
                "permissions",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default=sa.text("'[]'::jsonb"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_role_name"), "role", ["name"], unique=True)

    if "membership" not in existing_tables:
        op.create_table(
            "membership",
            sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("created_datetime", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_datetime", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("org_id", sa.Uuid(), nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.ForeignKeyConstraint(["org_id"], ["organisation.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
        )
        op.create_index(op.f("ix_membership_org_id"), "membership", ["org_id"], unique=False)
        op.create_index(op.f("ix_membership_user_id"), "membership", ["user_id"], unique=False)

    if "membership_role" not in existing_tables:
        op.create_table(
            "membership_role",
            sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("membership_id", sa.Uuid(), nullable=False),
            sa.Column("role_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["membership_id"], ["membership.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["role_id"], ["role.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("membership_id", "role_id", name="uq_membership_role"),
        )
        op.create_index(op.f("ix_membership_role_membership_id"), "membership_role", ["membership_id"], unique=False)
        op.create_index(op.f("ix_membership_role_role_id"), "membership_role", ["role_id"], unique=False)

    if "user_role" not in existing_tables:
        # The global-context analogue of membership_role: binds roles directly
        # to a user, independent of any org, so service-wide roles such as
        # service_owner resolve in the personal context (org_id is None).
        op.create_table(
            "user_role",
            sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("role_id", sa.Uuid(), nullable=False),
            sa.ForeignKeyConstraint(["role_id"], ["role.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
        )
        op.create_index(op.f("ix_user_role_role_id"), "user_role", ["role_id"], unique=False)
        op.create_index(op.f("ix_user_role_user_id"), "user_role", ["user_id"], unique=False)

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

    if "user_role" in existing_tables:
        op.drop_index(op.f("ix_user_role_user_id"), table_name="user_role")
        op.drop_index(op.f("ix_user_role_role_id"), table_name="user_role")
        op.drop_table("user_role")

    if "membership_role" in existing_tables:
        op.drop_index(op.f("ix_membership_role_role_id"), table_name="membership_role")
        op.drop_index(op.f("ix_membership_role_membership_id"), table_name="membership_role")
        op.drop_table("membership_role")

    if "membership" in existing_tables:
        op.drop_index(op.f("ix_membership_user_id"), table_name="membership")
        op.drop_index(op.f("ix_membership_org_id"), table_name="membership")
        op.drop_table("membership")

    if "role" in existing_tables:
        op.drop_index(op.f("ix_role_name"), table_name="role")
        op.drop_table("role")

    if "organisation" in existing_tables:
        op.drop_table("organisation")
