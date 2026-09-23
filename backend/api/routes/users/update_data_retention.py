import logging

from backend.api.dependencies import SQLSessionDep, UserDep
from common.types import GetUserResponse, UpdateDataRetentionReq

logger = logging.getLogger(__name__)


async def endpoint(
    user: UserDep,
    session: SQLSessionDep,
    req: UpdateDataRetentionReq,
) -> GetUserResponse:
    """Update the data retention period for the current user."""

    user.data_retention_days = req.data_retention_days
    await session.commit()
    await session.refresh(user)

    logger.info(
        "Updated data retention period to %s days for user %s",
        req.data_retention_days,
        user.id,
    )

    return GetUserResponse.from_user(user)
