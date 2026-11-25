"""Unit tests for the own-vs-any resource rule in ``common.authz.policy``.

DB-free: the context gate (active membership) is covered by the resolver tests,
so here the context permission set is passed directly to ``can``.
"""

import uuid

from common.authz import Action, ResourceOwnership, can
from common.database.postgres_models import Permission

ME = uuid.uuid4()
OTHER = uuid.uuid4()
ORG = uuid.uuid4()

# A plain member's baseline permission set within a context.
MEMBER_SET = frozenset(
    {
        Permission.FILE_CREATE,
        Permission.FILE_READ_OWN,
        Permission.FILE_EDIT_OWN,
        Permission.FILE_DELETE_OWN,
        Permission.FILE_EXPORT_OWN,
    }
)
# A file admin additionally holds read.any (but NOT edit/delete/export.any).
FILE_ADMIN_SET = MEMBER_SET | {Permission.FILE_READ_ANY}


def test_member_can_act_on_own_content():
    resource = ResourceOwnership(org_id=ORG, created_by_user_id=ME)
    assert can(ME, MEMBER_SET, Action.READ, resource)
    assert can(ME, MEMBER_SET, Action.EDIT, resource)
    assert can(ME, MEMBER_SET, Action.DELETE, resource)
    assert can(ME, MEMBER_SET, Action.EXPORT, resource)


def test_member_cannot_act_on_others_content():
    resource = ResourceOwnership(org_id=ORG, created_by_user_id=OTHER)
    assert not can(ME, MEMBER_SET, Action.READ, resource)
    assert not can(ME, MEMBER_SET, Action.EDIT, resource)
    assert not can(ME, MEMBER_SET, Action.DELETE, resource)
    assert not can(ME, MEMBER_SET, Action.EXPORT, resource)


def test_file_admin_can_read_but_not_edit_others_content():
    others = ResourceOwnership(org_id=ORG, created_by_user_id=OTHER)
    # read.any grants read over others' content...
    assert can(ME, FILE_ADMIN_SET, Action.READ, others)
    # ...but there is deliberately no edit.any / delete.any / export.any.
    assert not can(ME, FILE_ADMIN_SET, Action.EDIT, others)
    assert not can(ME, FILE_ADMIN_SET, Action.DELETE, others)
    assert not can(ME, FILE_ADMIN_SET, Action.EXPORT, others)


def test_file_admin_retains_own_rights():
    own = ResourceOwnership(org_id=ORG, created_by_user_id=ME)
    assert can(ME, FILE_ADMIN_SET, Action.EDIT, own)
    assert can(ME, FILE_ADMIN_SET, Action.DELETE, own)


def test_empty_context_set_denies_everything():
    # Non-member / leaver: context_permissions returned an empty set.
    own = ResourceOwnership(org_id=ORG, created_by_user_id=ME)
    assert not can(ME, frozenset(), Action.READ, own)
    assert not can(ME, frozenset(), Action.EDIT, own)
    assert not can(ME, frozenset(), Action.DELETE, own)


def test_personal_content_own_rule_uses_creator():
    # Personal context (org_id None): personal_default is own-scoped, so only the
    # creator can act. A null creator (orphaned legacy row) is nobody's own.
    mine = ResourceOwnership(org_id=None, created_by_user_id=ME)
    not_mine = ResourceOwnership(org_id=None, created_by_user_id=OTHER)
    orphan = ResourceOwnership(org_id=None, created_by_user_id=None)
    assert can(ME, MEMBER_SET, Action.READ, mine)
    assert not can(ME, MEMBER_SET, Action.READ, not_mine)
    assert not can(ME, MEMBER_SET, Action.READ, orphan)
