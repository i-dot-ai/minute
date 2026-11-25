"""Resource-level authorization helpers for content routes."""

from typing import TypeVar
from uuid import UUID

from fastapi import HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from common.authz import Action, ResourceOwnership, can, context_permissions
from common.database.postgres_models import Minute, MinuteVersion, Recording, Transcription

_AuthzResource = TypeVar("_AuthzResource", Transcription, Recording, Minute, MinuteVersion)


def _resolve_ownership(resource: _AuthzResource) -> ResourceOwnership | None:
    """Resolve the ``ResourceOwnership`` for ``resource``, dispatching on its type.

    Transcription & Recording carry ownership directly. Minute and MinuteVersion
    inherit it from the parent Transcription.
    """
    if isinstance(resource, Minute | MinuteVersion):
        minute = resource if isinstance(resource, Minute) else resource.minute
        transcription = minute.transcription if minute is not None else None
        if transcription is None:
            return None
        return ResourceOwnership(org_id=transcription.org_id, created_by_user_id=transcription.user_id)
    return ResourceOwnership(org_id=resource.org_id, created_by_user_id=resource.user_id)


async def authorize_resource(
    session: AsyncSession,
    user_id: UUID,
    resource: _AuthzResource | None,
    action: Action,
) -> _AuthzResource:
    """Return ``resource`` if ``user_id`` may ``action`` it, else raise 404."""
    if resource is None:
        raise HTTPException(status_code=404, detail="Not found")

    ownership = _resolve_ownership(resource)
    if ownership is None:
        raise HTTPException(status_code=404, detail="Not found")

    perms = await context_permissions(session, user_id, ownership.org_id)
    if not can(user_id, perms, action, ownership):
        raise HTTPException(status_code=404, detail="Not found")

    return resource
