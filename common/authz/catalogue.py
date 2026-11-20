"""The permission catalogue: the authoritative, code-side list of capabilities.

Permissions are defined in code (this module), not in the database. The set of
*which permissions exist* is fixed by the application, so it lives with the
application rather than as seeded reference data. Roles - and which permissions
each role grants - remain data in the database (see the ``role`` table's
``permissions`` column), so new roles and remappings are a data change, not a
code change.

The resolver reads a role's granted permission strings from the DB and coerces
each to this enum; unknown strings (catalogue drift) are logged and ignored.
"""

from enum import StrEnum


class Permission(StrEnum):
    """The full set of granular capabilities in the system.

    Own-scoped capabilities (``*.own``) are evaluated against the resource's
    creator; ``*.any`` capabilities grant the action over any resource in the
    context (an org) regardless of creator.
    """

    FILE_CREATE = "file.create"
    FILE_READ_OWN = "file.read.own"
    FILE_EDIT_OWN = "file.edit.own"
    FILE_DELETE_OWN = "file.delete.own"
    FILE_EXPORT_OWN = "file.export.own"
    FILE_READ_ANY = "file.read.any"
    MEMBERSHIP_MANAGE = "membership.manage"
    # Service-wide (global, org-less) capability: create organisations. Resolved
    # in the personal context (org_id is None) via a user_role grant, not a
    # per-org membership.
    ORG_CREATE = "org.create"
    # Per-org organisation capabilities. ``org.read`` is the low baseline every
    # member holds; update/archive are permissions_admin-level.
    ORG_READ = "org.read"
    ORG_UPDATE = "org.update"
    ORG_ARCHIVE = "org.archive"
