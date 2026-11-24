from enum import StrEnum

from common.authz.permissions import Permission


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


def permissions_for_role(role_name: RoleName) -> frozenset[Permission]:
    """The permissions granted by ``role_name``."""
    return ROLE_PERMISSIONS[role_name]
