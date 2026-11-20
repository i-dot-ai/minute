"""seed permissions roles and role-permission mappings

Revision ID: c7e1a9d35f20
Revises: 8b229444d54b
Create Date: 2026-11-15 08:50:00.000000

Seeds permissions & roles, wires up which permissions each role grants.

Role -> permission mapping:
  personal_default : file.create, file.read.own, file.edit.own,
                     file.delete.own, file.export.own
  member           : same baseline as personal_default (within an org)
  file_admin       : file.read.any + file.open.any
  permissions_admin: membership.manage
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7e1a9d35f20"
down_revision: str | None = "8b229444d54b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS = [
    "file.create",
    "file.read.own",
    "file.edit.own",
    "file.delete.own",
    "file.export.own",
    "file.read.any",
    "file.open.any",
    "membership.manage",
]


ROLE_PERMISSIONS: dict[str, list[str]] = {
    "personal_default": ["file.create", "file.read.own", "file.edit.own", "file.delete.own", "file.export.own"],
    "member": ["file.create", "file.read.own", "file.edit.own", "file.delete.own", "file.export.own"],
    "file_admin": ["file.read.any", "file.open.any"],
    "permissions_admin": ["membership.manage"],
}


def upgrade() -> None:
    bind = op.get_bind()

    for name in PERMISSIONS:
        bind.execute(
            sa.text("INSERT INTO permission (name) VALUES (:name) " "ON CONFLICT (name) DO NOTHING"),
            {"name": name},
        )

    for name in ROLE_PERMISSIONS:
        bind.execute(
            sa.text("INSERT INTO role (name, is_system) VALUES (:name, true) " "ON CONFLICT (name) DO NOTHING"),
            {"name": name},
        )

    for role_name, permission_names in ROLE_PERMISSIONS.items():
        for permission_name in permission_names:
            bind.execute(
                sa.text(
                    "INSERT INTO role_permission (role_id, permission_id) "
                    "SELECT r.id, p.id FROM role r, permission p "
                    "WHERE r.name = :role_name AND p.name = :permission_name "
                    "ON CONFLICT (role_id, permission_id) DO NOTHING"
                ),
                {"role_name": role_name, "permission_name": permission_name},
            )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM role_permission WHERE role_id IN " "(SELECT id FROM role WHERE name = ANY(:roles))"),
        {"roles": list(ROLE_PERMISSIONS.keys())},
    )
    bind.execute(
        sa.text("DELETE FROM role WHERE name = ANY(:roles)"),
        {"roles": list(ROLE_PERMISSIONS.keys())},
    )
    bind.execute(
        sa.text("DELETE FROM permission WHERE name = ANY(:perms)"),
        {"perms": PERMISSIONS},
    )
