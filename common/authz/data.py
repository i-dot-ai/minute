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
    ORG_CREATE = "org.create"
    ORG_READ = "org.read"
    ORG_UPDATE = "org.update"
    ORG_ARCHIVE = "org.archive"


class RoleName(StrEnum):
    PERSONAL_DEFAULT = "personal_default"
    MEMBER = "member"
    FILE_ADMIN = "file_admin"
    PERMISSIONS_ADMIN = "permissions_admin"
    SERVICE_OWNER = "service_owner"


ROLE_PERMISSIONS: dict[RoleName, frozenset[Permission]] = {
    RoleName.PERSONAL_DEFAULT: frozenset(
        {
            Permission.FILE_CREATE,
            Permission.FILE_READ_OWN,
            Permission.FILE_EDIT_OWN,
            Permission.FILE_DELETE_OWN,
            Permission.FILE_EXPORT_OWN,
        }
    ),
    RoleName.MEMBER: frozenset(
        {
            Permission.ORG_READ,
            Permission.FILE_CREATE,
            Permission.FILE_READ_OWN,
            Permission.FILE_EDIT_OWN,
            Permission.FILE_DELETE_OWN,
            Permission.FILE_EXPORT_OWN,
        }
    ),
    RoleName.FILE_ADMIN: frozenset({Permission.FILE_READ_ANY}),
    RoleName.PERMISSIONS_ADMIN: frozenset(
        {Permission.MEMBERSHIP_MANAGE, Permission.ORG_UPDATE, Permission.ORG_ARCHIVE}
    ),
    RoleName.SERVICE_OWNER: frozenset({Permission.ORG_CREATE}),
}
