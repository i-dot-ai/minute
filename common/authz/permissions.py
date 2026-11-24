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
