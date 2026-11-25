from sqlalchemy import ColumnElement, and_, false, or_

from common.authz import ActorPermissions, Permission
from common.database.postgres_models import Transcription


def visible_transcriptions_filter(actor: ActorPermissions) -> ColumnElement[bool]:
    """A boolean SQL expression selecting the transcriptions ``actor`` may read."""
    clauses: list[ColumnElement[bool]] = []

    if Permission.FILE_READ_OWN in actor.personal:
        clauses.append(
            and_(
                Transcription.org_id.is_(None),  # type: ignore[attr-defined]
                Transcription.user_id == actor.user_id,
            )
        )

    for org_id, perms in actor.by_org.items():
        if Permission.FILE_READ_ANY in perms:
            clauses.append(Transcription.org_id == org_id)
        elif Permission.FILE_READ_OWN in perms:
            clauses.append(
                and_(
                    Transcription.org_id == org_id,
                    Transcription.user_id == actor.user_id,
                )
            )

    if not clauses:
        return false()

    return or_(*clauses)
