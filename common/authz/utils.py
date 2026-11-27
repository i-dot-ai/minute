from .data import ROLE_PERMISSIONS, Permission, RoleName


def flatten_roles_to_permissions(role_names: set[RoleName] | list[RoleName]) -> frozenset[Permission]:
    """Union the permissions granted by each role."""
    union: set[Permission] = set()
    for role_name in role_names:
        union |= ROLE_PERMISSIONS[role_name]
    return frozenset(union)
