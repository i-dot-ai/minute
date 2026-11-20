"""seed roles and their granted permissions

Revision ID: c7e1a9d35f20
Revises: 8b229444d54b
Create Date: 2026-11-15 08:50:00.000000

Seeds the roles and the permissions each grants. The permission catalogue
itself is code (common/authz/catalogue.py); here we only record which
permission strings each role grants, stored as a JSON array on the role.

Role -> permissions:
  personal_default : file.create, file.read.own, file.edit.own,
                     file.delete.own, file.export.own
  member           : same baseline as personal_default, plus org.read
  file_admin       : file.read.any
  permissions_admin: membership.manage, org.update, org.archive
  service_owner    : org.create  (service-wide; held via user_role, org-less)
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7e1a9d35f20"
down_revision: str | None = "8b229444d54b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ROLE_PERMISSIONS: dict[str, list[str]] = {
    "personal_default": ["file.create", "file.read.own", "file.edit.own", "file.delete.own", "file.export.own"],
    "member": ["file.create", "file.read.own", "file.edit.own", "file.delete.own", "file.export.own", "org.read"],
    "file_admin": ["file.read.any"],
    "permissions_admin": ["membership.manage", "org.update", "org.archive"],
    "service_owner": ["org.create"],
}


def upgrade() -> None:
    bind = op.get_bind()

    for role_name, permissions in ROLE_PERMISSIONS.items():
        # Insert the role with its permissions, or refresh the permissions of an
        # existing role so re-running converges on the code-defined grants.
        bind.execute(
            sa.text(
                "INSERT INTO role (name, is_system, permissions) "
                "VALUES (:name, true, CAST(:permissions AS jsonb)) "
                "ON CONFLICT (name) DO UPDATE SET permissions = EXCLUDED.permissions"
            ),
            {"name": role_name, "permissions": json.dumps(permissions)},
        )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM role WHERE name = ANY(:roles)"),
        {"roles": list(ROLE_PERMISSIONS.keys())},
    )
