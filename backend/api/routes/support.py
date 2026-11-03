import logging
from datetime import UTC, datetime
from enum import StrEnum

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.dependencies import UserDep
from common.services.linear_client import LinearNotConfiguredError, create_linear_issue

support_router = APIRouter(tags=["Support"])

logger = logging.getLogger(__name__)


class SupportCategory(StrEnum):
    ACCESS = "access"
    ISSUE = "issue"
    RECOMMENDATION = "recommendation"
    GENERAL = "general"


class CreateSupportTicketRequest(BaseModel):
    category: SupportCategory
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)


class CreateSupportTicketResponse(BaseModel):
    reference: str


@support_router.post("/support/tickets")
async def create_support_ticket(
    data: CreateSupportTicketRequest, user: UserDep, request: Request
) -> CreateSupportTicketResponse:
    title = f"[{data.category.capitalize()}] {data.subject}"
    description = (
        f"User id: {user.id}\n"
        f"Email: {user.email}\n"
        f"Sent: {datetime.now(UTC):%Y-%m-%d %H:%M} UTC\n"
        f"Browser: {request.headers.get('user-agent', 'unknown')}"
        f"\n\n---\n{data.message}"
    )
    try:
        reference = await create_linear_issue(title, description)
    except LinearNotConfiguredError as e:
        raise HTTPException(status_code=503, detail="Support tickets are not configured") from e
    except Exception as e:
        logger.exception("Failed to create Linear support ticket")
        raise HTTPException(status_code=502, detail="Failed to create support ticket") from e
    return CreateSupportTicketResponse(reference=reference)
