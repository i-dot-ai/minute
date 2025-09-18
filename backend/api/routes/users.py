import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from backend.api.dependencies import SQLSessionDep, UserDep
from common.types import DataRetentionUpdateResponse, GetUserResponse

users_router = APIRouter(tags=["Users"])

logger = logging.getLogger(__name__)


@users_router.get("/users/me")
def get_user(user: UserDep) -> GetUserResponse:
    return GetUserResponse(
        id=user.id,
        created_datetime=user.created_datetime,
        updated_datetime=user.updated_datetime,
        email=user.email,
        data_retention_days=user.data_retention_days,
        strict_data_retention=user.strict_data_retention,
    )


@users_router.patch("/users/data-retention", response_model=GetUserResponse)
async def update_data_retention(
    data: DataRetentionUpdateResponse,
    session: SQLSessionDep,
    user: UserDep,
) -> GetUserResponse:
    """Update the data retention period for the current user.

    Args:
        data: Request body containing data_retention_days
        current_user: The current authenticated user
    """
    if user.strict_data_retention:
        raise HTTPException(
            status_code=403, detail="Strict data retention enabled, you cannot update your data retention."
        )

    if data.data_retention_days is not None and data.data_retention_days < 1:
        raise HTTPException(
            status_code=400,
            detail="Data retention period must be at least 1 day or None for indefinite retention",
        )

    user.data_retention_days = data.data_retention_days
    user.updated_datetime = datetime.now(tz=UTC)

    await session.commit()
    await session.refresh(user)

    logger.info(
        "Updated data retention period to %s days for user %s",
        data.data_retention_days,
        user.id,
    )

    return GetUserResponse(
        id=user.id,
        created_datetime=user.created_datetime,
        updated_datetime=user.updated_datetime,
        email=user.email,
        data_retention_days=user.data_retention_days,
        strict_data_retention=user.strict_data_retention,
    )
